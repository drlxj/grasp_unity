"""
Render a grasp stage in Blender: a set of cells from export_grasp_scenes.py set out on
one floor and photographed together.

Runs inside Blender, not the grasping env:
  blender -b --factory-startup --python render_grasps.py -- --scenes <dir> --out <dir>
          [--width 4000] [--samples 128] [--hand skeleton|skin] [--fov 20]
          [--rows level|packed] [--frame-cols 0 11] [--frame-rows 0 10] [--save-blend]

Each cell is its object in the object's default orientation with one grasp around it,
so every column shows one object the same way round and the hands reaching it from
wherever they did. Columns run left to right across the picture, a wider gap between
clusters, and rows recede from the viewer, spaced by what each cell actually covers on
screen so nothing overlaps. Every object's bottom sits at one height, FLOOR_DROP above a
shadow-catching floor. The camera frames the whole stage, or with --frame-cols and
--frame-rows (0-based, end excluded) only those cells, the rest still in the scene.

Writes <out>/stage.png, transparent but for the shadows; <out>/labels.json, the pixel
position above each column where its title would go; and with --save-blend the scene
itself, <out>/stage.blend, to take further by hand (a camera move, say).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

# The dataset is y-up, Blender z-up: a quarter turn about x, (x, y, z) -> (x, -z, y).
# Every position that enters the scene goes through this, and nothing else changes axes.
Y_UP_TO_Z_UP = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))

# Paper colours, as sRGB hex. The skeleton keeps org_style's one grey family: dark bones,
# lighter joints, no hue of its own. The object is the figure's neutral warm grey.
OBJECT_HEX = "#c4c0b8"
BONE_HEX = "#3a3f47"
JOINT_HEX = "#8d96a3"

# The stage. Gaps are on screen, in metres at the stage's depth, between the extents of
# neighbouring cells; the floor is this far under the objects' common bottom.
COLUMN_GAP = 0.03
ROW_GAP = 0.03
FLOOR_DROP = 0.15
SAFE_AREA = 0.96
SKYLINE_BIN = 0.01  # strip width for comparing silhouettes, in metres on screen
CLUSTER_GAP = 0.12  # added between two columns from different clusters
LAYOUT_POINTS = 4000  # at most this many vertices of a cell are used to lay it out

# Sun lights, so every cell on the stage is lit the same. (azimuth offset from the
# camera, elevation, strength in W/m2, angular diameter in degrees, casts shadows). The
# key comes from the upper left of the picture, the usual reading direction for light,
# and high. Only the key and the world cast shadows: the rim light stands behind the
# stage, low, and would drag long shadows towards the viewer. The key's 2 W/m2 plus the
# world's pi * strength make a face turned to it bright, not white.
LIGHTS = {
    "key": dict(azimuth=-50.0, elevation=72.0, strength=2.0, angle=12.0, shadow=True),
    "fill": dict(azimuth=70.0, elevation=30.0, strength=0.5, angle=30.0, shadow=False),
    "rim": dict(azimuth=175.0, elevation=40.0, strength=0.8, angle=20.0, shadow=False),
}
WORLD_STRENGTH = 0.18


def hex_to_linear(hex_color):
    """'#rrggbb' in sRGB to linear RGBA, which is what Blender's colour inputs take."""
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (*(lin(int(hex_color[i:i + 2], 16) / 255) for i in (1, 3, 5)), 1.0)


def direction(azimuth_deg, elevation_deg):
    """aitviewer_utils.camera_direction, in Blender's axes."""
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    return Y_UP_TO_Z_UP @ Vector((math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)))


def look_at(obj, position, target=Vector((0, 0, 0))):
    obj.location = position
    obj.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()


def screen_axes(view):
    """Right and up on screen for a camera looking back along `view`, as numpy arrays."""
    right = Vector((0, 0, 1)).cross(view).normalized()
    return np.array(right), np.array(view.cross(right))


# --------------------------------------------------------------------------- setup

