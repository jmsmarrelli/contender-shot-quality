"""Every chart in the repo, drawn from the tables stage 3 has already written.

Keeping the drawing here rather than inline in the run script means a figure can
be re-cut without refitting anything, and it keeps the analysis readable.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D

import style as st
from config import CONTENDERS, FIG, FULL_NAME, REPORT_SEASON, SUBJECT

SEVEN = [SUBJECT] + CONTENDERS
DIV = LinearSegmentedColormap.from_list("div", st.DIVERGING[::-1])

# A few contenders land close enough together in 2024-25 that their labels would
# sit on top of each other. Nudges are in points, and only these five are moved.
LABEL_NUDGE = {
    ("offence", "LAL"): (-19, 4), ("offence", "OKC"): (17, 6),
    ("defence", "LAL"): (-19, 4), ("defence", "DEN"): (12, 7),
    ("defence", "SAS"): (24, -3),
}

ZONE_ORDER = ["Restricted Area", "In The Paint (Non-RA)", "Mid-Range",
              "Left Corner 3", "Right Corner 3", "Above the Break 3"]
ZONE_SHORT = {"Restricted Area": "Rim", "In The Paint (Non-RA)": "Paint",
              "Mid-Range": "Mid-range", "Left Corner 3": "Corner 3 (L)",
              "Right Corner 3": "Corner 3 (R)", "Above the Break 3": "Above break 3"}


def _season_label(end_year: int) -> str:
    return f"{end_year - 1}-{str(end_year)[2:]}"


def _team_colour(team: str) -> str:
    if team == SUBJECT:
        return st.SPURS
    return st.SERIES[CONTENDERS.index(team) % len(st.SERIES)]


# --------------------------------------------------------------------------
def fig_scatter(off: pd.DataFrame, deff: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.3))
    panels = [("offence", off, "Offence", "better"), ("defence", deff, "Defence", "worse")]

    both = pd.concat([off, deff])
    both = both[both["season"] == REPORT_SEASON]
    lim = max(both["quality"].abs().max(), both["making"].abs().max()) * 1.18

    for ax, (side, tbl, label, direction) in zip(axes, panels):
        sel = tbl[tbl["season"] == REPORT_SEASON]

        for c in (-8, -4, 0, 4, 8):
            ax.plot([-lim, lim], [c + lim, c - lim], color=st.GRID, lw=0.8,
                    zorder=0, solid_capstyle="butt")
        ax.axhline(0, color=st.INK_3, lw=0.9, zorder=1)
        ax.axvline(0, color=st.INK_3, lw=0.9, zorder=1)

        rest = sel[~sel["team"].isin(SEVEN)]
        ax.scatter(rest["quality"], rest["making"], s=26, color=st.NEUTRAL, zorder=2)

        for _, r in sel[sel["team"].isin(SEVEN)].iterrows():
            col = _team_colour(r["team"])
            ax.scatter([r["quality"]], [r["making"]], s=74, color=col, zorder=4,
                       edgecolor=st.SURFACE, linewidth=1.2)
            dx, dy = LABEL_NUDGE.get((side, r["team"]), (0, 10))
            ax.annotate(r["team"], (r["quality"], r["making"]),
                        textcoords="offset points", xytext=(dx, dy),
                        ha="center", fontsize=8.6, fontweight="semibold",
                        color=col, zorder=5)

        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.set_xlabel("shot quality")
        ax.set_ylabel("shot making")
        st.titled(ax, label, f"diagonals are equal total value; up and right is {direction}")
        st.strip(ax, keep=())

    st.caption(fig,
               f"Points per 100 attempts against the {REPORT_SEASON - 1}-{str(REPORT_SEASON)[2:]} "
               "league. Quality is the expected value of the shots taken, scored out of fold by a "
               "model of geometry alone; making is what the shooters did with them. On the defence "
               "panel both axes are what the opponent got, so down and left is the good corner.",
               y=-0.06)
    fig.savefig(FIG / "01_quality_and_making.png")
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_reliability(curve: pd.DataFrame, series_att: int) -> None:
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    x = curve["half_size"]

    ax.plot(x, curve["quality_half"], color=st.SERIES[0], marker="o", ms=4.5,
            label="shot quality")
    ax.plot(x, curve["making_half"], color=st.SERIES[1], marker="o", ms=4.5,
            label="shot making")

    ax.axvline(series_att, color=st.INK_2, lw=1.0, ls=(0, (4, 3)), zorder=1)
    ax.annotate(f"an illustrative sample\n{series_att} attempts",
                (series_att, 0.03), xytext=(9, 0), textcoords="offset points",
                fontsize=8.2, color=st.INK_2, va="bottom")

    row = curve[curve["half_size"] == series_att].iloc[0]
    for col, colour in (("quality_half", st.SERIES[0]), ("making_half", st.SERIES[1])):
        ax.scatter([series_att], [row[col]], s=66, color=colour, zorder=5,
                   edgecolor=st.SURFACE, linewidth=1.4)
        ax.annotate(f"{row[col]:.2f}", (series_att, row[col]),
                    xytext=(-6, 8), textcoords="offset points", ha="right",
                    fontsize=8.6, fontweight="semibold", color=colour)

    ax.set_xscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{int(v):,}" for v in x])
    ax.minorticks_off()
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("attempts in each half")
    ax.set_ylabel("correlation between the two halves")
    ax.legend(loc="lower right")
    st.titled(ax, "Within-season split-sample consistency",
              "two disjoint samples from the same team-season, averaged over 60 random splits")
    st.strip(ax)
    small = curve.iloc[0]
    st.caption(fig, 'Two disjoint random samples of attempts from the same team-season. These are spread across a season, not consecutive games or an early-season forecast. The common eligible team-season cohort is fixed across sample sizes.')
    fig.savefig(FIG / "02_reliability_curve.png")
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_contender_bars(view: pd.DataFrame) -> None:
    """Quality and making side by side rather than stacked.

    They are stacked in the arithmetic - the two add to the total - but stacking
    them in the picture hides the shorter bar whenever the two point in opposite
    directions, which is exactly the case worth looking at. So they get their own
    rows and the total goes in the label.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.2), sharex=True)
    for ax, side in zip(axes, ("offence", "defence")):
        best_first = side == "offence"
        sel = view[view["side"] == side].sort_values("total", ascending=not best_first)
        sel = sel.iloc[::-1]                      # barh draws upward from zero
        y = np.arange(len(sel))

        ax.barh(y + 0.19, sel["quality"], height=0.33, color=st.SERIES[0], zorder=3)
        ax.barh(y - 0.19, sel["making"], height=0.33, color=st.SERIES[1], zorder=3)
        ax.axvline(0, color=st.INK_3, lw=0.9, zorder=4)

        ax.set_yticks(y)
        ax.set_yticklabels([f"{t}   {v:+.1f}" for t, v in zip(sel["team"], sel["total"])],
                           fontsize=9.2)
        for tick, team in zip(ax.get_yticklabels(), sel["team"]):
            tick.set_color(_team_colour(team))
            tick.set_fontweight("bold" if team == SUBJECT else "semibold")
        ax.set_ylim(-0.62, len(sel) - 0.38)
        ax.set_xlim(-8.4, 8.4)
        sub = ("best at the top; up is more scoring" if side == "offence"
               else "best at the top; up is more scoring allowed")
        st.titled(ax, side.capitalize(), sub)
        ax.set_xlabel("points per 100 attempts vs league")
        st.strip(ax, keep=("bottom",))
        ax.grid(axis="y", visible=False)

    handles = [Line2D([], [], color=st.SERIES[0], lw=7, label="shot quality"),
               Line2D([], [], color=st.SERIES[1], lw=7, label="shot making")]
    axes[1].legend(handles=handles, loc="lower right")
    st.caption(fig,
               f"{REPORT_SEASON - 1}-{str(REPORT_SEASON)[2:]}. The number beside each team is the "
               "two bars added together. San Antonio is the clearest case of the two pulling "
               "against each other: the sixth-best looks in the league on offence, and 20th at "
               "converting them.",
               y=-0.03)
    fig.savefig(FIG / "03_contender_split.png")
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_series_bands(sim: pd.DataFrame, series_att: int) -> None:
    sel = sim.sort_values("season_making").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9.0, 7.4))

    for i, r in sel.iterrows():
        highlight = r["team"] in SEVEN
        col = _team_colour(r["team"]) if highlight else st.NEUTRAL
        ax.plot([r["p05"], r["p95"]], [i, i], color=col,
                lw=4.2 if highlight else 2.6, solid_capstyle="round",
                alpha=1.0 if highlight else 0.85, zorder=3 if highlight else 2)
        ax.plot([r["season_making"]], [i], marker="|", ms=13,
                color=st.SURFACE, mew=2.2, zorder=4)
        ax.plot([r["season_making"]], [i], marker="o", ms=4.6,
                color=st.INK if highlight else st.INK_3, zorder=5)

    ax.axvline(0, color=st.INK_3, lw=0.9, zorder=1)
    ax.set_yticks(range(len(sel)))
    ax.set_yticklabels(sel["team"])
    for tick, team in zip(ax.get_yticklabels(), sel["team"]):
        if team in SEVEN:
            tick.set_fontweight("bold")
            tick.set_color(_team_colour(team))
    ax.set_ylim(-0.8, len(sel) - 0.2)
    ax.set_xlabel("shot making, points per 100 attempts vs league")
    st.titled(ax, "Uncertainty in independent shot resamples",
              f"dot: the {REPORT_SEASON - 1}-{str(REPORT_SEASON)[2:]} season figure. bar: the middle "
              f"90% of {series_att}-attempt resamples of that same season")
    st.strip(ax, keep=("bottom",))
    ax.grid(axis="y", visible=False)
    covers = int(((sel["p05"] <= 0) & (sel["p95"] >= 0)).sum())
    ends = "even the top and bottom bands overlap" if sel["p05"].iloc[0] <= sel["p95"].iloc[-1] \
        else "the top and bottom bands are the only pair that do not overlap"
    st.caption(fig, 'Independent resamples from each team’s observed regular-season shots. This illustrative sample-size exercise omits opponent adjustments, within-game dependence, changing rotations and playoff tactics. Overlapping bands do not establish equality or simulate a playoff series.')
    fig.savefig(FIG / "04_series_bands.png")
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_zone_surplus(zones: pd.DataFrame) -> None:
    grid = (zones[zones["team"].isin(SEVEN)]
            .pivot(index="team", columns="zone", values="surplus")
            .reindex(index=SEVEN, columns=ZONE_ORDER)
            .fillna(0.0))
    tot = grid.sum(axis=1)
    order = tot.sort_values(ascending=False).index
    grid, tot = grid.loc[order], tot.loc[order]

    fig, ax = plt.subplots(figsize=(9.8, 4.6))
    lim = float(np.abs(grid.to_numpy()).max())
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim)
    ax.imshow(grid.to_numpy(), cmap=DIV, norm=norm, aspect="auto")

    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid.iat[i, j]
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8.4,
                    color=st.SURFACE if abs(v) > 0.62 * lim else st.INK)
        ax.text(grid.shape[1] - 0.32, i, f"{tot.iat[i]:+.2f}", ha="left", va="center",
                fontsize=9.0, fontweight="semibold", color=st.INK)

    ax.set_xticks(range(grid.shape[1]))
    ax.set_xticklabels([ZONE_SHORT[z] for z in grid.columns], fontsize=8.6)
    ax.set_yticks(range(grid.shape[0]))
    ax.set_yticklabels(grid.index, fontsize=9.4)
    for tick, team in zip(ax.get_yticklabels(), grid.index):
        tick.set_color(_team_colour(team))
        tick.set_fontweight("bold" if team == SUBJECT else "semibold")
    ax.text(grid.shape[1] - 0.32, -0.72, "total", ha="left", va="center",
            fontsize=8.6, color=st.INK_2)
    ax.set_xlim(-0.5, grid.shape[1] + 0.35)
    ax.grid(False)
    st.strip(ax, keep=())
    st.titled(ax, "Where the shot quality comes from",
              f"points per 100 attempts against the league, "
              f"{REPORT_SEASON - 1}-{str(REPORT_SEASON)[2:]}")
    st.caption(fig,
               "Each cell adds two things: shooting from a zone more often than the league does, "
               "valued at what the league gets there, and finding better looks than the league "
               "inside the zone. Rows sum to the team's quality figure.",
               y=-0.06)
    fig.savefig(FIG / "05_zone_surplus.png")
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_yardstick(yard: pd.DataFrame) -> None:
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9.4, 6.6), sharex=True,
                                  gridspec_kw={"height_ratios": [2.1, 1.0]})
    s = yard["season"]
    ax.plot(s, yard["actual"], color=st.INK, marker="o", ms=4, label="what was scored")
    ax.plot(s, yard["expected"], color=st.SERIES[0], marker="o", ms=4,
            label="what the looks were worth")
    ax.fill_between(s, yard["expected"], yard["actual"],
                    where=yard["actual"] >= yard["expected"],
                    color=st.SERIES[1], alpha=0.20, lw=0)
    ax.fill_between(s, yard["expected"], yard["actual"],
                    where=yard["actual"] < yard["expected"],
                    color=st.SERIES[0], alpha=0.16, lw=0)

    peak = int(yard.loc[yard["expected"].idxmax(), "season"])
    last = yard.iloc[-1]
    below = yard[yard["expected"] < last["expected"]]["season"]
    since = int(below.max()) + 1 if len(below) else int(yard["season"].min())
    ax.scatter([peak], [yard["expected"].max()], s=78, facecolor="none",
               edgecolor=st.SERIES[0], linewidth=1.4, zorder=6)
    ax.text(0.40, 0.03,
            f"the average look was worth most in {_season_label(peak)} (circled), and in "
            f"{_season_label(int(last['season']))}\nit was worth less than in any season since "
            f"{_season_label(since)}",
            transform=ax.transAxes, fontsize=8.4, color=st.SERIES[0], va="bottom")
    ax.set_ylabel("points per attempt")
    ax.legend(loc="upper left")
    st.titled(ax, "The model is a fixed yardstick, and the league moved past it",
              "league totals, coordinate era")
    st.strip(ax)

    ax2.plot(s, 100 * yard["three_share"], color=st.SERIES[2], marker="o", ms=4)
    ax2.set_ylabel("three-point share, %")
    ax2.set_xlabel("season, by the year it ended")
    st.strip(ax2)

    st.caption(fig,
               "The expectation carries no season term, so the shaded gap is the league's own shot "
               f"making against a fixed standard. Note what the two panels do together: after "
               f"{_season_label(peak)} the share of threes keeps climbing while the value of the "
               "average look falls, and scoring rises anyway because the shots go in more often. "
               "Openness is invisible to a model of geometry, so part of that gap is better "
               "spacing rather than better shooting.",
               y=-0.02)
    fig.savefig(FIG / "06_league_yardstick.png")
    plt.close(fig)


# --------------------------------------------------------------------------
def draw_all(*, off, deff, view, curve, sim, adj, zones, noise, series_att,
             rel_season, rel_series, yardstick) -> None:
    fig_scatter(off, deff)
    fig_reliability(curve, series_att)
    fig_contender_bars(view)
    fig_series_bands(sim, series_att)
    fig_zone_surplus(zones)
    fig_yardstick(yardstick)
