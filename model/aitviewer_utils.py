"""
aitviewer helpers for hand skeleton + object scenes: renderables, a fixed camera, floor and
shadow, and a fix for aitviewer's window events.
Used by visualize_npz_aitviewer.py and the scripts in visualization/.
"""
import numpy as np
from dataset_utils import HAND_SKELETON_LINES

# (2 * n_edges,) index array: hand_pts[..., _BONE_IDX, :] lays the joints out in the
# start/end pair order that Lines(mode="lines") expects.
_BONE_IDX = np.asarray(HAND_SKELETON_LINES).reshape(-1)


def build_hand_object_renderables(hand_pts, obj_pcl, obj_trans, is_sequence=False):
    """
    hand_pts: (21, 3) or (T, 21, 3)
    obj_pcl: (1024, 3) or (T, 1024, 3)
    obj_trans: (3,) or (T, 3)
    Returns (hand_spheres, hand_lines, obj_pc) for aitviewer.
    """
    from aitviewer.renderables.spheres import Spheres
    from aitviewer.renderables.lines import Lines
    from aitviewer.renderables.point_clouds import PointClouds

    hand_pts = np.asarray(hand_pts, dtype=np.float32)
    obj_pcl = np.asarray(obj_pcl, dtype=np.float32)
    obj_trans = np.asarray(obj_trans, dtype=np.float32)
    if obj_trans.ndim == 1:
        obj_trans = obj_trans.reshape(1, 3)
    if hand_pts.ndim == 2:
        hand_pts = hand_pts[np.newaxis]
    if obj_pcl.ndim == 2:
        obj_pcl = obj_pcl[np.newaxis]
    T = hand_pts.shape[0]
    if obj_trans.shape[0] == 1 and T > 1:
        obj_trans = np.broadcast_to(obj_trans, (T, 3))

    obj_world = obj_pcl + obj_trans[:, np.newaxis, :]

    hand_spheres = Spheres(hand_pts, radius=0.006, color=(0.2, 0.5, 0.9, 1.0))
    hand_lines = Lines(hand_pts[:, _BONE_IDX, :], mode="lines", color=(0.3, 0.3, 0.3, 1.0))
    obj_pc = PointClouds(points=obj_world, color=(0.9, 0.3, 0.2, 0.8))
    return hand_spheres, hand_lines, obj_pc


# ------------------------------------------------------------------------ trial scenes

def build_trial_renderables(trial, *, object_color, joint_color, bone_color, joint_radius, bone_radius):
    """
    The aitviewer nodes for one dataset_utils.Trial: hand joints, hand bones, object mesh.

    Unlike build_hand_object_renderables, the object is its mesh rather than a point cloud.
    """
    from aitviewer.renderables.lines import Lines
    from aitviewer.renderables.meshes import Meshes
    from aitviewer.renderables.spheres import Spheres

    hand_pts = trial.hand
    joints = Spheres(hand_pts, radius=joint_radius, color=joint_color, name="Hand joints")
    bones = Lines(hand_pts[:, _BONE_IDX, :], mode="lines", r_base=bone_radius,
                  color=bone_color, name="Hand bones")

    # Static vertices plus a per-frame 4x4, rather than a full (T, V, 3) vertex sequence:
    # 0.3 MB instead of ~170 MB for a 559-frame trial. aitviewer transposes the matrices
    # itself before upload, so these are plain row-major [[R, t], [0, 1]].
    obj = Meshes(
        np.asarray(trial.entry["verts"], dtype=np.float32),
        np.asarray(trial.entry["faces"]).astype(np.int32),
        instance_transforms=_object_transforms(trial)[:, np.newaxis],
        color=object_color,
        name=trial.object_name,
    )
    return joints, bones, obj


def _object_transforms(trial):
    """Per-frame object placement as (T, 4, 4) matrices."""
    transforms = np.tile(np.eye(4, dtype=np.float32), (len(trial.obj_trans), 1, 1))
    transforms[:, :3, :3] = trial.obj_rot
    transforms[:, :3, 3] = trial.obj_trans
    return transforms


def camera_direction(azimuth_deg, elevation_deg):
    """Unit vector from the wrist towards where the camera sits."""
    az, el = np.radians(azimuth_deg), np.radians(elevation_deg)
    return np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])


def sequence_points(trial):
    """
    Every point the camera has to hold, over the whole trial.

    The object contributes the eight corners of its local bounding box, transformed per
    frame. An affine transform maps the box to a parallelepiped with those corners, and
    the mesh stays inside it, so this bounds the object exactly without touching all
    50k vertices on all several hundred frames.
    """
    verts = np.asarray(trial.entry["verts"], dtype=np.float32)
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    corners = np.array(np.meshgrid(*zip(lo, hi))).reshape(3, -1).T  # (8, 3)
    obj = np.einsum("tij,cj->tci", trial.obj_rot, corners) + trial.obj_trans[:, None, :]
    return np.vstack([trial.hand.reshape(-1, 3), obj.reshape(-1, 3)])


