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
from org_style import (BONE_RGBA, INK, INK_SOFT, JOINT_RGBA, OFFSET_MAX_CM, SURFACE,
                       hex_to_rgba, offset_colormap, offset_rgba, style, verdict_of)

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
    # distance, headphones accepted, a game controller accepted and then defeated.
    "negatives": dict(rel_path="s10/bowl/20250729_100341/all_trials.json",
                      trials={"incompatible": 1, "compatible": 3, "wrong orientation": 2}),
    # pick_orientation's first choice: apple 9 degrees of hand turn across its three
    # orientations, banana 94, teapot 75 with the approach swinging round by 108.
    "orientation": dict(subject="s20"),
}
ROWS = tuple(SHOWCASE)

# No symmetry to adapt to / a long axis to follow / a handle to find.
ORIENTATION_OBJECTS = ("apple", "banana", "teapot")
# Left to right in the negatives row: rejected at a distance, accepted, accepted at a
# distance and then defeated once in reach.
NEGATIVE_ORDER = ("incompatible", "compatible", "wrong orientation")

# The viewer's first-person viewpoint, for the rows where the object is in the picture.
FIRST_PERSON = (viz.CAMERA_AZIMUTH_DEG, viz.CAMERA_ELEVATION_DEG)
# The posture row shows the hand alone, and from first person the fingers stack up
# behind one another. Nearly straight down, they fan out, and each out-of-reach finger
# lies beside its in-reach counterpart instead of behind it.
POSE_CAMERA = (200.0, 80.0)

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
        if set(NEGATIVE_ORDER) <= set(first.index) and target not in seen_targets:
            seen_targets.add(target)
            picks.append(dict(rel_path=rel_path, trials={v: int(first[v]) for v in NEGATIVE_ORDER}))
    return picks[:n]


