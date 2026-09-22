"""
The one palette and verdict rule shared by every ORG_dataset visualization, so that a
colour means the same thing in the 3D viewer, the overview charts and the project-page
figures.

Each verdict comes in two forms. The hexes are for paper white (matplotlib). The RGBA
values are the same hues for aitviewer, pre-divided by roughly 1.5: the scene runs at
ambient_strength 2.0, and feeding it the colour we actually want back comes out
fluorescent.
"""
import numpy as np

# Blue / amber / red rather than the usual green / red, which is the one pairing that
# red-green colour blindness collapses. These three also separate by lightness, so they
# survive being printed in greyscale: amber is light, blue mid, red dark.
VERDICTS = ["compatible", "wrong orientation", "incompatible", "unsure"]

# Validated as a set (all pairs): CVD Delta-E >= 12.6, normal-vision >= 15.2, contrast
# >= 3:1 against white. The renderer's amber is re-stepped darker here: at its own value
# it comes out at 2.14:1 on white, under the 3:1 a filled mark needs. UNSURE is the
# reserved neutral -- absence of a verdict, not a fifth series -- which is why it alone
# carries no chroma.
VERDICT_HEX = {
    "compatible": "#2e6fb4",         # oor 1, ir 1
    "wrong orientation": "#bf8613",  # oor 1, ir 0 -- judged workable at a distance, then defeated
    "incompatible": "#b0392e",       # oor 0
    "unsure": "#868c96",             # either label is 2
}
VERDICT_RGBA = {
    "compatible": (0.12, 0.29, 0.47, 1.0),
    "wrong orientation": (0.59, 0.43, 0.10, 1.0),
    "incompatible": (0.46, 0.15, 0.12, 1.0),
    "unsure": (0.41, 0.41, 0.41, 1.0),
}
VERDICT_LABELS = {
    "compatible": "compatible  (oor 1, ir 1)",
    "wrong orientation": "wrong orientation  (oor 1, ir 0)",
    "incompatible": "incompatible  (oor 0)",
    "unsure": "unsure  (label 2)",
}

# The object carries the verdict, so the hand is kept neutral: a coloured hand next to a
# coloured object leaves nothing for the eye to anchor on, and a blue hand beside a blue
# object is worse still. Dark bones, lighter joints, one grey family, no hue of its own.
BONE_RGBA = (0.26, 0.28, 0.32, 1.0)
JOINT_RGBA = (0.52, 0.55, 0.60, 1.0)

INK = "#1a1a1a"
INK_SOFT = "#5c5c5c"
GRID = "#e4e4e2"
SURFACE = "#fcfcfb"


def verdict_of(oor_label, ir_label):
    """
    The verdict name for a label pair, or an array of them for arrays of labels.

    Both labels are recorded once per trial, but at two different moments: oorLabel is
    the spoken judgement made while the object was still out of reach, irLabel whether
    the grasp actually worked once it was in reach. The pair (1, 0) is the interesting
    one -- judged workable, then defeated by the object's orientation -- and it is why
    this is not a yes/no.
    """
    oor, ir = np.asarray(oor_label), np.asarray(ir_label)
    names = np.select(
        [(ir == 2) | (oor == 2), (oor == 1) & (ir == 1), oor == 1],
        ["unsure", "compatible", "wrong orientation"],
        default="incompatible")
    return str(names) if names.ndim == 0 else names


def style():
    """matplotlib defaults for every ORG_dataset figure."""
    import matplotlib.pyplot as plt

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
