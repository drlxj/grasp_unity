#!/usr/bin/env python3
"""
Render a representative trial per object class off-screen, and tile them into a
contact sheet of the dataset.

The 3D viewer answers "what does this trial look like"; this answers "what is in here
at all". Both draw the same scene through visualize_collected_data, so a tile on the
sheet and the same trial opened interactively are the same picture from the same fixed
viewpoint -- the point of the wall is that thirty grasps can be compared side by side,
which only holds if nothing moves between them.

Each object appears in both of the roles it plays in the study:
  target       the participant was asked to grasp this object, and did (trial 0)
  replacement  this object was shown to a posture formed for something else, and the
               participant accepted it anyway

Usage:
  python render_org_dataset_thumbnails.py                 # both roles, 60 tiles
  python render_org_dataset_thumbnails.py --roles target  # 30 tiles
  python render_org_dataset_thumbnails.py --objects cup mug --size 720
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import visualize_collected_data as viz

MODEL_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = MODEL_DIR / "outputs" / "org_dataset" / "trials.csv"
DEFAULT_OUT = MODEL_DIR / "outputs" / "org_dataset"
ROLES = ("target", "replacement")


def choose_trials(csv_path, objects, roles):
    """
    One trial per (object, role), picked so the same call always renders the same wall.

    Among the trials that qualify, the one with the median frame count is taken. Length
    is a decent proxy for an unremarkable take: the shortest are cut off early and the
    longest are the ones where the participant hesitated or the tracking dropped, and
    the median is stable under a re-scan in a way that a random pick is not.
    """
    df = pd.read_csv(csv_path)
    df["verdict_ok"] = (df.oor_label == 1) & (df.ir_label == 1)
    picks = []
    for object_name in objects:
        for role in roles:
            if role == "target":
                pool = df[(df.trial_index == 0) & (df.obj_dir == object_name)]
            else:
                pool = df[(df.trial_index > 0) & (df.object_name == object_name)]
            pool = pool[pool.verdict_ok]
            if pool.empty:
                print(f"  skipping {object_name} / {role}: no accepted trial")
                continue
            pool = pool.sort_values(["n_frames", "rel_path", "trial_index"])
            picks.append((object_name, role, pool.iloc[len(pool) // 2]))
    return picks


def load_still(row, sources):
    """
    The one frame of a trial that gets rendered, as a single-frame Trial.

    That frame is the in-reach keyframe where there is one -- the posture the participant
    settled on with the object in hand -- and the out-of-reach keyframe otherwise, which
    is the only labelled moment in a trial that never came within reach.

    Slicing to one frame is also what makes the framing usable: viz.frame_camera fits
    every frame of a trial into shot, and for a full trial that includes the object at
    its out-of-reach distance, 1.6 m away, which leaves the hand a speck in the middle.
    """
    trial = viz.load_trial(viz.ORG_DATASET / Path(row.rel_path), int(row.trial_index), sources)
    frame = trial.ir_frame if trial.ir_frame is not None else trial.oor_frame
    return trial._replace(hand=trial.hand[frame:frame + 1],
                          obj_rot=trial.obj_rot[frame:frame + 1],
                          obj_trans=trial.obj_trans[frame:frame + 1]), frame


def fit_distance(renderer, still, camera):
    """How far the camera has to sit for this still to fit, in metres from the wrist."""
    width, height = renderer.window_size
    viz.frame_camera(renderer.scene.camera, still, *camera, aspect=width / height)
    return float(np.linalg.norm(renderer.scene.camera.position))


def render(renderer, still, out_path, camera, distance):
    """
    Render one still at a distance shared by the whole wall.

    Per-tile framing would size each hand to its own object, so the same hand would come
    out large beside a cup and small beside a frying pan -- which is exactly the
    comparison the wall exists to support. One distance for every tile, taken from the
    trial that needs the most room, keeps the hand at one scale throughout.
    """
    renderable = viz.build_renderables(still)
    renderer.scene.add(*renderable)
    renderer.scene.camera.target = np.zeros(3)
    renderer.scene.camera.position = viz.camera_direction(*camera) * distance
    renderer.scene.current_frame_id = 0
    renderer.save_frame(str(out_path))
    for node in renderable:
        renderer.scene.remove(node)


def common_crop(paths, pad=12):
    """
    Trim every tile to one box: the union of where any of them put ink, plus a margin.

    The camera looks at the wrist, so the hand sits at the same point in every frame and
    the object hangs off it in one direction. That leaves a band of background no tile
    ever uses, and cropping them all identically removes it without moving the hand
    relative to its neighbours.
    """
    from PIL import Image, ImageChops

    boxes = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        background = Image.new("RGB", image.size, image.getpixel((0, 0)))
        box = ImageChops.difference(image, background).convert("L").point(
            lambda v: 255 if v > 8 else 0).getbbox()
        if box:
            boxes.append(box)
    if not boxes:
        return
    width, height = Image.open(paths[0]).size
    union = (max(0, min(b[0] for b in boxes) - pad), max(0, min(b[1] for b in boxes) - pad),
             min(width, max(b[2] for b in boxes) + pad),
             min(height, max(b[3] for b in boxes) + pad))
    for path in paths:
        Image.open(path).crop(union).save(path)
    print(f"cropped {len(paths)} tiles to {union[2] - union[0]}x{union[3] - union[1]}")


def build_renderer(size):
    from aitviewer.headless import HeadlessRenderer

    renderer = HeadlessRenderer(size=(size, size))
    # Same three suppressions as the interactive viewer: everything is wrist-relative,
    # so the origin gizmo sits inside the hand and the floor slices through it.
    renderer.auto_set_camera_target = False
    renderer.auto_set_floor = False
    renderer.scene.origin.enabled = False
    renderer.scene.floor.enabled = False
    return renderer


def contact_sheet(tiles, out_path, ncols, dpi):
    """Tile the rendered PNGs into one sheet, captioned with object and role."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from plot_org_dataset_overview import INK, INK_SOFT, SURFACE, style

    style()
    nrows = int(np.ceil(len(tiles) / ncols))
    # Cell height follows the cropped tiles, which are no longer square, plus room for
    # the object name above and the provenance caption below.
    sample = plt.imread(tiles[0]["path"])
    cell_w = 2.05
    cell_h = cell_w * sample.shape[0] / sample.shape[1] + 0.62
    header_in = 0.72  # a fixed band for the heading, so it does not scale with the grid
    height = cell_h * nrows + header_in
    fig, axes = plt.subplots(nrows, ncols, squeeze=False,
                             figsize=(cell_w * ncols, height))
    for ax, tile in zip(np.ravel(axes), tiles):
        ax.imshow(plt.imread(tile["path"]))
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_color(SURFACE)
        ax.set_title(tile["object"], fontsize=8.5, color=INK, pad=3)
        ax.set_xlabel(tile["caption"], fontsize=7, color=INK_SOFT, labelpad=3)
    for ax in np.ravel(axes)[len(tiles):]:
        ax.axis("off")

    top = 1 - header_in / height
    fig.tight_layout(rect=(0, 0, 1, top), h_pad=1.6)
    fig.text(0.5, 1 - 0.22 / height, "One accepted grasp per object class",
             ha="center", va="top", fontsize=13, fontweight="bold")
    fig.text(0.5, 1 - 0.50 / height, "Every tile is the same fixed first-person viewpoint at "
             "the trial's labelled keyframe, so postures can be compared across objects.",
             ha="center", va="top", fontsize=8.5, color=INK_SOFT)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out_path}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--objects", nargs="*", default=None,
                   help="object classes to render (default: all 30)")
    p.add_argument("--roles", nargs="*", choices=ROLES, default=list(ROLES),
                   help="which role(s) to show each object in (default: both)")
    p.add_argument("--size", type=int, default=560, help="tile resolution in pixels")
    p.add_argument("--scale", choices=("shared", "per-tile"), default="shared",
                   help="'shared' puts every tile at one camera distance, so object sizes "
                        "are comparable but a watch is small; 'per-tile' fills each tile "
                        "with its own trial (default: shared)")
    p.add_argument("--ncols", type=int, default=6)
    p.add_argument("--dpi", type=int, default=170)
    return p.parse_args()


