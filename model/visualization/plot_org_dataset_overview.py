#!/usr/bin/env python3
"""
Static overview figures for dataset/ORG_dataset, from the CSV that scan_org_dataset.py
writes. Every figure is also written out as the CSV it was drawn from, so the numbers
can be read without the picture.

The recording protocol is what the figures have to make legible. One session is a
target object grasped out of reach (trial 0, positive by construction), followed by
five replacement objects shown to the same frozen hand posture (trials 1-5). Each
replacement is first judged at a distance (oorLabel) and, only if that judgement was
yes, pulled within reach and judged again (irLabel). So the two labels are a cascade,
not two independent binary targets, and the class balance that matters for training
is the one over trials 1-5 alone -- pooling trial 0 in triples the apparent positive
rate.

Usage: python plot_org_dataset_overview.py [--csv ...] [--out-dir ...] [--dpi 200]
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

# This file lives in model/visualization/; outputs stay in model/outputs/.
MODEL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CSV = MODEL_DIR / "outputs" / "org_dataset" / "trials.csv"
DEFAULT_OUT = MODEL_DIR / "outputs" / "org_dataset"

# The four verdicts of visualize_collected_data.verdict(), so a figure and a rendered
# trial agree on what a colour means. The hexes are that script's hues re-stepped for
# paper white: its values are pre-divided for a renderer running ambient_strength 2.0,
# and its amber comes out at 2.14:1 against white, under the 3:1 a filled mark needs.
#
# Validated as a set (all pairs): CVD Delta-E >= 12.6, normal-vision >= 15.2, contrast
# >= 3:1. UNSURE is the reserved neutral -- absence of a verdict, not a fifth series --
# which is why it alone carries no chroma.
COMPATIBLE = "#2e6fb4"   # oor 1, ir 1
BLOCKED = "#bf8613"      # oor 1, ir 0 -- judged workable at a distance, then defeated
INCOMPATIBLE = "#b0392e"  # oor 0
UNSURE = "#868c96"       # either label is 2

VERDICTS = ["compatible", "wrong orientation", "incompatible", "unsure"]
VERDICT_COLORS = {"compatible": COMPATIBLE, "wrong orientation": BLOCKED,
                  "incompatible": INCOMPATIBLE, "unsure": UNSURE}
VERDICT_LABELS = {
    "compatible": "compatible  (oor 1, ir 1)",
    "wrong orientation": "wrong orientation  (oor 1, ir 0)",
    "incompatible": "incompatible  (oor 0)",
    "unsure": "unsure  (label 2)",
}

INK = "#1a1a1a"
INK_SOFT = "#5c5c5c"
GRID = "#e4e4e2"
SURFACE = "#fcfcfb"

# A 2px surface gap between stacked segments, expressed as a linewidth in points.
SEGMENT_GAP = 1.5


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 9,
        "text.color": INK, "axes.labelcolor": INK, "axes.titlecolor": INK,
        "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
        "axes.edgecolor": GRID, "axes.linewidth": 0.8,
        "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
        "xtick.major.size": 0, "ytick.major.size": 0,
        "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False,
    })


def bare(ax, keep=()):
    """Strip the spines that are not doing work; the grid carries the scale."""
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


# Height of one line of deck text, in points; title() lifts the title by this per line.
DECK_LINE_PT = 12.5


def title(ax, text, subtitle=None):
    """
    Left-aligned heading with an optional grey deck above the axes.

    The deck is wrapped to the width of its own axes and the title's pad grown to clear
    it: matplotlib will otherwise let a long subtitle run out of its panel and across
    the next one, and a fixed pad puts the title on top of a two-line deck.
    """
    if subtitle:
        import textwrap
        # 8.5pt DejaVu Sans averages ~0.051 in per character, measured off a render.
        inches = ax.get_position().width * ax.figure.get_figwidth()
        wrap = max(28, int(inches / 0.051))
        subtitle = "\n".join(textwrap.fill(line, wrap) for line in subtitle.split("\n"))
        ax.text(0, 1.015, subtitle, transform=ax.transAxes, va="bottom", ha="left",
                fontsize=8.5, color=INK_SOFT, linespacing=1.45)
    lines = subtitle.count("\n") + 1 if subtitle else 0
    ax.set_title(text, loc="left", fontsize=11, fontweight="bold", pad=8 + DECK_LINE_PT * lines)
    return lines


def align_titles(fig, *panels):
    """
    Lower each (axes, deck line count) panel until every title sits at the same height.

    Side-by-side panels share an axes top, so a panel whose deck wraps to more lines
    carries its title higher than its neighbour. Moving that whole axes down by the
    difference -- rather than padding the shorter deck -- keeps each title tight to its
    own text and settles the busier panel level with the rest.
    """
    fewest = min(lines for _, lines in panels)
    for ax, lines in panels:
        shift = (lines - fewest) * DECK_LINE_PT / 72 / fig.get_figheight()
        if shift:
            pos = ax.get_position()
            ax.set_position([pos.x0, pos.y0 - shift, pos.width, pos.height])


def load(csv_path):
    df = pd.read_csv(csv_path)
    df["sid"] = df.subject.str[1:].astype(int)
    df["subject"] = pd.Categorical(df.subject, categories=[
        f"s{i}" for i in sorted(df.subject.str[1:].astype(int).unique())], ordered=True)
    df["verdict"] = np.select(
        [(df.ir_label == 2) | (df.oor_label == 2),
         (df.oor_label == 1) & (df.ir_label == 1),
         (df.oor_label == 1)],
        ["unsure", "compatible", "wrong orientation"],
        default="incompatible")
    df["is_target"] = df.trial_index == 0
    return df


def verdict_shares(df, by):
    """Verdict counts and row-normalised shares, grouped by one or more columns."""
    counts = (df.groupby(by, observed=True).verdict.value_counts().unstack(fill_value=0)
              .reindex(columns=VERDICTS, fill_value=0))
    return counts, counts.div(counts.sum(axis=1), axis=0)


def stacked_bars(ax, shares, counts=None, horizontal=True, label_min=0.08):
    """
    One stacked bar per row of `shares`, segments in VERDICTS order.

    Segments are separated by a surface-coloured hairline rather than an outline, and a
    percentage is drawn inside a segment only where it fits -- the rest is carried by
    the axis, the legend and the CSV beside the figure.
    """
    positions = np.arange(len(shares))
    offset = np.zeros(len(shares))
    for verdict in VERDICTS:
        width = shares[verdict].to_numpy()
        draw = ax.barh if horizontal else ax.bar
        kwargs = dict(color=VERDICT_COLORS[verdict], edgecolor=SURFACE,
                      linewidth=SEGMENT_GAP, zorder=3)
        if horizontal:
            draw(positions, width, left=offset, height=0.68, **kwargs)
        else:
            draw(positions, width, bottom=offset, width=0.68, **kwargs)
        for pos, w, off in zip(positions, width, offset):
            if w >= label_min:
                xy = (off + w / 2, pos) if horizontal else (pos, off + w / 2)
                ax.annotate(f"{w:.0%}", xy, ha="center", va="center",
                            fontsize=8, color="white", zorder=4)
        offset += width
    return positions


def legend(fig, ax, *, loc="upper center", ncol=4, bbox=None):
    handles = [Patch(facecolor=VERDICT_COLORS[v], label=VERDICT_LABELS[v]) for v in VERDICTS]
    ax.legend(handles=handles, loc=loc, ncol=ncol, bbox_to_anchor=bbox,
              fontsize=8.5, handlelength=0.9, handleheight=0.9, columnspacing=1.4,
              labelcolor=INK_SOFT)


def save(fig, out_dir, name, dpi):
    path = out_dir / f"{name}.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path.name}")
    return path


def table(frame, out_dir, name):
    path = out_dir / f"{name}.csv"
    frame.to_csv(path)
    return path


# --------------------------------------------------------------------------- figures

def fig_at_a_glance(df, out_dir, dpi):
    """
    The headline numbers, as tiles rather than a chart -- none of them is a comparison.

    The one that has to land is the last: the labels are per trial, and each trial marks
    exactly one out-of-reach keyframe plus, where the object was pulled in, one in-reach
    keyframe -- so well under one frame in a hundred carries a label.
    """
    labeled = df.n_labeled.sum() + df.n_in_reach.sum()
    per_cell = len(df) // (df.subject.nunique() * df.obj_dir.nunique())
    tiles = [
        ("SUBJECTS", f"{df.subject.nunique()}", "s1-s20, no s16"),
        ("OBJECT CLASSES", f"{df.obj_dir.nunique()}", "target and replacement both"),
        ("TRIALS", f"{len(df):,}", f"{per_cell} per subject x object, no gaps"),
        ("LABELED FRAMES", f"{labeled / df.n_frames.sum():.2%}",
         f"{labeled:,} of {df.n_frames.sum():,} frames"),
    ]
    # One axes rather than a subplot per tile: a caption can be wider than its column,
    # and in separate subplots that overflow drags the tight bounding box out sideways.
    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0, 1.06, "ORG_dataset at a glance", fontsize=13, fontweight="bold", va="top")
    ax.text(0, 0.93, "A fully crossed design: every subject grasped every one of the 30 objects, "
            "three times. The label lives on the trial, not the frame.",
            fontsize=8.5, color=INK_SOFT, va="top")
    for i, (label, value, note) in enumerate(tiles):
        x = i / len(tiles)
        ax.text(x, 0.66, " ".join(label), fontsize=7.5, color=INK_SOFT, va="top")
        ax.text(x, 0.46, value, fontsize=24, color=INK, va="center", fontweight="bold")
        ax.text(x, 0.10, note, fontsize=7.5, color=INK_SOFT, va="center")
        if i:
            ax.plot([x - 0.018, x - 0.018], [0.02, 0.72], color=GRID, lw=1.0, clip_on=False)
    return save(fig, out_dir, "fig1_at_a_glance", dpi)


def fig_label_cascade(df, out_dir, dpi):
    """
    What the two labels are, and why the positive rate depends on which trials you count.

    Left: the cascade as a set of stacked bars -- all trials, then split by role. Right:
    the same split per trial index, which shows the protocol directly. Trial 0 is the
    target object and is positive by construction; trials 1-5 sit flat at roughly one in
    twelve, with no drift over the course of a session.
    """
    counts_role, shares_role = verdict_shares(
        df.assign(role=np.where(df.is_target, "trial 0\ntarget object",
                                "trials 1-5\nreplacement objects")), "role")
    order = ["trial 0\ntarget object", "trials 1-5\nreplacement objects"]
    counts_role, shares_role = counts_role.loc[order], shares_role.loc[order]
    all_counts, all_shares = verdict_shares(df.assign(role="all trials"), "role")
    shares_role = pd.concat([all_shares, shares_role])
    counts_role = pd.concat([all_counts, counts_role])

    counts_idx, shares_idx = verdict_shares(df, "trial_index")

    fig, (ax_left, ax_right) = plt.subplots(
        1, 2, figsize=(13.5, 4.3), gridspec_kw={"width_ratios": [1, 1.15], "wspace": 0.22})

    pos = stacked_bars(ax_left, shares_role, horizontal=True)
    ax_left.set_yticks(pos)
    ax_left.set_yticklabels(
        [f"{i}\n{counts_role.iloc[k].sum():,} trials" for k, i in enumerate(shares_role.index)],
        fontsize=8.5)
    ax_left.invert_yaxis()
    ax_left.set_xlim(0, 1)
    ax_left.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax_left.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8)
    ax_left.grid(axis="x", zorder=0)
    bare(ax_left)
    lines_left = title(ax_left, "The positive rate depends on which trials you count",
          "Trial 0 is the participant grasping the object they were asked to grasp, so it is "
          "positive by design.\nPooling it in triples the apparent positive rate.")

    pos = stacked_bars(ax_right, shares_idx, horizontal=False, label_min=0.10)
    ax_right.set_xticks(pos)
    ax_right.set_xticklabels([f"trial {i}" for i in shares_idx.index], fontsize=8.5)
    ax_right.set_ylim(0, 1)
    ax_right.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax_right.set_yticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8)
    ax_right.grid(axis="y", zorder=0)
    bare(ax_right)
    lines_right = title(ax_right, "No drift across the five replacements",
          "Each replacement is judged out of reach first; only a yes is pulled within reach "
          "and judged again.\nSo oor 0 never reaches an ir label, and the pair is a cascade "
          "rather than two independent targets.")
    legend(fig, ax_right, loc="upper center", ncol=2, bbox=(0.5, -0.16))
    align_titles(fig, (ax_left, lines_left), (ax_right, lines_right))

    table(pd.concat([counts_role, counts_idx.set_index(
        pd.Index([f"trial {i}" for i in counts_idx.index]))]), out_dir, "fig3_label_cascade")
    return save(fig, out_dir, "fig3_label_cascade", dpi)


def fig_subject_bias(df, out_dir, dpi):
    """
    The finding a modeller has to see before splitting the data.

    Same protocol, same objects, same counts -- and the share of replacements a subject
    accepted runs from about 1 in 100 to 1 in 4. Bars run s1 to s20 in id order (the
    subject column is an ordered categorical), so a subject can be looked up directly.
    """
    distractors = df[~df.is_target]
    counts, shares = verdict_shares(distractors, "subject")

    fig, ax = plt.subplots(figsize=(13.5, 4.6))
    pos = stacked_bars(ax, shares, horizontal=False, label_min=0.12)
    ax.set_xticks(pos)
    ax.set_xticklabels(shares.index, fontsize=8.5)
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8)
    ax.grid(axis="y", zorder=0)
    bare(ax)

    # The two extremes are named in the deck rather than pinned to their bars: at these
    # shares the callout lands on top of the percentage already inside the segment.
    top, bottom = shares.compatible.idxmax(), shares.compatible.idxmin()
    hi, lo = shares.compatible[top], shares.compatible[bottom]

    title(ax, "Acceptance is a subject trait as much as an object property",
          f"Replacement trials only, {len(distractors):,} of them, {len(distractors) // len(shares)} per subject. "
          f"{top} accepted {hi:.0%} of the objects shown to them ({int(counts.compatible[top])} trials) "
          f"and {bottom} accepted {lo:.0%} ({int(counts.compatible[bottom])}) -- a {hi / lo:.0f}x spread "
          f"on identical stimuli.\nA random split leaks this; split by subject and the positive rate "
          "of a fold is largely set by who is in it.")
    legend(fig, ax, loc="upper center", ncol=4, bbox=(0.5, -0.09))

    table(counts, out_dir, "fig4_subject_bias")
    return save(fig, out_dir, "fig4_subject_bias", dpi)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                   help="trial index written by scan_org_dataset.py")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="where the figures go")
    p.add_argument("--dpi", type=int, default=200)
    return p.parse_args()


def main():
    args = parse_args()
    if not args.csv.exists():
        raise SystemExit(f"No {args.csv} -- run scan_org_dataset.py first")
    style()
    df = load(args.csv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"{len(df):,} trials -> {args.out_dir}")
    for figure in (fig_at_a_glance, fig_label_cascade, fig_subject_bias):
        figure(df, args.out_dir, args.dpi)


if __name__ == "__main__":
    main()
