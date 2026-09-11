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

MODEL_DIR = Path(__file__).resolve().parent
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
SEQUENTIAL_HUE = COMPATIBLE  # magnitude ramp: one hue, light to dark

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
    keyframe. 2.1M frames of hand tracking is the raw material, 13k labelled postures is
    the supervision.
    """
    tiles = [
        ("SUBJECTS", f"{df.subject.nunique()}", "s1-s20, no s16"),
        ("OBJECT CLASSES", f"{df.obj_dir.nunique()}", "target and replacement both"),
        ("SESSIONS", f"{df.rel_path.nunique():,}", "3 per subject x object"),
        ("TRIALS", f"{len(df):,}", "6 per session, no gaps"),
        ("TRACKED FRAMES", f"{df.n_frames.sum() / 1e6:.2f}M", "hand + object pose"),
        ("LABELLED KEYFRAMES", f"{df.n_labeled.sum() + df.n_in_reach.sum():,}",
         f"{df.n_labeled.sum():,} out-of-reach, {df.n_in_reach.sum():,} in-reach"),
    ]
    # One axes rather than six: each tile's caption is wider than a sixth of the figure,
    # and in separate subplots that overflow drags the tight bounding box out sideways.
    fig, ax = plt.subplots(figsize=(13.5, 2.5))
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


def fig_trial_matrix(df, out_dir, dpi):
    """
    The 19 x 30 grid the brief asks for.

    Drawn as acceptance rate rather than trial count, because the count is 18 in every
    cell -- a heatmap of it is one flat colour. The imbalance in this dataset is not in
    how many trials were collected but in how often a replacement object was accepted,
    and that varies about tenfold across subjects and fivefold across objects.
    """
    distractors = df[~df.is_target]
    rate = (distractors.assign(hit=distractors.verdict.eq("compatible"))
            .pivot_table(index="subject", columns="obj_dir", values="hit",
                         aggfunc="mean", observed=True))
    counts = distractors.pivot_table(index="subject", columns="obj_dir",
                                     values="trial_index", aggfunc="size", observed=True)
    # Rows and columns sorted by their own margin, so the subject effect and the object
    # effect both read as a gradient instead of being scrambled by alphabetical order.
    rate = rate.loc[rate.mean(axis=1).sort_values().index,
                    rate.mean(axis=0).sort_values().index]

    fig = plt.figure(figsize=(13.5, 6.4))
    # The colour bar gets a column of its own. Handing it ax=ax_right instead makes it
    # take that space from the marginal, which collapses to a hairline.
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 0.11, 0.022], height_ratios=[0.16, 1],
                          wspace=0.035, hspace=0.03)
    ax = fig.add_subplot(gs[1, 0])
    ax_top = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax)
    cax = fig.add_subplot(gs[1, 2])

    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "compat", ["#f4f6f9", SEQUENTIAL_HUE])
    mesh = ax.pcolormesh(rate.to_numpy(), cmap=cmap, vmin=0, vmax=0.5,
                         edgecolors=SURFACE, linewidth=1.2)
    ax.set_xticks(np.arange(len(rate.columns)) + 0.5)
    ax.set_xticklabels(rate.columns, rotation=90, fontsize=7.5)
    ax.set_yticks(np.arange(len(rate.index)) + 0.5)
    ax.set_yticklabels(rate.index, fontsize=7.5)
    ax.invert_yaxis()
    bare(ax)
    ax.set_xlabel("target object  (sorted by mean acceptance)", fontsize=8.5, color=INK_SOFT)

    for axis, series, orient in ((ax_top, rate.mean(axis=0), "v"),
                                 (ax_right, rate.mean(axis=1), "h")):
        pos = np.arange(len(series)) + 0.5
        if orient == "v":
            axis.bar(pos, series, width=0.7, color=SEQUENTIAL_HUE, zorder=3)
            axis.set_ylim(0, max(series) * 1.15)
        else:
            axis.barh(pos, series, height=0.7, color=SEQUENTIAL_HUE, zorder=3)
            axis.set_xlim(0, max(series) * 1.15)
        bare(axis)
        axis.tick_params(labelbottom=False, labelleft=False, labelright=False)
        axis.grid(False)
    ax_top.set_ylabel("mean", fontsize=7.5, color=INK_SOFT, rotation=0, ha="right", va="center")
    ax_right.set_xlabel("mean", fontsize=7.5, color=INK_SOFT)

    bar = fig.colorbar(mesh, cax=cax)
    bar.outline.set_visible(False)
    bar.ax.tick_params(labelsize=7.5, length=0)
    bar.set_ticks([0, 0.25, 0.5])
    bar.set_ticklabels(["0%", "25%", "50%+"])
    bar.set_label("replacement objects accepted (oor 1, ir 1)", fontsize=8, color=INK_SOFT)

    per_cell = counts.to_numpy().min()
    # Placed inside the figure, in the band the gridspec leaves above the marginal, so
    # the heading does not push the tight bounding box out and open a gap under itself.
    fig.text(0, 0.995, "Where the imbalance actually is: acceptance rate per subject x target object",
             fontsize=12.5, fontweight="bold", va="top")
    fig.text(0, 0.948,
             f"Trial counts are uniform -- all {rate.size} cells hold exactly {per_cell} "
             f"replacement trials ({per_cell // 5} sessions x 5), which is why this is drawn as a "
             "rate and not a count.\nWhat varies is the verdict: pale rows are strict subjects, "
             "pale columns are objects almost nothing substitutes for.",
             fontsize=8.5, color=INK_SOFT, va="top", linespacing=1.45)

    table(rate, out_dir, "fig2_subject_object_matrix")
    return save(fig, out_dir, "fig2_subject_object_matrix", dpi)


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
    accepted runs from about 1 in 25 to nearly 1 in 2. Sorted by acceptance rather than
    by id, because subject number carries no meaning and sorting turns nineteen bars
    into a single readable gradient.
    """
    distractors = df[~df.is_target]
    counts, shares = verdict_shares(distractors, "subject")
    shares = shares.sort_values("compatible", ascending=False)
    counts = counts.loc[shares.index]

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
    top, bottom = shares.index[0], shares.index[-1]
    hi, lo = shares.compatible.iloc[0], shares.compatible.iloc[-1]

    title(ax, "Acceptance is a subject trait as much as an object property",
          f"Replacement trials only, {len(distractors):,} of them, {len(distractors) // len(shares)} per subject. "
          f"{top} accepted {hi:.0%} of the objects shown to them ({int(counts.compatible.iloc[0])} trials) "
          f"and {bottom} accepted {lo:.0%} ({int(counts.compatible.iloc[-1])}) -- a {hi / lo:.0f}x spread "
          f"on identical stimuli.\nA random split leaks this; split by subject and the positive rate "
          "of a fold is largely set by who is in it.")
    legend(fig, ax, loc="upper center", ncol=4, bbox=(0.5, -0.09))

    table(counts, out_dir, "fig4_subject_bias")
    return save(fig, out_dir, "fig4_subject_bias", dpi)