def reset_scene(samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            if any(d.type == backend for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == backend
                scene.cycles.device = "GPU"
                break
        except TypeError:
            continue
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    # Standard, not AgX/Filmic: the paper colours should come back as the colours given.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = WORLD_STRENGTH
    scene.world = world
    return scene


def material(name, hex_color, roughness, specular=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = specular
    return mat


def add_lights(camera_azimuth):
    """The three suns, each placed by its angle from the camera's azimuth."""
    for name, spec in LIGHTS.items():
        light = bpy.data.lights.new(name, "SUN")
        light.energy = spec["strength"]
        light.angle = math.radians(spec["angle"])
        light.use_shadow = spec["shadow"]
        obj = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(obj)
        look_at(obj, direction(camera_azimuth + spec["azimuth"], spec["elevation"]))


def add_floor(height):
    """A shadow catcher: invisible itself, it leaves only the shadows in the alpha."""
    bpy.ops.mesh.primitive_plane_add(size=30.0, location=(0, 0, height))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.is_shadow_catcher = True
    return floor


# --------------------------------------------------------------------------- meshes

def link_mesh(name, mesh_or_bm, mat, smooth=True):
    if isinstance(mesh_or_bm, bmesh.types.BMesh):
        mesh = bpy.data.meshes.new(name)
        mesh_or_bm.to_mesh(mesh)
        mesh_or_bm.free()
    else:
        mesh = mesh_or_bm
    mesh.materials.append(mat)
    if smooth:
        mesh.shade_smooth()  # not a Python loop over faces: a stage holds ~20M of them
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def world_verts(obj):
    """An object's vertices in world space, (N, 3)."""
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    m = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


_MESHES = {}


def add_object(npz_path, rot, trans, mat):
    """The object, placed. Every cell of one object shares one mesh (Cycles instances it)."""
    if npz_path.stem not in _MESHES:
        data = np.load(npz_path)
        mesh = bpy.data.meshes.new(npz_path.stem)
        mesh.from_pydata(data["verts"].tolist(), [], data["faces"].tolist())
        mesh.validate()
        mesh.shade_smooth()
        mesh.set_sharp_from_angle(angle=math.radians(35))
        mesh.materials.append(mat)
        _MESHES[npz_path.stem] = mesh
    obj = bpy.data.objects.new(npz_path.stem, _MESHES[npz_path.stem])
    bpy.context.scene.collection.objects.link(obj)
    placement = Matrix.Identity(4)
    for i in range(3):
        placement[i][3] = trans[i]
        for j in range(3):
            placement[i][j] = rot[i][j]
    obj.matrix_world = Y_UP_TO_Z_UP.to_4x4() @ placement
    return obj


def add_skeleton(hand, skeleton, joint_radius, bone_radius, joint_mat, bone_mat):
    """Spheres at the joints and cylinders along the bones, one mesh each."""
    points = [Y_UP_TO_Z_UP @ Vector(p) for p in hand]

    bm = bmesh.new()
    for p in points:
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=joint_radius,
                                  matrix=Matrix.Translation(p))
    joints = link_mesh("Joints", bm, joint_mat)

    bm = bmesh.new()
    for a, b in skeleton:
        pa, pb = points[a], points[b]
        axis = pb - pa
        orient = axis.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=bone_radius, radius2=bone_radius,
                              depth=axis.length, matrix=Matrix.Translation((pa + pb) / 2) @ orient)
    return [joints, link_mesh("Bones", bm, bone_mat)]


# The skin: no MANO, just the 21 joints. Every bone becomes a metaball capsule, and
# capsules blend where they meet, so the metacarpals (wrist to finger base), drawn
# thick, fuse into a palm. Radii are the surface radii wanted, in metres, at the bone's
# start; fingers taper towards the tip.
FINGER_CHAINS = ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
FINGER_RADIUS = {0: 0.0105, 1: 0.0092, 2: 0.0090, 3: 0.0085, 4: 0.0080}  # thumb .. pinky
PALM_RADIUS = 0.0125
FOREARM = (0.035, 0.018)  # length and radius of the stub behind the wrist
TAPER = 0.85              # tip radius as a share of the finger's base radius
# A low threshold against a high stiffness makes each element's field fall off fast
# past its surface (it reaches 1.26 times the surface radius, against 1.74 at Blender's
# defaults), so neighbouring fingers stay apart while bones meeting at a joint still
# blend smoothly.
METABALL_THRESHOLD, METABALL_STIFFNESS = 0.3, 6.0
# Where the field of one element falls to the threshold, as a share of its radius.
SURFACE_SHARE = math.sqrt(1.0 - (METABALL_THRESHOLD / METABALL_STIFFNESS) ** (1 / 3))
# The bend tint: a joint's colour goes from the skin's to BEND_HEX as it bends from
# straight to BEND_MAX_DEG. The tint is full on the skin over the joint and fades over
# BEND_SPREAD beyond it; joint centres lie inside the finger, a finger's radius deep.
SKIN_HEX = "#aab2bd"
BEND_HEX = "#2f3540"
BEND_MAX_DEG = 80.0
BEND_SPREAD = 0.005


def bend_angles(points):
    """Degrees each joint is bent from straight, for the joints between two bones."""
    angles = {}
    for chain in FINGER_CHAINS:
        full = (0, *chain)
        for p, j, c in zip(full, full[1:], full[2:]):
            a, b = (points[j] - points[p]).normalized(), (points[c] - points[j]).normalized()
            angles[j] = math.degrees(a.angle(b))
    return angles


def add_skin(hand, mat, resolution=0.0008):
    """The hand as one smooth mesh, with a 'bend' colour attribute darkening bent joints."""
    points = [Y_UP_TO_Z_UP @ Vector(p) for p in hand]
    ball = bpy.data.metaballs.new("Skin")
    ball.resolution = ball.render_resolution = resolution
    ball.threshold = METABALL_THRESHOLD

    def capsule(a, b, radius):
        axis = b - a
        el = ball.elements.new(type="CAPSULE")
        el.co = (a + b) / 2
        el.size_x = axis.length / 2
        el.radius = radius / SURFACE_SHARE
        el.stiffness = METABALL_STIFFNESS
        el.rotation = axis.to_track_quat("X", "Z")

    wrist = points[0]
    for f, chain in enumerate(FINGER_CHAINS):
        base = FINGER_RADIUS[f]
        # The thumb's first bone is its metacarpal, inside the palm; the fingers' first
        # bone runs from the wrist to the knuckle, and is the palm.
        capsule(wrist, points[chain[0]], PALM_RADIUS if f else base * 1.15)
        for k, (a, b) in enumerate(zip(chain, chain[1:])):
            capsule(points[a], points[b], base * (1 - (1 - TAPER) * k / 2))
    for a, b in ((5, 9), (9, 13), (13, 17)):  # across the knuckles, to close the palm
        capsule(points[a], points[b], PALM_RADIUS * 0.8)
    back = (wrist - points[9]).normalized()
    capsule(wrist, wrist + back * FOREARM[0], FOREARM[1])

    # Metaball objects of one name family all fuse into one surface, so each hand is
    # turned into a mesh and its metaball removed before the next is made.
    obj = bpy.data.objects.new("SkinBalls", ball)
    bpy.context.scene.collection.objects.link(obj)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    bpy.data.objects.remove(obj)
    bpy.data.metaballs.remove(ball)

    # Tint each vertex by its nearest bent joints, weighted by distance.
    angles = bend_angles(points)
    skin, bend = np.array(hex_to_linear(SKIN_HEX)), np.array(hex_to_linear(BEND_HEX))
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    amount = np.zeros(len(co))
    depth = {j: FINGER_RADIUS[f] for f, chain in enumerate(FINGER_CHAINS) for j in chain}
    for j, deg in angles.items():
        beyond = np.maximum(np.linalg.norm(co - np.array(points[j]), axis=1) - depth[j], 0.0)
        weight = np.exp(-beyond ** 2 / (2 * BEND_SPREAD ** 2))
        amount = np.maximum(amount, min(deg / BEND_MAX_DEG, 1.0) * weight)
    colors = skin + (bend - skin) * amount[:, None]
    attr = mesh.color_attributes.new("bend", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", colors.astype(np.float32).ravel())
    return [link_mesh("Skin", mesh, mat)]


def skin_material():
    """Base colour read from the 'bend' attribute."""
    mat = material("Skin", SKIN_HEX, 0.45, 0.4)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    attr = nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "bend"
    links.new(attr.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
    return mat


# --------------------------------------------------------------------------- stage

def build_cell(name, spec, column, cell, scenes, mats, hand_mode):
    """
    One cell at the origin, parented to an empty that places it on the stage. Its object
    is lifted so its bottom is at z = 0. Returns (empty, world vertices before placing).
    """
    obj = add_object(scenes / f"{column['object']}.npz", cell["obj_rot"], cell["obj_trans"], mats["obj"])
    if hand_mode == "skin":
        hand = add_skin(cell["hand"], mats["skin"])
    else:
        hand = add_skeleton(cell["hand"], spec["skeleton"], spec["joint_radius"], spec["bone_radius"],
                            mats["joint"], mats["bone"])
    lift = -world_verts(obj)[:, 2].min()
    points = np.vstack([world_verts(o) for o in (obj, *hand)]) + [0, 0, lift]
    points = points[::max(1, len(points) // LAYOUT_POINTS)]
    empty = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(empty)
    for child in (obj, *hand):
        child.parent = empty
        child.location.z += lift
    return empty, points


def skyline_step(a_along, a_across, b_along, b_across, gap):
    """
    How far along one screen axis b must sit past a so that the two silhouettes keep
    `gap` apart. Both are cut into strips SKYLINE_BIN wide across that axis; in each
    strip only a's furthest point and b's nearest one matter, and each strip of a is
    checked against b's strips within `gap` of it. So b may tuck into a notch a leaves,
    which a bounding box would never allow.
    """
    lo = min(a_across.min(), b_across.min())
    ia = ((a_across - lo) / SKYLINE_BIN).astype(int)
    ib = ((b_across - lo) / SKYLINE_BIN).astype(int)
    n = max(ia.max(), ib.max()) + 1
    a_far = np.full(n, -np.inf)
    np.maximum.at(a_far, ia, a_along)
    b_near = np.full(n, np.inf)
    np.minimum.at(b_near, ib, b_along)
    reach = math.ceil(gap / SKYLINE_BIN)
    step = -np.inf
    for k in range(-reach, reach + 1):
        shifted = np.full(n, np.inf)
        if k >= 0:
            shifted[:n - k] = b_near[k:]
        else:
            shifted[-k:] = b_near[:n + k]
        both = np.isfinite(a_far) & np.isfinite(shifted)
        if both.any():
            step = max(step, float((a_far[both] - shifted[both]).max()))
    return step + gap


def lay_out(grid, clusters, view, elevation_deg, level_rows):
    """
    Offsets that set the cells out on the floor, and each column's centre on screen.

    `grid[c][r]` holds the (N, 3) vertices of column c, row r; columns may differ in
    length. Rows first: down each column, each cell sits as close under the one before
    as their silhouettes allow (skyline_step). With level_rows, a row's step is the
    largest any column needs, so rows run straight across the stage; without, each
    column is packed on its own. Then columns, each as close to the last as the two
    columns' whole silhouettes allow, plus CLUSTER_GAP where the cluster changes.

    Rows step across the floor away from the viewer, and a step d that way moves a
    point d * sin(elevation) up the screen. Spacing is solved on an orthographic view
    of the stage; the gaps take up what perspective adds.
    """
    right, up = screen_axes(view)
    sx = [[pts @ right for pts in col] for col in grid]
    sy = [[pts @ up for pts in col] for col in grid]

    def row_step(c, r):  # downwards, along -up
        return skyline_step(-sy[c][r - 1], sx[c][r - 1], -sy[c][r], sx[c][r], ROW_GAP)

    if level_rows:
        n_rows = max(len(col) for col in grid)
        steps = [max(row_step(c, r) for c in range(len(grid)) if len(grid[c]) > r) for r in range(1, n_rows)]
        ys = [[-sum(steps[:r]) for r in range(len(col))] for col in grid]
    else:
        ys = []
        for c, col in enumerate(grid):
            steps = [row_step(c, r) for r in range(1, len(col))]
            ys.append([-sum(steps[:r]) for r in range(len(col))])

    xs = [0.0]
    for c in range(1, len(grid)):
        a_x, a_y = np.concatenate(sx[c - 1]), np.concatenate([s + y for s, y in zip(sy[c - 1], ys[c - 1])])
        b_x, b_y = np.concatenate(sx[c]), np.concatenate([s + y for s, y in zip(sy[c], ys[c])])
        step = skyline_step(a_x, a_y, b_x, b_y, COLUMN_GAP)
        xs.append(xs[-1] + step + (CLUSTER_GAP if clusters[c] != clusters[c - 1] else 0.0))

    away = -np.array(view)  # from the camera towards the stage, flattened onto the floor
    away[2] = 0.0
    away /= np.linalg.norm(away)
    sin_el = math.sin(math.radians(elevation_deg))
    offsets = [[right * xs[c] + away * (y / sin_el) for y in ys[c]] for c in range(len(grid))]
    centres = [xs[c] + (min(s.min() for s in sx[c]) + max(s.max() for s in sx[c])) / 2 for c in range(len(grid))]
    top = max(s.max() for s in (col[0] for col in sy))
    return offsets, centres, top


def fit_camera(points, view, fov_deg, aspect):
    """
    aitviewer_utils.fit_distance around the points' centre on screen: where along `view`
    a camera with this vertical field of view must stand to hold every point.
    """
    right, up = screen_axes(view)
    v = np.array(view)
    target = right * (points @ right).min() / 2 + right * (points @ right).max() / 2 \
        + up * (points @ up).min() / 2 + up * (points @ up).max() / 2 + v * (points @ v).mean()
    q = points - target
    tan_v = math.tan(math.radians(fov_deg) / 2) * SAFE_AREA
    tan_h = tan_v * aspect
    along = q @ v
    distance = max(float(np.max(along + np.abs(q @ up) / tan_v)), float(np.max(along + np.abs(q @ right) / tan_h)))
    return Vector(target), distance


# --------------------------------------------------------------------------- main

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--scenes", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--width", type=int, default=4000, help="render width in pixels")
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--fov", type=float, default=20.0,
                   help="vertical field of view in degrees; smaller flattens the perspective")
    p.add_argument("--hand", choices=("skeleton", "skin"), default="skeleton")
    p.add_argument("--rows", choices=("level", "packed"), default="level",
                   help="rows straight across the stage, or each column packed on its own")
    p.add_argument("--frame-cols", nargs=2, type=int, metavar=("START", "END"))
    p.add_argument("--frame-rows", nargs=2, type=int, metavar=("START", "END"))
    p.add_argument("--save-blend", action="store_true")
    return p.parse_args(argv)


def main():
    args = parse_args()
    # Blender resolves a relative output path against neither the shell's directory nor
    # this script's, so make both absolute here.
    args.scenes, args.out = args.scenes.resolve(), args.out.resolve()
    spec = json.loads((args.scenes / "scene.json").read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)

    scene = reset_scene(args.samples)
    mats = dict(obj=material("Object", OBJECT_HEX, 0.55, 0.3), bone=material("Bone", BONE_HEX, 0.35),
                joint=material("Joint", JOINT_HEX, 0.3), skin=skin_material())
    azimuth, elevation = spec["camera"]["azimuth"], spec["camera"]["elevation"]
    view = direction(azimuth, elevation)  # from the stage towards the camera
    right, up = screen_axes(view)

    empties, grid = [], []
    for column in spec["columns"]:
        empties.append([])
        grid.append([])
        for cell in column["cells"]:
            empty, points = build_cell(f"{column['object']}_{cell['row']}", spec, column, cell,
                                       args.scenes, mats, args.hand)
            empties[-1].append(empty)
            grid[-1].append(points)
        print(f"BUILT {column['object']}", flush=True)

    clusters = [column.get("cluster", 0) for column in spec["columns"]]
    offsets, centres, top = lay_out(grid, clusters, view, elevation, args.rows == "level")
    for col_empties, col_offsets in zip(empties, offsets):
        for empty, offset in zip(col_empties, col_offsets):
            empty.location = Vector(offset)
    add_floor(-FLOOR_DROP)
    add_lights(azimuth)

    # Frame the chosen cells and, straight below them, the floor their shadows fall on.
    cols = range(*args.frame_cols) if args.frame_cols else range(len(grid))
    rows = range(*args.frame_rows) if args.frame_rows else range(max(len(col) for col in grid))
    placed = np.vstack([grid[c][r] + offsets[c][r] for c in cols for r in rows if r < len(grid[c])])
    shadows = placed.copy()
    shadows[:, 2] = -FLOOR_DROP
    framed = np.vstack([placed, shadows])
    aspect = np.ptp(framed @ right) / np.ptp(framed @ up)
    scene.render.resolution_x = args.width
    scene.render.resolution_y = round(args.width / aspect)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.sensor_fit = "VERTICAL"
    cam_data.angle_y = math.radians(args.fov)
    cam_data.clip_start = 0.01
    cam_data.clip_end = 100.0
    camera = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(camera)
    target, distance = fit_camera(framed, view, args.fov, aspect)
    look_at(camera, target + view * distance, target)
    scene.camera = camera
    bpy.context.view_layer.update()  # so the camera's matrix_world is current for projecting

    # Where each column's title goes: above its centre, at the top of the first row (which
    # lay_out leaves in place across the screen, unmoved up or down it).
    width, height = scene.render.resolution_x, scene.render.resolution_y
    labels = []
    for column, centre in zip(spec["columns"], centres):
        anchor = Vector(right * centre + up * top)
        u, v, _ = world_to_camera_view(scene, camera, anchor)
        labels.append(dict(title=column["object"], x=u * width, y=(1 - v) * height))
    (args.out / "labels.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")

    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(args.out / "stage.blend"), compress=True)
    scene.render.filepath = str(args.out / "stage.png")
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED stage.png {width}x{height}", flush=True)


if __name__ == "__main__":
    main()
