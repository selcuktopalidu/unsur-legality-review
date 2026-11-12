"""Figure for the paper: outcome of the replay by kind of decision, with and without the Board's assessments."""
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
rows = [r for r in csv.DictReader(open(ROOT / "eval" / "results.csv", encoding="utf-8")) if r["split"] == "test"]

LABELS = {
    "affected_staff": "employee affected by the regulation",
    "own_records": "records about the applicant",
    "not_affected": "applicant not affected",
    "public_concern": "information of public concern",
    "not_internal": "not an internal regulation",
    "unclear": "applicant's status not stated",
    "former_staff": "former employee",
    "representative": "union or lawyer acting for staff",
    "candidate_or_member": "candidate or chamber member",
}
STATUS = [("agree", "same outcome as the Board", "#2a78d6", None),
          ("refer", "referred to a human", "#eb6834", "////"),
          ("disagree", "different outcome", "#1baf7a", "\\\\\\\\")]
HATCH_INK = {"refer": "#b5481d", "disagree": "#0f7d55"}   # a darker step of each fill
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

count = defaultdict(Counter)
for r in rows:
    count["board", r["pattern"]][r["status_board"]] += 1
    count["withheld", r["pattern"]][r["status_withheld"]] += 1
order = sorted(LABELS, key=lambda p: -sum(count["board", p].values()))

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "hatch.linewidth": 0.6,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK})
fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.75), sharey=True, gridspec_kw={"wspace": 0.06})
titles = {"board": "(a) with the Board's assessments", "withheld": "(b) assessments withheld"}
for ax, run in zip(axes, ("board", "withheld")):
    for i, p in enumerate(order):
        left = 0
        for key, _, color, hatch in STATUS:
            n = count[run, p][key]
            if not n:
                continue
            ax.barh(i, n, left=left, height=0.62, color=color, edgecolor="white", linewidth=1.0,
                    hatch=hatch, zorder=2)
            if hatch:   # re-draw the hatch in a tone of the fill so it survives grayscale print
                ax.barh(i, n, left=left, height=0.62, color="none", edgecolor=HATCH_INK[key], linewidth=0,
                        hatch=hatch, zorder=3)
            if n >= 2:
                ax.text(left + n / 2, i, str(n), ha="center", va="center", color="white" if key == "agree" else INK,
                        fontsize=7, zorder=4)
            left += n
    ax.set_title(titles[run], fontsize=8, color=INK, loc="left", pad=4)
    ax.set_xlim(0, 27)
    ax.set_xticks([0, 5, 10, 15, 20, 25])
    ax.xaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("decisions", color=MUTED)
axes[0].set_yticks(range(len(order)))
axes[0].set_yticklabels([LABELS[p] for p in order])
axes[0].invert_yaxis()
handles = [plt.Rectangle((0, 0), 1, 1, facecolor=c, edgecolor="white", hatch=h) for _, _, c, h in STATUS]
fig.legend(handles, [lab for _, lab, _, _ in STATUS], loc="upper center", ncol=3, frameon=False,
           bbox_to_anchor=(0.6, 1.03), fontsize=7.5, handlelength=1.6)
fig.savefig(ROOT / "eval" / "fig_replay.pdf", bbox_inches="tight")
fig.savefig(ROOT / "eval" / "fig_replay.png", bbox_inches="tight", dpi=200)
print("written")
