#!/usr/bin/env python3
"""
The panels of the dataset figure on the project page, one PNG per panel.

Three rows, one claim each (the claims themselves live in the page's HTML, not here):

  pose_gap     an out-of-reach grasp is not the contact grasp it stands in for:
               the same trial's out-of-reach posture, its in-reach posture, and the two
               overlaid with every joint tinted by how far it moved
  negatives    the dataset records grasps that do not work: one frozen posture from one
               session, shown three replacement objects with three different outcomes
  orientation  how a person grasps follows the object's orientation, in a way set by its
               shape and function: one participant's grasps of an apple, a banana and a
               teapot, each at the three orientations it was presented in

Panels are separate files so the page can lay them out responsively, and each row's
panels share one camera distance and one crop, so they can sit side by side at one
scale. A preview sheet per row is written beside them for review only; it is not meant
for the page. manifest.csv records which trial and frame every panel shows.

The trials shown are fixed in SHOWCASE. Left at None, a row takes the top pick of its
picker; --candidates N renders the top N alternatives instead, to choose from.

Usage:
  python render_showcase_rows.py                            # all rows, SHOWCASE picks
  python render_showcase_rows.py --rows orientation
  python render_showcase_rows.py --candidates 4 --rows negatives
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# dataset_utils and aitviewer_utils live in model/, one level up; outputs stay in model/.
MODEL_DIR = Path(__file__).resolve().parents[1]
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

import aitviewer_utils
import dataset_utils
import render_org_dataset_thumbnails as thumbs
import visualize_collected_data as viz
from compute_pose_offsets import FINGERTIPS
from org_style import (BONE_RGBA, INK, INK_SOFT, JOINT_RGBA, OFFSET_MAX_CM, RENDER_DIM, SURFACE,
                       VERDICT_HEX, hex_to_rgba, offset_colormap, offset_rgba, style, verdict_of)

ORG_DATASET = viz.ORG_DATASET
TRIALS_CSV = MODEL_DIR / "outputs" / "org_dataset" / "trials.csv"
OFFSETS_CSV = MODEL_DIR / "outputs" / "org_dataset" / "pose_offsets.csv"
DEFAULT_OUT = MODEL_DIR / "outputs" / "org_dataset" / "showcase"

# The trials on the page. None means "the picker's first choice"; once a choice is made
# from --candidates, pin it here so a re-run cannot quietly swap the picture.
SHOWCASE = {
    # pick_pose_gap's first choice: fingers straight out of reach, curled round the banana
    # in reach, the gap largest at the tips.
    "pose_gap": dict(rel_path="s19/banana/20250801_153113/all_trials.json", trial=0),
    # pick_negatives' third: a posture formed for the bowl; a teapot turned down at a
    # distance, headphones accepted, a game controller accepted and then failed in reach.
    "negatives": dict(rel_path="s10/bowl/20250729_100341/all_trials.json",
                      trials={"oor_no": 1, "oor_yes_ir_yes": 3, "oor_yes_ir_no": 2}),
    # pick_orientation's top five, in its order; the first also fills the bubbles.
    "orientation": dict(subjects=["s20", "s17", "s14", "s1", "s19"]),
}
ROWS = tuple(SHOWCASE)

# No symmetry to adapt to / a long axis to follow / a handle to find.
ORIENTATION_OBJECTS = ("apple", "banana", "teapot")
# Left to right in the negatives row, as (key, org_style verdict). Named by what was
# recorded, not by why: the data holds the two judgements, never the reason an object
# accepted at a distance then failed in reach, and calling that "wrong orientation"
# would also blur this row into the orientation row below it.
OUTCOMES = (("oor_no", "incompatible"),
            ("oor_yes_ir_yes", "compatible"),
            ("oor_yes_ir_no", "wrong orientation"))

# The viewer's first-person viewpoint, for the rows where the object is in the picture.
FIRST_PERSON = (viz.CAMERA_AZIMUTH_DEG, viz.CAMERA_ELEVATION_DEG)
# The posture row, from behind the hand and 45 degrees round to the thumb side, 45
# degrees up: the fingers fan out rather than stacking behind one another, and the thumb
# stays clear of the palm, which a view from straight above hides it under.
POSE_CAMERA = (138.0, 45.0)
# The orientation figure: participants as rows; for each object, its three orientations
# as columns. Every cell is turned about the vertical into the object's own frame, so
# the object is the same in all of them and the hand arrives from wherever that
# orientation put it. Seen from high up, so the hand shows over the object from any side.
ORIENTATION_ROWS = 5
ORIENTATION_CAMERA = (160.0, 60.0)
# Neutral rather than a verdict colour: this figure encodes no verdict (every trial in it
# is a target grasp), and the hands in the bubbles need the colour to tell apart.
ORIENTATION_OBJECT_HEX = "#c4c0b8"
# The three orientations' hands in each bubble, keyed to the column chips. The first
# three categorical slots, which validate all-pairs (worst CVD Delta E 9.2); the aqua is
# 2.74:1 on the surface, so every colour also carries its number in the header.
ORIENTATION_HAND_HEX = ("#2a78d6", "#eb6834", "#1baf7a")
CELL_PX = 360          # final width of one grid cell
GROUP_GAP_PX = 28      # between one object's three columns and the next object's
ROW_LABEL_PX = 96      # left margin for the participant labels
HEADER_PX = 132        # top band for object names and column chips
BUBBLE_CELLS = 1.75    # bubble diameter, in cell widths ...
BUBBLE_ROWS = 2.2      # ... or in row heights, whichever is smaller: it covers ~two rows
BUBBLE_TOP_GAP_PX = 10  # bubble top below the header, over the first rows of the grid
BUBBLE_EDGE = "#b9b9b4"
# A session counts as the default orientation when its object is within this much of it.
DEFAULT_TOLERANCE_DEG = 2.0

# The two-slot panels of the posture and negatives rows: the object's place 2 m away
# above, the space within reach below, at identical positions in every panel of a row.
# Objects in the far slot are drawn at this share of their in-reach scale -- a cue that
# they are further off, not a measurement; at true perspective they would be specks.
FAR_SCALE = 0.55
SLOT_LABELS = ("2 m", "in reach")
SLOT_EDGE = "#d9d9d6"
SLOT_PAD = 40       # px, inside a slot around its picture
SLOT_HEADER = 84    # px, the band at the top of a slot for its label and mark
SLOT_GAP = 36       # px, between the two slots
PANEL_MARGIN = 12   # px, around the pair
LABEL_PX = 36
MARK_PX = 64
# An object that has left the far slot for the near one is drawn there as a faint
# outline of where it was, at this opacity of its colour.
OUTLINE_ALPHA = 0.55
OUTLINE_PX = 5
CHECK, CROSS = "✓", "✗"

# The out-of-reach hand in the overlay: the same grey family as the hand, lighter and
# drawn as a thin wireframe, so it reads as "where the hand was" without hiding the
# tinted joints of the in-reach hand.
GHOST_RGBA = (0.64, 0.66, 0.69, 1.0)
GHOST_SCALE = 0.35

FINGERS = ("thumb", "index", "middle", "ring", "pinky")


# --------------------------------------------------------------------------- pickers

def pick_pose_gap(n):
    """
    Target trials whose offset is typical overall but concentrated at the fingertips.

    Typical in size: mean offset within 0.2 cm of the median trial, so the picture does
    not exaggerate. Typical in direction: the out-of-reach hand is the more extended one,
    as it is in most trials, by an amount between the median and the 90th percentile --
    ranking on the fingertips alone otherwise favours trials where the fingers close up
    out of reach instead, the less common case. Concentrated: the largest ratio of
    fingertip to finger-base offset. The thumb base sits almost on the wrist and moves by
    millimetres, so it is left out of the ratio.
    """
    df = pd.read_csv(OFFSETS_CSV)
    target = df[df.trial_index == 0].copy()
    median = target.mean_cm.median()
    tips = target[[f"{f}4" for f in FINGERS]].mean(axis=1)
    bases = target[[f"{f}1" for f in FINGERS[1:]]].mean(axis=1)
    target["tip_ratio"] = tips / bases
    ext_lo, ext_hi = target.extension_cm.quantile([0.5, 0.9])
    pool = target[((target.mean_cm - median).abs() < 0.2)
                  & target.extension_cm.between(max(ext_lo, 0.0), ext_hi)]
    pool = pool.sort_values(["tip_ratio", "rel_path"], ascending=[False, True])
    return [dict(rel_path=r.rel_path, trial=int(r.trial_index)) for r in pool.head(n).itertuples()]


def pick_negatives(n):
    """
    Sessions in which the one frozen posture drew all three outcomes from its replacement
    objects, at most one session per target object so the candidates differ.
    """
    df = pd.read_csv(TRIALS_CSV)
    df["verdict"] = verdict_of(df.oor_label, df.ir_label)
    picks, seen_targets = [], set()
    for rel_path, session in df[df.trial_index > 0].groupby("rel_path", sort=True):
        first = session.drop_duplicates("verdict").set_index("verdict").trial_index
        target = session.obj_dir.iloc[0]
        if {v for _, v in OUTCOMES} <= set(first.index) and target not in seen_targets:
            seen_targets.add(target)
            picks.append(dict(rel_path=rel_path, trials={k: int(first[v]) for k, v in OUTCOMES}))
    return picks[:n]


def pick_orientation(n, sources):
    """
    The n participants whose three objects show the contrast most clearly, as one pick
    for the grid. The contrast: the apple grasp barely turns with the apple, the banana
    and teapot grasps turn a lot, and the hand comes at the teapot from a different side
    each time.

    Hand orientation is read off the skeleton (wrist to middle-finger base, and the palm
    normal), approach direction off where the object sits relative to the wrist. Each
    measure is ranked across participants and the ranks summed.
    """
    rows = []
    for subject_dir in sorted(p for p in ORG_DATASET.iterdir() if p.is_dir()):
        row = dict(subject=subject_dir.name)
        for object_name in ORIENTATION_OBJECTS:
            stills = [(t, t.ir_frame) for _, t in load_sessions(subject_dir.name, object_name, sources)]
            turns = pairwise([hand_frame(t.hand[f]) for t, f in stills], rotation_angle)
            approaches = pairwise([-t.obj_trans[f][[0, 2]] for t, f in stills], planar_angle)
            row[f"{object_name}_turn"] = np.mean(turns)
            row[f"{object_name}_approach"] = np.mean(approaches)
        rows.append(row)
        print(f"  {subject_dir.name}: " + ", ".join(f"{k} {v:.0f}" for k, v in row.items() if k != "subject"))
    df = pd.DataFrame(rows)
    df["score"] = (-df.apple_turn.rank() + df.banana_turn.rank() + df.teapot_turn.rank()
                   + df.teapot_approach.rank())
    df = df.sort_values(["score", "subject"], ascending=[False, True])
    return [dict(subjects=list(df.subject.head(n)))]


def hand_frame(hand):
    """An orthonormal frame for a (21, 3) posture: along the palm, across it, its normal."""
    along = hand[9] / np.linalg.norm(hand[9])
    normal = np.cross(hand[5], hand[17])
    normal -= (normal @ along) * along
    normal /= np.linalg.norm(normal)
    return np.stack([along, np.cross(normal, along), normal], axis=1)


def rotation_angle(a, b):
    """Degrees between two rotation matrices."""
    return float(np.degrees(np.arccos(np.clip((np.trace(a.T @ b) - 1) / 2, -1.0, 1.0))))


def planar_angle(a, b):
    """Degrees between two 2D directions."""
    cos = a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def pairwise(items, measure):
    return [measure(items[i], items[j]) for i in range(len(items)) for j in range(i + 1, len(items))]


# --------------------------------------------------------------------------- scenes

def load_sessions(subject, object_name, sources):
    """(path, target trial) for each of this participant's sessions with this object."""
    paths = sorted((ORG_DATASET / subject / object_name).glob("*/all_trials.json"))
    return [(path, dataset_utils.load_trial(path, 0, sources)) for path in paths]