def pick_orientation(n, sources):
    """
    Participants whose three objects show the contrast most clearly: the apple grasp
    barely turns with the apple, the banana and teapot grasps turn a lot, and the hand
    comes at the teapot from a different side each time.

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
    return [dict(subject=s) for s in df.subject.head(n)]


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


def provenance(trial_path, trial_index, frame, trial, **extra):
    return dict(rel_path=Path(trial_path).relative_to(ORG_DATASET).as_posix(),
                trial=trial_index, frame=frame, object=trial.object_name,
                oor_label=trial.oor_label, ir_label=trial.ir_label, **extra)


# --------------------------------------------------------------------------- rows

def row_pose_gap(renderer, pick, sources, out_dir):
    """
    Out-of-reach posture, in-reach posture, and the two overlaid.

    The hand alone, without the object: both panels would show the same object, once
    1.6 m away and once in hand, and the difference between those two pictures would
    swamp the few centimetres the row is about. The postures are aligned at the wrist by
    translation only, as compute_pose_offsets.py measures them, so the tint on each
    joint is the number in pose_offsets.csv.
    """
    path = ORG_DATASET / pick["rel_path"]
    trial = dataset_utils.load_trial(path, pick["trial"], sources)
    oor, ir = trial.hand[trial.oor_frame], trial.hand[trial.ir_frame]
    cm = np.linalg.norm(oor - ir, axis=1) * 100
    distance = distance_for(renderer, np.vstack([oor, ir]), POSE_CAMERA)

    panels = [
        ("oor", hand_nodes(oor), trial.oor_frame),
        ("ir", hand_nodes(ir), trial.ir_frame),
        ("overlay", (*hand_nodes(oor, joint_color=GHOST_RGBA, bone_color=GHOST_RGBA,
                                 scale=GHOST_SCALE, name="Out-of-reach hand"),
                     *hand_nodes(ir, joint_color=offset_rgba(cm), name="In-reach hand")),
         trial.ir_frame),
    ]
    manifest = []
    for name, nodes, frame in panels:
        png = out_dir / f"row1_pose_gap_{name}.png"
        shoot(renderer, nodes, png, distance, POSE_CAMERA)
        manifest.append(dict(panel=png.name, **provenance(path, pick["trial"], frame, trial)))
    thumbs.common_crop([out_dir / m["panel"] for m in manifest])
    colorbar(out_dir / "row1_pose_gap_colorbar.png")

    tips = [i + 1 for i in FINGERTIPS]  # the Trial's hand has the wrist prepended
    extension = (np.linalg.norm(oor[tips], axis=1) - np.linalg.norm(ir[tips], axis=1)).mean() * 100
    print(f"  pose_gap: {pick['rel_path']} trial {pick['trial']}  mean {cm[1:].mean():.2f} cm, "
          f"fingertips {cm[tips].mean():.2f} cm, out of reach {extension:+.2f} cm more extended")
    preview(out_dir / "row1_pose_gap_preview.png", [[out_dir / m["panel"] for m in manifest]],
            col_labels=["out of reach", "in reach", "overlaid, tinted by offset"], row_labels=[""],
            note=f"{trial.object_name}, {pick['rel_path'].split('/')[0]}")
    return manifest


def row_negatives(renderer, pick, sources, out_dir):
    """
    One session's frozen posture with three replacement objects, one per outcome.

    Each panel is at the in-reach keyframe where the object was brought in, and at the
    out-of-reach keyframe for the one that was turned down at a distance, which never
    came closer. All three share one camera distance, so the rejected object stands as
    far off as it did.
    """
    path = ORG_DATASET / pick["rel_path"]
    stills = []
    for verdict in NEGATIVE_ORDER:
        index = pick["trials"][verdict]
        trial = dataset_utils.load_trial(path, index, sources)
        frame = trial.ir_frame if trial.ir_frame is not None else trial.oor_frame
        stills.append((verdict, index, frame, trial, at_frame(trial, frame)))
    distance = max(distance_for(renderer, aitviewer_utils.sequence_points(s)) for *_, s in stills)

    manifest = []
    for verdict, index, frame, trial, still in stills:
        png = out_dir / f"row2_negatives_{verdict.replace(' ', '_')}.png"
        shoot(renderer, viz.build_renderables(still), png, distance)
        manifest.append(dict(panel=png.name, **provenance(path, index, frame, trial, verdict=verdict)))
        print(f"  negatives: {verdict:<18} {trial.object_name:<14} trial {index} frame {frame}")
    thumbs.common_crop([out_dir / m["panel"] for m in manifest])
    target = pick["rel_path"].split("/")[1]
    preview(out_dir / "row2_negatives_preview.png", [[out_dir / m["panel"] for m in manifest]],
            col_labels=[f"{m['object']}: {m['verdict']}" for m in manifest], row_labels=[""],
            note=f"posture formed for the {target}, {pick['rel_path'].split('/')[0]}")
    return manifest


def row_orientation(renderer, pick, sources, out_dir):
    """
    Three objects by the three orientations each was presented in, same participant.

    The in-reach keyframe, where the grasp is complete. The camera looks at the object
    rather than the wrist: the point is where the hand arrives around a fixed object,
    and a wrist-centred camera would instead hold the hand still and swing the object.
    Each object's orientations run left to right in order of how far it is turned from
    its first session; one camera distance serves all nine panels, so sizes compare.
    """
    subject = pick["subject"]
    grid = []
    for object_name in ORIENTATION_OBJECTS:
        sessions = load_sessions(subject, object_name, sources)
        first = sessions[0][1]
        base = first.obj_rot[first.ir_frame]
        cells = []
        for path, trial in sessions:
            frame = trial.ir_frame
            cells.append(dict(path=path, trial=trial, frame=frame,
                              yaw=yaw_between(base, trial.obj_rot[frame]),
                              still=at_frame(trial, frame, origin=object_centre(trial, frame))))
        grid.append(sorted(cells, key=lambda c: c["yaw"]))
    distance = max(distance_for(renderer, aitviewer_utils.sequence_points(c["still"]))
                   for row in grid for c in row)

    manifest = []
    for object_name, row in zip(ORIENTATION_OBJECTS, grid):
        for k, cell in enumerate(row, start=1):
            png = out_dir / f"row3_orientation_{object_name}_{k}.png"
            shoot(renderer, viz.build_renderables(cell["still"]), png, distance)
            manifest.append(dict(panel=png.name, yaw_from_first=round(cell["yaw"]),
                                 **provenance(cell["path"], 0, cell["frame"], cell["trial"])))
        print(f"  orientation: {subject} {object_name:<7} yaws "
              + ", ".join(f"{c['yaw']:+.0f}" for c in row))
    thumbs.common_crop([out_dir / m["panel"] for m in manifest])
    preview(out_dir / "row3_orientation_preview.png",
            [[out_dir / f"row3_orientation_{o}_{k}.png" for k in (1, 2, 3)] for o in ORIENTATION_OBJECTS],
            col_labels=["orientation 1", "orientation 2", "orientation 3"],
            row_labels=list(ORIENTATION_OBJECTS), note=f"participant {subject}")
    return manifest


# --------------------------------------------------------------------------- sheets

def colorbar(path):
    """The key for the overlay's tint, as its own small image for the page to place."""
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    fig, ax = plt.subplots(figsize=(3.2, 0.62))
    bar = fig.colorbar(ScalarMappable(Normalize(0, OFFSET_MAX_CM), offset_colormap()),
                       cax=ax, orientation="horizontal")
    bar.outline.set_visible(False)
    bar.set_ticks(np.arange(0, OFFSET_MAX_CM + 0.5, 1.0))
    bar.ax.tick_params(labelsize=8, colors=INK_SOFT, length=0, pad=3)
    bar.ax.set_xticklabels([f"{t:g}" for t in bar.get_ticks()[:-1]] + [f"{OFFSET_MAX_CM:g} cm"])
    ax.set_title("joint moved, out of reach → in reach", fontsize=8.5, color=INK, loc="left", pad=4)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


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
    return pick_orientation(n, sources)


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