def frame_camera(camera, trial, azimuth_deg, elevation_deg, *, aspect, safe_area):
    """
    Place a fixed camera so the whole trial stays in shot, including the frame where the
    object is furthest away, within the central `safe_area` share of the half-frame.

    The camera looks at the wrist, which is the origin in every trial, so the hand lands
    in the same place on screen no matter which trial is loaded. Distance is solved
    against the view frustum rather than a bounding sphere: a first-person camera looks
    almost straight down the line the object travels, so the far object sits near the
    centre of the image and costs far less room than its 1.6 m would suggest.
    """
    direction = camera_direction(azimuth_deg, elevation_deg)
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(up, direction)
    right /= np.linalg.norm(right)
    screen_up = np.cross(direction, right)

    # Fit against a frustum shrunk to the safe area, so the padding is the same on screen
    # for a point 10 cm away as for one 1.6 m away. A multiplier on the distance instead
    # barely moves a point that is already far away.
    tan_v = np.tan(np.radians(camera.fov) / 2.0) * safe_area
    tan_h = tan_v * aspect

    # For a point q (relative to the target) the camera must sit at least
    # q.direction + |q.screen_axis| / tan(half fov) away for q to fall inside the frustum.
    q = sequence_points(trial)
    along = q @ direction
    distance = max(
        float(np.max(along + np.abs(q @ screen_up) / tan_v)),
        float(np.max(along + np.abs(q @ right) / tan_h)),
    )

    camera.target = np.zeros(3)
    camera.position = direction * distance


def place_floor(scene, trial, *, drop):
    """
    Put the floor at one height for the whole trial, `drop` metres below its lowest point.

    aitviewer's own auto_set_floor() re-seats it on the lowest point of the *current*
    frame, so it jumps as soon as the object is moved into reach and ends up slicing
    through the hand; turn that off on the viewer when using this.
    """
    lowest = float(sequence_points(trial)[:, 1].min())
    scene.floor.enabled = True
    scene.floor.position[1] = lowest - drop
    scene.floor.update_transform(parent_transform=scene.model_matrix)


def cast_shadow_from_camera_side(scene, azimuth_deg, *, elevation_deg):
    """
    Make the light on the camera's side the shadow caster, raised to `elevation_deg` and
    swung round to follow the camera's azimuth, so the shadow stays in view whichever
    way the camera faces.

    Out of the box the shadow comes from the light on the far side, which throws it
    towards the camera and out of shot. Only this one light moves, so the overall
    lighting, and with it the colours of the scene, stay as they were.
    """
    from aitviewer.utils.utils import spherical_coordinates_from_direction

    lights = {light.name: light for light in scene.lights}
    back, front = lights["Back Light"], lights["Front Light"]  # as set up by aitviewer's Scene

    position = camera_direction(azimuth_deg, elevation_deg) * np.linalg.norm(back.position)
    back.position = position
    back.elevation, back.azimuth = spherical_coordinates_from_direction(
        -position / np.linalg.norm(position), degrees=True
    )
    back.shadow_enabled = True
    front.shadow_enabled = False


# ------------------------------------------------------------------------ window events

# aitviewer 1.13 was written against moderngl-window 2.x, whose WindowConfig looked for
# handlers named render(), key_event(), mouse_press_event() and so on. moderngl-window
# 3.x looks for on_render(), on_key_event(), ... instead, finds none of aitviewer's, and
# wires the base class's no-ops. Every input event is then dropped without a word: no
# GUI clicks, no camera orbit, no keyboard shortcuts, no reaction to window resizes.
_WINDOW_EVENTS = (
    "render",
    "resize",
    "key_event",
    "mouse_position_event",
    "mouse_press_event",
    "mouse_release_event",
    "mouse_drag_event",
    "mouse_scroll_event",
    "unicode_char_entered",
)


def connect_window_events(viewer):
    """Hand the window's callbacks to aitviewer's handlers under their 2.x names."""
    for name in _WINDOW_EVENTS:
        setattr(viewer.wnd, f"{name}_func", getattr(viewer, name))

    # Once events do arrive, the first scroll crashes one layer down: moderngl-window's
    # imgui bridge writes io.mouse_wheel_h, which pyimgui 2.0 calls mouse_wheel_horizontal.
    io = viewer.imgui.io

    def mouse_scroll_event(x_offset, y_offset):
        io.mouse_wheel_horizontal = x_offset
        io.mouse_wheel = y_offset

    viewer.imgui.mouse_scroll_event = mouse_scroll_event