def at_frame(trial, frame, origin=None):
    """A single-frame copy of a Trial, shifted so that `origin` becomes the origin."""
    shift = np.zeros(3) if origin is None else np.asarray(origin)
    return trial._replace(hand=trial.hand[frame:frame + 1] - shift,
                          obj_rot=trial.obj_rot[frame:frame + 1],
                          obj_trans=trial.obj_trans[frame:frame + 1] - shift)


def object_centre(trial, frame):
    """The centre of the object's bounding box at this frame, wrist-relative."""
    verts = np.asarray(trial.entry["verts"])
    return trial.obj_rot[frame] @ ((verts.min(axis=0) + verts.max(axis=0)) / 2) + trial.obj_trans[frame]


def yaw_between(rot_a, rot_b):
    """Degrees the object turned about the vertical from rot_a to rot_b."""
    turn = rot_b @ rot_a.T
    return float(np.degrees(np.arctan2(turn[0, 2], turn[2, 2])))


def hand_nodes(hand, *, joint_color=JOINT_RGBA, bone_color=BONE_RGBA, scale=1.0, name="Hand"):
    return aitviewer_utils.build_hand_renderables(
        hand[np.newaxis], joint_color=joint_color, bone_color=bone_color,
        joint_radius=viz.JOINT_RADIUS * scale, bone_radius=viz.BONE_RADIUS * scale, name=name)