def fig_object_roles(df, out_dir, dpi):
    """
    Each object twice: as the target that set the hand posture, and as a replacement
    judged against someone else's posture.

    These are different questions and they rank differently. As a replacement, an object
    is asking "does an arbitrary grasp happen to fit me" -- which spheres and bottles
    answer yes to far more often than bowls and teapots do.
    """
    distractors = df[~df.is_target]
    as_target = verdict_shares(distractors, "obj_dir")[1].sort_values("compatible", ascending=True)
    shown_counts, as_shown = verdict_shares(distractors, "object_name")
    # Each panel is ranked by its own question -- that difference is the point of the
    # figure -- so the CSV beside it is the one that puts the two in a common row order.
    as_shown = as_shown.loc[as_target.index]

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(13.5, 7.4),
                                     gridspec_kw={"wspace": 0.30})
    for ax, shares, heading, sub in (
        (ax_l, as_target, "As the target that set the posture",
         "Of the five replacements shown to a grasp of this object,\nhow many were accepted?"),
        (ax_r, as_shown.sort_values("compatible"), "As the replacement being judged",
         "Of every posture this object was shown to,\nhow many accepted it?"),
    ):
        pos = stacked_bars(ax, shares, horizontal=True, label_min=0.11)
        ax.set_yticks(pos)
        ax.set_yticklabels(shares.index, fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8)
        ax.grid(axis="x", zorder=0)
        bare(ax)
        title(ax, heading, sub)

    legend(fig, ax_r, loc="upper center", ncol=4, bbox=(-0.18, -0.06))
    fig.suptitle("The same 30 objects, ranked by the two different questions they answer",
                 x=0.125, y=1.005, ha="left", fontsize=12, fontweight="bold")

    table(pd.concat({"as_target": as_target, "as_shown": as_shown}, axis=1),
          out_dir, "fig5_object_roles")
    return save(fig, out_dir, "fig5_object_roles", dpi)