def main():
    args = parse_args()
    if not args.csv.exists():
        sys.exit(f"No {args.csv} -- run scan_org_dataset.py first")
    objects = args.objects or sorted(p.name for p in (viz.ORG_DATASET / "s1").iterdir() if p.is_dir())

    picks = choose_trials(args.csv, objects, args.roles)
    print(f"rendering {len(picks)} tiles at {args.size}px")

    frame_dir = args.out_dir / "thumbnails"
    frame_dir.mkdir(parents=True, exist_ok=True)
    sources = viz.load_object_sources()
    renderer = build_renderer(args.size)

    camera = (viz.CAMERA_AZIMUTH_DEG, viz.CAMERA_ELEVATION_DEG)
    stills = []
    for object_name, role, row in picks:
        still, frame = load_still(row, sources)
        stills.append((object_name, role, row, still))
        print(f"  {object_name}/{role}: {row.subject} trial {row.trial_index} frame {frame}")

    distances = [fit_distance(renderer, still, camera) for *_, still in stills]
    if args.scale == "shared":
        distances = [max(distances)] * len(distances)
        print(f"one camera distance for all tiles: {distances[0]:.2f} m from the wrist")

    tiles = []
    for (object_name, role, row, still), distance in zip(stills, distances):
        path = frame_dir / f"{object_name}_{role}.png"
        render(renderer, still, path, camera, distance)
        caption = (f"{row.subject}, grasping it" if role == "target"
                   else f"{row.subject}, posture from {row.obj_dir}")
        tiles.append(dict(path=path, object=object_name, caption=caption))

    # Only a shared distance leaves a band of background common to every tile; with
    # per-tile framing each one already fills its own frame.
    if args.scale == "shared":
        common_crop([tile["path"] for tile in tiles])

    suffix = "" if len(args.roles) == 2 else f"_{args.roles[0]}"
    contact_sheet(tiles, args.out_dir / f"fig7_thumbnail_wall{suffix}.png", args.ncols, args.dpi)


if __name__ == "__main__":
    main()