# --------------------------------------------------------------------------- rendering

def build_renderer(size):
    renderer = thumbs.build_renderer(size)
    renderer.scene.background_color = hex_to_rgba(SURFACE)
    return renderer


def distance_for(renderer, points, camera=FIRST_PERSON):
    """Camera distance from the origin that fits `points` in this renderer's frame."""
    width, height = renderer.window_size
    return aitviewer_utils.fit_distance(points, *camera, fov=renderer.scene.camera.fov,
                                        aspect=width / height, safe_area=viz.CAMERA_SAFE_AREA)


def shoot(renderer, nodes, path, distance, camera=FIRST_PERSON):
    """Render `nodes` from the fixed direction, looking at the origin, and save a PNG."""
    renderer.scene.add(*nodes)
    renderer.scene.camera.target = np.zeros(3)
    renderer.scene.camera.position = aitviewer_utils.camera_direction(*camera) * distance
    renderer.scene.current_frame_id = 0
    renderer.save_frame(str(path))
    for node in nodes:
        renderer.scene.remove(node)


def render_set(renderer, jobs, camera):
    """
    Render (path, nodes, points) jobs at one shared camera distance -- the one the
    roomiest job needs -- and crop them all to one box. Returns that distance.
    """
    distance = max(distance_for(renderer, points, camera) for _, _, points in jobs)
    for path, nodes, _ in jobs:
        shoot(renderer, nodes, path, distance, camera)
    thumbs.common_crop([path for path, _, _ in jobs])
    return distance


def provenance(trial_path, trial_index, trial, **extra):
    return dict(rel_path=Path(trial_path).relative_to(ORG_DATASET).as_posix(),
                trial=trial_index, oor_frame=trial.oor_frame, ir_frame=trial.ir_frame,
                object=trial.object_name, oor_label=trial.oor_label, ir_label=trial.ir_label,
                **extra)