def fig_pair_coverage(df, out_dir, dpi):
    """
    How the 870 ordered (target, replacement) pairs were sampled, and how they scored.

    Worth a panel because the pairing is the experiment's real independent variable and
    it was randomised per session: every off-diagonal pair occurs, but between 2 and 20
    times, so a per-pair acceptance rate is a noisy estimate at the low end.
    """
    distractors = df[~df.is_target]
    shown = distractors.pivot_table(index="obj_dir", columns="object_name",
                                    values="trial_index", aggfunc="size")
    accepted = (distractors.assign(hit=distractors.verdict.eq("compatible"))
                .pivot_table(index="obj_dir", columns="object_name", values="hit", aggfunc="sum"))

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(13.5, 5.6),
                                     gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.24})

    per_pair = shown.to_numpy()[~np.isnan(shown.to_numpy())]
    bins = np.arange(per_pair.min(), per_pair.max() + 2) - 0.5
    ax_l.hist(per_pair, bins=bins, color=SEQUENTIAL_HUE, zorder=3,
              edgecolor=SURFACE, linewidth=1.2)
    ax_l.grid(axis="y", zorder=0)
    bare(ax_l)
    ax_l.set_xlabel("times this pair was shown", fontsize=8.5, color=INK_SOFT)
    ax_l.set_ylabel("ordered object pairs", fontsize=8.5, color=INK_SOFT)
    ax_l.tick_params(labelsize=8)
    title(ax_l, "Every pair occurs, none of them often",
          f"All {int(np.isfinite(shown.to_numpy()).sum())} off-diagonal pairs of the 30x30 grid "
          f"were sampled\n(median {int(np.nanmedian(shown.to_numpy()))}, "
          f"range {int(per_pair.min())}-{int(per_pair.max())}). An object is never its own replacement.")

    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("compat", ["#f4f6f9", SEQUENTIAL_HUE])
    order = accepted.sum(axis=1).sort_values().index
    mesh = ax_r.pcolormesh(accepted.loc[order, order].to_numpy(), cmap=cmap,
                           edgecolors=SURFACE, linewidth=0.6)
    ax_r.set_xticks(np.arange(len(order)) + 0.5)
    ax_r.set_xticklabels(order, rotation=90, fontsize=6.5)
    ax_r.set_yticks(np.arange(len(order)) + 0.5)
    ax_r.set_yticklabels(order, fontsize=6.5)
    ax_r.invert_yaxis()
    bare(ax_r)
    ax_r.set_xlabel("replacement shown", fontsize=8.5, color=INK_SOFT)
    ax_r.set_ylabel("posture came from", fontsize=8.5, color=INK_SOFT)
    bar = fig.colorbar(mesh, ax=ax_r, fraction=0.04, pad=0.02)
    bar.outline.set_visible(False)
    bar.ax.tick_params(labelsize=7.5, length=0)
    bar.set_label("accepted trials", fontsize=8, color=INK_SOFT)
    title(ax_r, "Which substitutions actually worked",
          "Rows and columns are both sorted by row total, so the pale band across the top "
          "is the postures nothing else satisfied.\nCounts rather than rates, because most "
          "pairs have single-digit samples.")

    table(shown, out_dir, "fig6_pair_shown")
    table(accepted, out_dir, "fig6_pair_accepted")
    return save(fig, out_dir, "fig6_pair_coverage", dpi)


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
    for figure in (fig_at_a_glance, fig_trial_matrix, fig_label_cascade,
                   fig_subject_bias, fig_object_roles, fig_pair_coverage):
        figure(df, args.out_dir, args.dpi)


if __name__ == "__main__":
    main()
