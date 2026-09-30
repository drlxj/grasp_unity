#!/usr/bin/env python3
"""
A grasp stage rendered in Blender: export a set of cells, set them out on one floor,
photograph them, and lay the picture on the page's background.

  --set showcase   the grasp figure: eight objects, one per cluster of the paper, five
                   distinct grasps each (render_showcase_rows.row_grasps' choice)
  --set all        the whole dataset: 30 objects by cluster, every in-reach grasp of
                   each, similar grasps together down each column

Usage (grasping env):
  python make_grasp_stage.py --set all                          # export, render, compose
  python make_grasp_stage.py --set all --skip-export --save-blend
  python make_grasp_stage.py --set all --skip-export --frame-cols 0 11 --frame-rows 0 8
  python make_grasp_stage.py --set showcase --skip-export --width 1600 --samples 32
  python make_grasp_stage.py --set all --skip-export --low     # low, slanting, 16:9

Writes <out-dir>/stage_<set>_<hand>[_c<cols>_r<rows>].png, the suffix naming the
framed cells if not all; the raw render, label positions and (with --save-blend) the
.blend scene stay in a folder of the same name.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import render_showcase_rows as rows
from org_style import INK, SURFACE

import export_grasp_scenes

BLENDER = Path(os.environ.get("BLENDER", r"D:\AppsData\STEAM\steamapps\common\Blender\blender.exe"))

# Shadow alpha under this is dropped, and what is above it rescaled to start from zero:
# the world light leaves a faint haze of shadow that would otherwise reach the crop.
SHADOW_FLOOR = 0.06
MARGIN = 0.02      # around the stage, as a share of the render's width
TITLE_BAND = 0.05  # the band above the stage for column titles, same unit
TITLE_SIZE = 0.013
# The low view: a camera near the ground with a wide lens, swung round to look across
# the ranks at a slant, row 1 at the front and the rest receding, in a video's 16:9.
# (--orbit 0 looks straight down the files instead.)
LOW_VIEW = ["--elevation", "15", "--orbit", "35", "--fov", "40", "--aspect", "1.7778", "--first-row", "near"]


def render(scenes, out_dir, args):
    cmd = [str(args.blender), "-b", "--factory-startup", "--python", str(HERE / "render_grasps.py"), "--",
           "--scenes", str(scenes), "--out", str(out_dir), "--width", str(args.width),
           "--samples", str(args.samples), "--hand", args.hand, "--fov", str(args.fov), "--rows", args.rows]
    for flag in ("frame_cols", "frame_rows"):
        if getattr(args, flag):
            cmd += ["--" + flag.replace("_", "-"), *map(str, getattr(args, flag))]
    if args.save_blend:
        cmd.append("--save-blend")
    for flag in ("elevation", "orbit", "aspect"):
        if getattr(args, flag) is not None:
            cmd += ["--" + flag, str(getattr(args, flag))]
    cmd += ["--first-row", args.first_row]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    log = []
    for line in proc.stdout:
        log.append(line)
        if line.startswith(("BUILT", "LAID OUT", "RENDERED")):
            print("  " + line.strip(), flush=True)
    if proc.wait() or not any(line.startswith("RENDERED") for line in log):
        sys.exit("Blender failed:\n" + "".join(log[-40:]))


def compose(stage_dir, path, titles, crop=True):
    """
    The render on the page's background, cropped to what is drawn (unless not `crop`,
    for a frame of fixed shape), titles optional.
    """
    from PIL import Image, ImageDraw, ImageFilter

    image = Image.open(stage_dir / "stage.png").convert("RGBA")
    cut = round(SHADOW_FLOOR * 255)
    alpha = image.getchannel("A").point(lambda a: max(0, round((a - cut) * 255 / (255 - cut))))
    image.putalpha(alpha)
    # The crop follows what is drawn, less isolated specks: a stray bright sample at the
    # frame's edge would otherwise stretch the crop out to it.
    ink = alpha.point(lambda a: 255 if a > 0 else 0).filter(ImageFilter.MinFilter(7))
    left, top, right, bottom = ink.getbbox() if crop else (0, 0, image.width, image.height)

    margin = round(MARGIN * image.width) if crop else 0
    band = round(TITLE_BAND * image.width) if titles else 0
    box = (max(0, left - margin), max(0, top - margin),
           min(image.width, right + margin), min(image.height, bottom + margin))
    canvas = Image.new("RGBA", (box[2] - box[0], box[3] - box[1] + band), SURFACE)
    canvas.alpha_composite(image.crop(box), (0, band))
    if titles:
        draw = ImageDraw.Draw(canvas)
        font = rows.font(round(TITLE_SIZE * image.width))
        for label in json.loads((stage_dir / "labels.json").read_text(encoding="utf-8")):
            draw.text((label["x"] - box[0], band // 2), label["title"], font=font, fill=INK, anchor="mm")
    canvas.convert("RGB").save(path)
    print(f"  stage: {canvas.width}x{canvas.height} px -> {path}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set", choices=("showcase", "all"), default="all")
    p.add_argument("--out-dir", type=Path, default=export_grasp_scenes.OUT_ROOT)
    p.add_argument("--skip-export", action="store_true", help="reuse <out-dir>/scenes_<set>")
    p.add_argument("--width", type=int, default=4000, help="render width in pixels")
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--fov", type=float, help="vertical field of view in degrees (default: 20, or 40 --low)")
    p.add_argument("--hand", choices=("skeleton", "skin"), default="skeleton")
    p.add_argument("--rows", choices=("level", "packed"), default="level",
                   help="rows straight across the stage, or each column packed on its own")
    p.add_argument("--frame-cols", nargs=2, type=int, metavar=("START", "END"),
                   help="frame only these columns (0-based, end excluded)")
    p.add_argument("--frame-rows", nargs=2, type=int, metavar=("START", "END"),
                   help="frame only these rows (0-based, end excluded)")
    p.add_argument("--save-blend", action="store_true", help="also save the scene as a .blend")
    p.add_argument("--titles", action="store_true", help="name the columns above the stage")
    p.add_argument("--elevation", type=float, help="camera elevation in degrees (default: 60)")
    p.add_argument("--orbit", type=float, help="degrees the camera swings round from the grid's azimuth")
    p.add_argument("--aspect", type=float, help="fixed frame width over height; the frame is then not cropped")
    p.add_argument("--first-row", choices=("far", "near"), default="far")
    p.add_argument("--low", action="store_true",
                   help=f"shorthand for the low slanting view: {' '.join(LOW_VIEW)}")
    p.add_argument("--blender", type=Path, default=BLENDER)
    args = p.parse_args()
    if args.low:  # the preset fills in only what was not given explicitly
        preset = p.parse_args(LOW_VIEW)
        for key in ("elevation", "orbit", "fov", "aspect"):
            if getattr(args, key) is None:
                setattr(args, key, getattr(preset, key))
        args.first_row = "near"
    if args.fov is None:
        args.fov = 20.0

    scenes = args.out_dir / f"scenes_{args.set}"
    name = f"stage_{args.set}_{args.hand}" + (f"_low_o{args.orbit:g}" if args.low else "")
    if args.frame_cols or args.frame_rows:
        name += "_c{}-{}_r{}-{}".format(*(args.frame_cols or ("", "")), *(args.frame_rows or ("", "")))
    if not args.skip_export:
        import dataset_utils
        export_grasp_scenes.export(scenes, args.set, dataset_utils.load_object_sources())
    render(scenes, args.out_dir / name, args)
    compose(args.out_dir / name, args.out_dir / f"{name}.png", args.titles, crop=args.aspect is None)


if __name__ == "__main__":
    main()