def mark(label):
    """The mark for one recorded judgement: yes, no, or not sure."""
    return {1: CHECK, 0: CROSS}.get(label, "?")


def far_still(trial):
    """The object alone where it stood out of reach, centred for its own close-up."""
    frame = trial.oor_frame
    return at_frame(trial, frame, origin=object_centre(trial, frame))


# --------------------------------------------------------------------------- rows

def row_pose_gap(renderer, pick, sources, out_dir):
    """
    Out-of-reach posture, in-reach posture, and the two overlaid.

    The first two panels are two-slot, like the negatives row: out of reach the object
    stands in the far slot and the hand is empty in the near one; in reach the object is
    in the hand and only its outline is left behind. The overlay drops the slots and the
    object, and shows the two hands alone with each in-reach joint tinted by how far it
    moved. The postures are aligned at the wrist by translation only, as
    compute_pose_offsets.py measures them, so each tint is a number in pose_offsets.csv.
    """
    path = ORG_DATASET / pick["rel_path"]
    trial = dataset_utils.load_trial(path, pick["trial"], sources)
    oor, ir = trial.hand[trial.oor_frame], trial.hand[trial.ir_frame]
    cm = np.linalg.norm(oor - ir, axis=1) * 100
    color, _ = viz.verdict(trial)
    held = at_frame(trial, trial.ir_frame)
    distant = far_still(trial)
    slots = slot_dir(out_dir)

    far_png = slots / "row1_far.png"
    d_far = render_set(renderer, [(far_png, (aitviewer_utils.build_object_renderable(distant, color),),
                                   aitviewer_utils.object_points(distant))], POSE_CAMERA)
    near = {
        "oor": (hand_nodes(oor), oor),
        "ir": (viz.build_renderables(held), aitviewer_utils.sequence_points(held)),
        "overlay": ((*hand_nodes(oor, joint_color=GHOST_RGBA, bone_color=GHOST_RGBA,
                                 scale=GHOST_SCALE, name="Out-of-reach hand"),
                     *hand_nodes(ir, joint_color=offset_rgba(cm), name="In-reach hand")),
                    np.vstack([oor, ir])),
    }
    near_png = {name: slots / f"row1_near_{name}.png" for name in near}
    d_near = render_set(renderer, [(near_png[k], nodes, pts) for k, (nodes, pts) in near.items()],
                        POSE_CAMERA)
    layout = slot_layout(far_png, near_png["oor"], FAR_SCALE * d_far / d_near)

    outline = VERDICT_HEX[verdict_of(trial.oor_label, trial.ir_label)]
    panels = {
        "oor": dict(far=far_png, caption="OOR"),
        "ir": dict(far=far_png, far_outline=outline, caption="IR"),
        "overlay": dict(header=colorbar_image(layout["box_width"] - 2 * SLOT_PAD), caption="OOR + IR"),
    }
    manifest = []
    for name, spec in panels.items():
        png = out_dir / f"row1_pose_gap_{name}.png"
        caption = spec.pop("caption")
        compose_panel(png, layout, near=near_png[name], **spec)
        manifest.append(dict(panel=png.name, caption=caption, **provenance(path, pick["trial"], trial)))

    tips = [i + 1 for i in FINGERTIPS]  # the Trial's hand has the wrist prepended
    extension = (np.linalg.norm(oor[tips], axis=1) - np.linalg.norm(ir[tips], axis=1)).mean() * 100
    print(f"  pose_gap: {pick['rel_path']} trial {pick['trial']}  mean {cm[1:].mean():.2f} cm, "
          f"fingertips {cm[tips].mean():.2f} cm, out of reach {extension:+.2f} cm more extended")
    preview(out_dir / "row1_pose_gap_preview.png", [[out_dir / m["panel"] for m in manifest]],
            col_labels=[m["caption"] for m in manifest], row_labels=[""],
            note=f"{trial.object_name}, {pick['rel_path'].split('/')[0]}")
    return manifest


