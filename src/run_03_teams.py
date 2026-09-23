"""Stage 3 - the decomposition, its reliability, and what survives a series.

    python src/run_03_teams.py
    python src/run_03_teams.py --figures

Reads data/processed/scored.csv.gz. Writes the tables in output/ and the
figures in figures/. The second form redraws the figures from the tables that
are already there, which takes a second rather than five minutes and is what
you want while you are arguing with a chart.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CONTENDERS, FIG, FULL_NAME, N_SPLITS, OUT, PROC, REPORT_SEASON, SEED, SUBJECT  # noqa: E402
import quality  # noqa: E402
import figures as fg  # noqa: E402

SEVEN = [SUBJECT] + CONTENDERS
SIZES = [150, 300, 500, 750, 1100, 1600, 2200, 2700]
SERIES_GAMES = 7


def load(spec: str = "geo") -> pd.DataFrame:
    d = pd.read_csv(PROC / "scored.csv.gz",
                    usecols=["season", "game_id", "team_abbrev", "opponent", "zone",
                             "is_three", "made", "points", f"xpps_{spec}"])
    return d.rename(columns={f"xpps_{spec}": "xpps"})


def contender_view(off: pd.DataFrame, deff: pd.DataFrame, season: int) -> pd.DataFrame:
    rows = []
    for side, tbl in (("offense", off), ("defense", deff)):
        sel = tbl[tbl["season"] == season].copy()
        asc = side == "defense"
        sel["quality_rank"] = sel["quality"].rank(ascending=asc, method="min").astype(int)
        sel["making_rank"] = sel["making"].rank(ascending=asc, method="min").astype(int)
        sel["total_rank"] = sel["total"].rank(ascending=asc, method="min").astype(int)
        rows.append(sel[sel["team"].isin(SEVEN)])
    out = pd.concat(rows, ignore_index=True)
    out["name"] = out["team"].map(FULL_NAME)
    cols = ["side", "team", "name", "att", "games", "quality", "making", "total",
            "quality_rank", "making_rank", "total_rank"]
    return out[cols].round(3)


def spec_sensitivity(season: int) -> pd.DataFrame:
    """Does the geometry-only yardstick change the 2024-25 ordering?"""
    frames = {}
    for spec in ("geo", "full"):
        d = load(spec)
        for side in ("offense", "defense"):
            t = quality.side_table(d, side)
            t = t[t["season"] == season].set_index("team")
            frames[(spec, side)] = t[["quality", "making"]]
    rows = []
    for side in ("offense", "defense"):
        g, f = frames[("geo", side)], frames[("full", side)]
        j = g.join(f, lsuffix="_geo", rsuffix="_full")
        for comp in ("quality", "making"):
            a, b = j[f"{comp}_geo"], j[f"{comp}_full"]
            rows.append({"side": side, "component": comp,
                         "pearson_r": round(float(a.corr(b)), 4),
                         "spearman_r": round(float(a.corr(b, method="spearman")), 4),
                         "mean_abs_gap": round(float((a - b).abs().mean()), 3),
                         "max_rank_move": int((a.rank(ascending=False)
                                               - b.rank(ascending=False)).abs().max())})
    return pd.DataFrame(rows)


def zone_surplus(scored: pd.DataFrame, season: int) -> pd.DataFrame:
    """Where a team's quality surplus is generated, by zone.

    Quality surplus splits into two pieces per zone: shooting from a zone more
    than the league does, valued at the league's expectation there, and finding
    better-than-league looks inside the zone.
    """
    sel = scored[scored["season"] == season]
    lg = (sel.groupby("zone", observed=True)
          .agg(lg_att=("points", "size"), lg_e=("xpps", "mean")).reset_index())
    lg["lg_share"] = lg["lg_att"] / lg["lg_att"].sum()
    lg_e_all = sel["xpps"].mean()

    tm = (sel.groupby(["team_abbrev", "zone"], observed=True)
          .agg(att=("points", "size"), e=("xpps", "mean")).reset_index()
          .rename(columns={"team_abbrev": "team"}))
    tm["share"] = tm["att"] / tm.groupby("team", observed=True)["att"].transform("sum")
    tm = tm.merge(lg, on="zone", how="left")
    tm["from_mix"] = 100 * (tm["share"] - tm["lg_share"]) * (tm["lg_e"] - lg_e_all)
    tm["from_look"] = 100 * tm["share"] * (tm["e"] - tm["lg_e"])
    tm["surplus"] = tm["from_mix"] + tm["from_look"]
    return tm[["team", "zone", "att", "share", "lg_share", "e", "lg_e",
               "from_mix", "from_look", "surplus"]].round(4)


def redraw() -> None:
    """Re-cut every figure from the tables in output/, fitting nothing."""
    off = pd.read_csv(OUT / "team_offence.csv")
    deff = pd.read_csv(OUT / "team_defence.csv")
    curve = pd.read_csv(OUT / "reliability_curve.csv")
    half = pd.read_csv(OUT / "split_half.csv")
    sim = pd.read_csv(OUT / "series_noise.csv")
    adj = pd.read_csv(OUT / "shrunk_offence.csv")
    zones = pd.read_csv(OUT / "zone_surplus.csv")
    noise = pd.read_csv(OUT / "noise_share.csv")
    view = pd.read_csv(OUT / "contenders.csv")
    yard = pd.read_csv(OUT / "season_yardstick.csv")

    series_att = int(curve.loc[~curve["half_size"].isin(SIZES), "half_size"].iloc[0])
    rel_season = float(half.loc[half["side"] == "offense", "making_full"].iloc[0])
    rel_series = float(curve.loc[curve["half_size"] == series_att, "making_half"].iloc[0])

    fg.draw_all(off=off, deff=deff, view=view, curve=curve, sim=sim, adj=adj,
                zones=zones, noise=noise, series_att=series_att,
                rel_season=rel_season, rel_series=rel_series, yardstick=yard)
    print(f"figures redrawn in {FIG}")


def main() -> None:
    d = load("geo")
    print(f"{len(d):,} scored attempts, {d['season'].min()}-{d['season'].max()}", flush=True)

    off = quality.side_table(d, "offense")
    deff = quality.side_table(d, "defense")
    for t, n in ((off, "team_offence"), (deff, "team_defence")):
        t.round(4).to_csv(OUT / f"{n}.csv", index=False)

    view = contender_view(off, deff, REPORT_SEASON)
    view.to_csv(OUT / "contenders.csv", index=False)
    print("\n" + view.to_string(index=False), flush=True)

    # --- how much of this is real -----------------------------------------
    half = pd.DataFrame([quality.split_half(d, s, n_splits=N_SPLITS, seed=SEED)
                         for s in ("offense", "defense")]).round(4)
    half.to_csv(OUT / "split_half.csv", index=False)
    print("\n" + half.to_string(index=False), flush=True)

    # A seven-game series' worth of attempts is put on the curve explicitly
    # rather than read off between two points.
    per_game = quality.attempts_per_game(d, REPORT_SEASON, "offense")
    series_att = int(round(per_game * SERIES_GAMES))
    sizes = sorted(set(SIZES + [series_att]))
    curve = quality.reliability_curve(d, "offense", sizes, n_splits=60, seed=SEED).round(4)
    curve.to_csv(OUT / "reliability_curve.csv", index=False)
    print(f"\n{per_game:.1f} attempts per team-game, {series_att} in a full series")
    print(curve.to_string(index=False), flush=True)

    noise = quality.noise_share(d, "offense").round(4)
    noise.to_csv(OUT / "noise_share.csv", index=False)
    print("\n" + noise.to_string(index=False), flush=True)

    rel = {side: {c: float(half.loc[half["side"] == side, f"{c}_full"].iloc[0])
                  for c in ("quality", "making", "total")}
           for side in ("offense", "defense")}
    yoy = pd.concat([quality.year_over_year(off, rel["offense"]),
                     quality.year_over_year(deff, rel["defense"])],
                    ignore_index=True).round(4)
    yoy.to_csv(OUT / "year_over_year.csv", index=False)
    print("\n" + yoy.to_string(index=False), flush=True)

    # --- what a seven-game sample does ------------------------------------
    sim = quality.series_noise(d, REPORT_SEASON, "offense", series_att,
                               n_sims=4000, seed=SEED).round(3)
    sim.to_csv(OUT / "series_noise.csv", index=False)
    print("\n" + sim.to_string(index=False), flush=True)

    # Two shrinkages, on the same season. The first uses the reliability a full
    # season of attempts earns; the second uses the reliability a single series
    # earns. The gap between them is the point of the whole exercise.
    rel_season = float(half.loc[half["side"] == "offense", "making_full"].iloc[0])
    row = curve[curve["half_size"] == series_att].iloc[0]
    rel_series = float(row["making_half"])
    rel_series_q = float(row["quality_half"])

    season_year = off[off["season"] == REPORT_SEASON]
    adj = quality.shrink(season_year, rel_season)
    ser = quality.shrink(season_year, rel_series, rel_series_q)
    adj = adj[["team", "quality", "making", "total", "quality_adj", "making_adj", "total_adj"]]
    adj = adj.merge(ser[["team", "total_adj"]].rename(columns={"total_adj": "total_series"}),
                    on="team")
    adj["move"] = (adj["total"].rank(ascending=False, method="min")
                   - adj["total_adj"].rank(ascending=False, method="min")).astype(int)
    adj["move_series"] = (adj["total"].rank(ascending=False, method="min")
                          - adj["total_series"].rank(ascending=False, method="min")).astype(int)
    adj = adj.sort_values("total_adj", ascending=False).round(3)
    adj.to_csv(OUT / "shrunk_offence.csv", index=False)
    print(f"\nmaking reliability: {rel_season:.3f} over a season, "
          f"{rel_series:.3f} over {series_att} attempts")
    print(adj.to_string(index=False), flush=True)

    zones = zone_surplus(d, REPORT_SEASON)
    zones.to_csv(OUT / "zone_surplus.csv", index=False)

    sens = spec_sensitivity(REPORT_SEASON)
    sens.to_csv(OUT / "spec_sensitivity.csv", index=False)
    print("\n" + sens.to_string(index=False), flush=True)

    fg.draw_all(off=off, deff=deff, view=view, curve=curve, sim=sim, adj=adj,
                zones=zones, noise=noise, series_att=series_att,
                rel_season=rel_season, rel_series=rel_series,
                yardstick=pd.read_csv(OUT / "season_yardstick.csv"))
    print(f"\nfigures written to {FIG}")


if __name__ == "__main__":
    if "--figures" in sys.argv[1:]:
        redraw()
    else:
        main()