def row_negatives(renderer, pick, sources, out_dir):
    """
    One session's frozen posture with three replacement objects, one per outcome.

    Each panel has the same two slots. The far slot holds the object where it was judged
    at a distance, marked with that judgement: solid if it stayed there, a faint outline
    if it was then brought in. The near slot holds the hand, with the object in it and
    the in-reach judgement where it got that far; the one turned down at a distance never
    came closer, so its near slot has the hand alone and no mark.
    """
    path = ORG_DATASET / pick["rel_path"]
    slots = slot_dir(out_dir)
    cells, far_jobs, near_jobs = [], [], []
    for key, _ in OUTCOMES:
        index = pick["trials"][key]
        trial = dataset_utils.load_trial(path, index, sources)
        color, _ = viz.verdict(trial)
        distant = far_still(trial)
        far_jobs.append((slots / f"row2_far_{key}.png",
                         (aitviewer_utils.build_object_renderable(distant, color),),
                         aitviewer_utils.object_points(distant)))
        if trial.ir_frame is not None:
            held = at_frame(trial, trial.ir_frame)
            near_jobs.append((slots / f"row2_near_{key}.png", viz.build_renderables(held),
                              aitviewer_utils.sequence_points(held)))
        else:
            hand = trial.hand[trial.oor_frame]
            near_jobs.append((slots / f"row2_near_{key}.png", hand_nodes(hand), hand))
        cells.append((key, index, trial))
        print(f"  negatives: {key:<15} {trial.object_name:<14} trial {index}")
    d_far = render_set(renderer, far_jobs, FIRST_PERSON)
    d_near = render_set(renderer, near_jobs, FIRST_PERSON)
    layout = slot_layout(far_jobs[0][0], near_jobs[0][0], FAR_SCALE * d_far / d_near)

    manifest = []
    for (key, index, trial), (far_png, *_), (near_png, *_) in zip(cells, far_jobs, near_jobs):
        reached = trial.ir_frame is not None
        png = out_dir / f"row2_negatives_{key}.png"
        compose_panel(png, layout, far=far_png, near=near_png,
                      far_outline=VERDICT_HEX[verdict_of(trial.oor_label, trial.ir_label)] if reached else None,
                      far_mark=mark(trial.oor_label), near_mark=mark(trial.ir_label) if reached else None)
        caption = f"OOR {mark(trial.oor_label)}" + (f" · IR {mark(trial.ir_label)}" if reached else "")
        manifest.append(dict(panel=png.name, caption=caption, **provenance(path, index, trial)))
    target = pick["rel_path"].split("/")[1]
    preview(out_dir / "row2_negatives_preview.png", [[out_dir / m["panel"] for m in manifest]],
            col_labels=[f"{m['object']}   {m['caption']}" for m in manifest], row_labels=[""],
            note=f"posture formed for the {target}, {pick['rel_path'].split('/')[0]}")
    return manifest


def row_orientation(renderer, pick, sources, out_dir):
    """
    Participants by (object, orientation), every cell in the object's own frame.

    Each participant grasped each object at three orientations: the object's default,
    shared by everyone, and two turned about the vertical by amounts that vary between
    participants. Turning each trial back -- hand and object together, about the
    object's centre -- leaves the object identical in every cell and moves the hand to
    wherever that orientation put it relative to the object. Column 1 of each object is
    the default orientation, 2 and 3 the turned ones in order of turn. All at the in-reach
    keyframe, where the grasp is complete, and at one camera distance, so hands compare
    in size across the whole grid.

    One bubble per object overlays the first participant's three hands in the colours of
    the column chips, over the top of the grid.
    """
    subjects = pick["subjects"]
    slots = slot_dir(out_dir)
    object_color = hex_to_rgba(ORIENTATION_OBJECT_HEX, RENDER_DIM)

    cells = {}  # (subject, object, column) -> dict(path, trial, yaw, still)
    for object_name in ORIENTATION_OBJECTS:
        sessions = {s: load_sessions(s, object_name, sources) for s in subjects}
        reference = default_orientation(object_name, sessions)
        for subject, trials in sessions.items():
            row = []
            for path, trial in trials:
                rot = trial.obj_rot[trial.ir_frame]
                row.append(dict(path=path, trial=trial, yaw=yaw_between(reference, rot),
                                still=in_object_frame(trial, trial.ir_frame, reference)))
            # The default first, then the two turned orientations by how far they turned.
            row.sort(key=lambda c: (abs(c["yaw"]) > DEFAULT_TOLERANCE_DEG, c["yaw"]))
            for k, cell in enumerate(row, start=1):
                cells[subject, object_name, k] = cell
            print(f"  orientation: {subject:<4} {object_name:<7} turned "
                  + ", ".join(f"{c['yaw']:+.0f}" for c in row))

    # One camera distance and one crop per object: within an object's fifteen cells the
    # hands compare in size, and the apple is not shrunk to leave room for the teapot.
    camera = ORIENTATION_CAMERA
    for object_name in ORIENTATION_OBJECTS:
        group = [c for (_, o, _), c in cells.items() if o == object_name]
        distance = max(distance_for(renderer, aitviewer_utils.sequence_points(c["still"]), camera)
                       for c in group)
        for (subject, o, k), cell in cells.items():
            if o != object_name:
                continue
            cell["png"] = slots / f"row3_{subject}_{object_name}_{k}.png"
            still = cell["still"]
            nodes = (*hand_nodes(still.hand[0]),
                     aitviewer_utils.build_object_renderable(still, object_color))
            shoot(renderer, nodes, cell["png"], distance, camera)
        thumbs.common_crop([c["png"] for c in group])

    bubbles = {}
    for object_name in ORIENTATION_OBJECTS:
        stills = [cells[subjects[0], object_name, k]["still"] for k in (1, 2, 3)]
        nodes = [aitviewer_utils.build_object_renderable(stills[0], object_color)]
        for still, hex_color in zip(stills, ORIENTATION_HAND_HEX):
            # Undimmed: thin bones shade darker than a mesh face, and at RENDER_DIM the
            # three hues sink to navy, brown and bottle green.
            rgba = hex_to_rgba(hex_color)
            nodes += hand_nodes(still.hand[0], joint_color=rgba, bone_color=rgba)
        points = np.vstack([aitviewer_utils.sequence_points(s) for s in stills])
        bubbles[object_name] = slots / f"row3_bubble_{object_name}.png"
        shoot(renderer, nodes, bubbles[object_name], distance_for(renderer, points, camera), camera)

    png = out_dir / "row3_orientation_grid.png"
    compose_orientation_grid(png, cells, bubbles, subjects)
    return [dict(panel=png.name, caption=f"P{subjects.index(s) + 1} {o} {k}",
                 subject=s, yaw_from_default=round(c["yaw"]),
                 **provenance(c["path"], 0, c["trial"]))
            for (s, o, k), c in cells.items()]


def default_orientation(object_name, sessions):
    """
    The object's default orientation: the one every participant was shown. Each of
    them saw it once, alongside two orientations turned by amounts of their own, so it is
    the only rotation that recurs in every participant's sessions.
    """
    rotations = {s: [t.obj_rot[t.ir_frame] for _, t in trials] for s, trials in sessions.items()}
    first, *others = rotations.values()
    for candidate in first:
        if all(any(abs(yaw_between(candidate, r)) < DEFAULT_TOLERANCE_DEG for r in rs) for rs in others):
            return candidate
    sys.exit(f"No orientation of the {object_name} is shared by {', '.join(sessions)}")


def in_object_frame(trial, frame, reference):
    """
    One frame of a trial turned about the vertical so the object sits at `reference`,
    centred on the origin, with the hand carried round with it.
    """
    rot = trial.obj_rot[frame]
    turn = reference @ rot.T  # a turn about the vertical: the presets differ only in yaw
    centre = object_centre(trial, frame)
    return trial._replace(hand=((trial.hand[frame] - centre) @ turn.T)[np.newaxis],
                          obj_rot=reference[np.newaxis],
                          obj_trans=((trial.obj_trans[frame] - centre) @ turn.T)[np.newaxis])


def compose_orientation_grid(path, cells, bubbles, subjects):
    """
    The grid: object names and numbered colour chips on top, one row per participant
    (P1..., anonymised), the three objects' column groups separated by a gap and a rule,
    and the bubbles laid over the top rows of each group.
    """
    from PIL import Image, ImageDraw, ImageFilter

    # Each object's cells were cropped on their own; one cell height fits the tallest.
    cell_h = max(round(Image.open(c["png"]).height * CELL_PX / Image.open(c["png"]).width)
                 for c in cells.values())
    group_w = 3 * CELL_PX
    width = ROW_LABEL_PX + 3 * group_w + 2 * GROUP_GAP_PX + PANEL_MARGIN
    height = HEADER_PX + len(subjects) * cell_h + PANEL_MARGIN
    canvas = Image.new("RGB", (width, height), SURFACE)
    draw = ImageDraw.Draw(canvas)

    def column_x(g, k):  # left edge of object group g's column k (1-based)
        return ROW_LABEL_PX + g * (group_w + GROUP_GAP_PX) + (k - 1) * CELL_PX

    for g, object_name in enumerate(ORIENTATION_OBJECTS):
        draw.text((column_x(g, 1) + group_w // 2, 40), object_name, font=font(44), fill=INK, anchor="mm")
        for k, hex_color in enumerate(ORIENTATION_HAND_HEX, start=1):
            cx, cy = column_x(g, k) + CELL_PX // 2, HEADER_PX - 36
            draw.ellipse((cx - 30, cy - 12, cx - 6, cy + 12), fill=hex_color)
            draw.text((cx + 2, cy), str(k), font=font(LABEL_PX), fill=INK_SOFT, anchor="lm")
        if g:
            x = column_x(g, 1) - GROUP_GAP_PX // 2
            draw.line((x, HEADER_PX, x, height - PANEL_MARGIN), fill=SLOT_EDGE, width=3)
    for r, subject in enumerate(subjects):
        top = HEADER_PX + r * cell_h
        draw.text((ROW_LABEL_PX // 2, top + cell_h // 2), f"P{r + 1}", font=font(LABEL_PX),
                  fill=INK_SOFT, anchor="mm")
        for g, object_name in enumerate(ORIENTATION_OBJECTS):
            for k in (1, 2, 3):
                image = Image.open(cells[subject, object_name, k]["png"]).convert("RGB")
                image.thumbnail((CELL_PX, cell_h), Image.LANCZOS)
                canvas.paste(image, (column_x(g, k) + (CELL_PX - image.width) // 2,
                                     top + (cell_h - image.height) // 2))

    diameter = round(min(BUBBLE_CELLS * CELL_PX, BUBBLE_ROWS * cell_h))
    for g, object_name in enumerate(ORIENTATION_OBJECTS):
        bubble = circular_crop(Image.open(bubbles[object_name]).convert("RGB"), diameter)
        left = column_x(g, 2) + CELL_PX // 2 - diameter // 2
        top = HEADER_PX + BUBBLE_TOP_GAP_PX
        # A soft shadow under the bubble, so it reads as lying on top of the grid.
        shadow = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(shadow).ellipse((left, top + 10, left + diameter, top + diameter + 10), fill=70)
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        canvas.paste(Image.new("RGB", canvas.size, INK), mask=shadow)
        mask = Image.new("L", (diameter, diameter), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, diameter - 1, diameter - 1), fill=255)
        canvas.paste(bubble, (left, top), mask=mask)
        draw.ellipse((left, top, left + diameter - 1, top + diameter - 1), outline=BUBBLE_EDGE, width=5)
        draw.text((left + diameter // 2, top + diameter - 40), "P1, all three", font=font(28),
                  fill=INK_SOFT, anchor="mm")
    canvas.save(path)
    print(f"  orientation grid: {width}x{height} px, {len(cells)} cells")


def circular_crop(image, diameter):
    """
    A square around the image centre -- where the camera's target, the object's centre,
    lands -- just large enough to hold everything drawn, scaled to `diameter`.
    """
    from PIL import Image

    pixels = np.asarray(image).astype(int)
    ink = np.abs(pixels - pixels[0, 0]).max(axis=-1) > 8
    ys, xs = np.nonzero(ink)
    cy, cx = image.height / 2, image.width / 2
    radius = int(np.sqrt((ys - cy) ** 2 + (xs - cx) ** 2).max() * 1.08) + 8
    # Pad with the background rather than crop, which would fill any overhang with black.
    square = Image.new("RGB", (2 * radius, 2 * radius), tuple(int(v) for v in pixels[0, 0]))
    square.paste(image, (radius - int(cx), radius - int(cy)))
    return square.resize((diameter, diameter), Image.LANCZOS)


# --------------------------------------------------------------------------- panels

def slot_dir(out_dir):
    """Where the per-slot renders go before they are composed into panels."""
    path = out_dir / "slots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def slot_layout(far_png, near_png, far_resize):
    """
    Pixel geometry shared by every panel of a row: the far slot above, the near slot
    below, each a header band plus its picture. The far pictures are drawn at
    `far_resize` of their rendered size, which puts them at FAR_SCALE of the near
    pictures' scale however far each set's camera stood.
    """
    from PIL import Image

    fw, fh = Image.open(far_png).size
    far_size = (max(1, round(fw * far_resize)), max(1, round(fh * far_resize)))
    near_size = Image.open(near_png).size
    box_width = max(far_size[0], near_size[0]) + 2 * SLOT_PAD
    left, top = PANEL_MARGIN, PANEL_MARGIN
    far_box = (left, top, left + box_width, top + SLOT_HEADER + far_size[1] + SLOT_PAD)
    top = far_box[3] + SLOT_GAP
    near_box = (left, top, left + box_width, top + SLOT_HEADER + near_size[1] + SLOT_PAD)
    return dict(size=(box_width + 2 * PANEL_MARGIN, near_box[3] + PANEL_MARGIN),
                far_box=far_box, near_box=near_box, far_size=far_size, box_width=box_width)


def compose_panel(path, layout, *, near, far=None, far_outline=None, far_mark=None,
                  near_mark=None, header=None):
    """
    One panel from its slot renders. far_outline, a hex colour, draws the far object as
    a faint outline in it instead of solid. With `header` (an image) the panel has no
    slots: the header sits where the far slot would be and the near picture where it
    always is, so the panel still lines up with its neighbours.
    """
    from PIL import Image, ImageDraw

    canvas = Image.new("RGB", layout["size"], SURFACE)
    draw = ImageDraw.Draw(canvas)
    boxes = (layout["far_box"], layout["near_box"])
    if header is None:
        for box, label, glyph in zip(boxes, SLOT_LABELS, (far_mark, near_mark)):
            draw.rounded_rectangle(box, radius=28, outline=SLOT_EDGE, width=3)
            middle = box[1] + SLOT_HEADER // 2
            draw.text((box[0] + SLOT_PAD, middle), label, font=font(LABEL_PX), fill=INK_SOFT, anchor="lm")
            if glyph:
                draw.text((box[2] - SLOT_PAD, middle), glyph, font=font(MARK_PX), fill=INK, anchor="rm")
    else:
        box = layout["far_box"]
        canvas.paste(header, (box[0] + (layout["box_width"] - header.width) // 2,
                              box[1] + (box[3] - box[1] - header.height) // 2))
    if far is not None:
        image = Image.open(far).convert("RGB").resize(layout["far_size"], Image.LANCZOS)
        if far_outline:
            image = outline_of(image, far_outline)
        paste_in_slot(canvas, image, layout["far_box"], layout["box_width"])
    paste_in_slot(canvas, Image.open(near).convert("RGB"), layout["near_box"], layout["box_width"])
    canvas.save(path)


def paste_in_slot(canvas, image, box, box_width):
    canvas.paste(image, (box[0] + (box_width - image.width) // 2, box[1] + SLOT_HEADER))


def outline_of(image, hex_color):
    """The silhouette edge of what is drawn on `image`, as a faint line in hex_color."""
    from PIL import Image, ImageChops, ImageFilter

    background = Image.new("RGB", image.size, image.getpixel((0, 0)))
    mask = ImageChops.difference(image, background).convert("L").point(lambda v: 255 if v > 8 else 0)
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(OUTLINE_PX)),
                               mask.filter(ImageFilter.MinFilter(OUTLINE_PX)))
    out = Image.new("RGB", image.size, SURFACE)
    out.paste(Image.new("RGB", image.size, hex_color), mask=edge.point(lambda v: int(v * OUTLINE_ALPHA)))
    return out


_FONTS = {}


def font(px):
    """DejaVu Sans, as matplotlib ships it -- it has the check and cross glyphs."""
    from PIL import ImageFont
    from matplotlib import font_manager

    if px not in _FONTS:
        _FONTS[px] = ImageFont.truetype(font_manager.findfont("DejaVu Sans"), px)
    return _FONTS[px]


def colorbar_image(width_px):
    """The key for the overlay's tint, `width_px` wide, at the panels' type size."""
    import io

    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from PIL import Image

    dpi = 200
    pt = LABEL_PX * 72 / dpi
    fig = plt.figure(figsize=(width_px / dpi, 230 / dpi), dpi=dpi)
    ax = fig.add_axes([0.04, 0.34, 0.84, 0.2])  # room on the right for the "4 cm" label
    bar = fig.colorbar(ScalarMappable(Normalize(0, OFFSET_MAX_CM), offset_colormap()),
                       cax=ax, orientation="horizontal")
    bar.outline.set_visible(False)
    bar.set_ticks(np.arange(0, OFFSET_MAX_CM + 0.5, 1.0))
    bar.ax.tick_params(labelsize=pt, colors=INK_SOFT, length=0, pad=6)
    bar.ax.set_xticklabels([f"{t:g}" for t in bar.get_ticks()[:-1]] + [f"{OFFSET_MAX_CM:g} cm"])
    fig.text(0.04, 0.95, "joint moved from OOR (grey) to IR", fontsize=pt, color=INK, va="top")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


# --------------------------------------------------------------------------- sheets

def preview(path, grid, *, col_labels, row_labels, note):
    """A review sheet of one row's panels as the page would show them; not for the page."""
    import matplotlib.pyplot as plt

    images = [[plt.imread(p) for p in row] for row in grid]
    h, w = images[0][0].shape[:2]
    ncols, nrows = len(grid[0]), len(grid)
    cell_w = 2.6
    fig, axes = plt.subplots(nrows, ncols, squeeze=False,
                             figsize=(cell_w * ncols + 0.6, cell_w * h / w * nrows + 0.5))
    for r, row in enumerate(images):
        for c, image in enumerate(row):
            ax = axes[r][c]
            ax.imshow(image)
            ax.set_xticks([])
            ax.set_yticks([])
            for side in ax.spines.values():
                side.set_visible(False)
            if r == 0:
                ax.set_title(col_labels[c], fontsize=8.5, color=INK, pad=3)
            if c == 0 and row_labels[r]:
                ax.set_ylabel(row_labels[r], fontsize=8.5, color=INK)
    fig.text(0.01, 0.005, note, fontsize=7.5, color=INK_SOFT)
    fig.tight_layout(h_pad=0.4, w_pad=0.4)
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- main

ROW_FUNCTIONS = {"pose_gap": row_pose_gap, "negatives": row_negatives, "orientation": row_orientation}


def picks_for(row, n, sources):
    if row == "pose_gap":
        return pick_pose_gap(n)
    if row == "negatives":
        return pick_negatives(n)
    return pick_orientation(ORIENTATION_ROWS, sources)  # one grid; n does not apply


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rows", nargs="*", choices=ROWS, default=list(ROWS))
    p.add_argument("--candidates", type=int, default=0, metavar="N",
                   help="render the top N picks per row into candidates/ instead of the page panels")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--size", type=int, default=2000,
                   help="render resolution in pixels; panels are cropped from it (default: 2000)")
    return p.parse_args()


def main():
    args = parse_args()
    for needed, script in ((TRIALS_CSV, "scan_org_dataset.py"), (OFFSETS_CSV, "compute_pose_offsets.py")):
        if not needed.exists():
            sys.exit(f"No {needed} -- run {script} first")
    style()
    sources = dataset_utils.load_object_sources()
    renderer = build_renderer(args.size)

    if args.candidates:
        for row in args.rows:
            for k, pick in enumerate(picks_for(row, args.candidates, sources), start=1):
                out_dir = args.out_dir / "candidates" / row / f"{k}"
                out_dir.mkdir(parents=True, exist_ok=True)
                print(f"{row} candidate {k}: {pick}")
                ROW_FUNCTIONS[row](renderer, pick, sources, out_dir)
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for row in args.rows:
        pick = SHOWCASE[row] or picks_for(row, 1, sources)[0]
        print(f"{row}: {pick}")
        manifest += ROW_FUNCTIONS[row](renderer, pick, sources, args.out_dir)

    fields = list(dict.fromkeys(k for m in manifest for k in m))
    with open(args.out_dir / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest)
    print(f"wrote {len(manifest)} panels to {args.out_dir}")


if __name__ == "__main__":
    main()
