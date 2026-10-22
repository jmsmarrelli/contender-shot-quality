"""Splitting a team's shot value into the part it chose and the part it made.

Every attempt carries an expected value, xPPS: the points a league-average
shooter would be expected to score from that spot, scored by a model that never
saw the game the shot came from. Aggregate those over a team's season and you
have the value of the *looks* the team generated. The gap between what the team
actually scored on those attempts and what the model expected is shot making.

Both are reported as points per 100 attempts relative to the league in the same
season, which makes them add up:

    total = quality + making

with `quality = e - L_e`, `making = (a - e) - (L_a - L_e)` and
`total = a - L_a`, where a and e are the team's actual and expected points per
attempt and L is the league's. Centring making on the league's own residual
matters: the model carries no season term, so the league's residual is not zero
in any given year, and skipping that step would quietly hand every team the
league's era drift.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SIDE_KEY = {"offence": "team_abbrev", "defence": "opponent"}


def league_baseline(scored: pd.DataFrame) -> pd.DataFrame:
    """Per season: the league's own actual and expected points per attempt."""
    return (
        scored.groupby("season", observed=True)
        .agg(L_att=("points", "size"), L_a=("points", "mean"), L_e=("xpps", "mean"))
        .reset_index()
    )


def side_table(scored: pd.DataFrame, side: str = "offence") -> pd.DataFrame:
    """One row per team-season, on the chosen side of the ball.

    On defence the sign convention is kept as-is rather than flipped: a positive
    number means the opponent scored more than the league does, so *lower is
    better*. Flipping it here would make the arithmetic above stop adding up.
    """
    key = SIDE_KEY[side]
    tbl = (
        scored.groupby(["season", key], observed=True)
        .agg(att=("points", "size"), a=("points", "mean"), e=("xpps", "mean"),
             games=("game_id", "nunique"))
        .reset_index()
        .rename(columns={key: "team"})
        .merge(league_baseline(scored), on="season", how="left")
    )
    tbl["quality"] = 100 * (tbl["e"] - tbl["L_e"])
    tbl["making"] = 100 * ((tbl["a"] - tbl["e"]) - (tbl["L_a"] - tbl["L_e"]))
    tbl["total"] = 100 * (tbl["a"] - tbl["L_a"])
    tbl["side"] = side
    return tbl


def rank_within_season(tbl: pd.DataFrame, col: str, ascending: bool = False) -> pd.Series:
    return tbl.groupby("season", observed=True)[col].rank(ascending=ascending, method="min")


def _halves(rng: np.random.Generator, n: int, size: int) -> tuple[np.ndarray, np.ndarray]:
    take = rng.choice(n, size=2 * size, replace=False)
    return take[:size], take[size:]


def split_half(scored: pd.DataFrame, side: str, size: int | None = None,
               n_splits: int = 200, seed: int = 0,
               min_attempts: int | None = None) -> dict:
    """Correlate quality and making measured on two disjoint halves of a season.

    `size` is the number of attempts in each half. Passing None uses half of the
    smallest team-season in the sample, which is the largest split every team can
    supply. Correlations are averaged over `n_splits` random partitions and then
    stepped up to full length with Spearman-Brown.

    `min_attempts` fixes which team-seasons are eligible. The reliability curve
    passes the same value at every sample size so that the curve is a statement
    about sample size and not about which teams dropped out of it.
    """
    key = SIDE_KEY[side]
    rng = np.random.default_rng(seed)
    base = league_baseline(scored).set_index("season")

    groups = []
    for (season, team), g in scored.groupby(["season", key], observed=True):
        groups.append((season, team, g["points"].to_numpy(dtype=float),
                       g["xpps"].to_numpy(dtype=float)))
    smallest = min(len(p) for _, _, p, _ in groups)
    size = smallest // 2 if size is None else size
    floor = 2 * size if min_attempts is None else min_attempts
    groups = [g for g in groups if len(g[2]) >= max(floor, 2 * size)]

    q_r, m_r, t_r = [], [], []
    for _ in range(n_splits):
        rows = []
        for season, team, pts, xp in groups:
            i, j = _halves(rng, len(pts), size)
            L_a, L_e = base.loc[season, "L_a"], base.loc[season, "L_e"]
            rows.append((
                100 * (xp[i].mean() - L_e), 100 * (xp[j].mean() - L_e),
                100 * ((pts[i] - xp[i]).mean() - (L_a - L_e)),
                100 * ((pts[j] - xp[j]).mean() - (L_a - L_e)),
                100 * (pts[i].mean() - L_a), 100 * (pts[j].mean() - L_a),
            ))
        arr = np.asarray(rows)
        q_r.append(np.corrcoef(arr[:, 0], arr[:, 1])[0, 1])
        m_r.append(np.corrcoef(arr[:, 2], arr[:, 3])[0, 1])
        t_r.append(np.corrcoef(arr[:, 4], arr[:, 5])[0, 1])

    def sb(r: float) -> float:
        return 2 * r / (1 + r)

    out = {"side": side, "half_size": size, "team_seasons": len(groups),
           "n_splits": n_splits}
    for name, vals in (("quality", q_r), ("making", m_r), ("total", t_r)):
        r = float(np.mean(vals))
        out[f"{name}_half"], out[f"{name}_full"] = r, float(sb(r))
    return out


def reliability_curve(scored: pd.DataFrame, side: str, sizes: list[int],
                      n_splits: int = 60, seed: int = 0) -> pd.DataFrame:
    """Split-half correlation as a function of how many attempts you have seen."""
    floor = 2 * max(sizes)
    return pd.DataFrame(
        [split_half(scored, side, size=s, n_splits=n_splits, seed=seed + i,
                    min_attempts=floor)
         for i, s in enumerate(sizes)]
    )


def noise_share(scored: pd.DataFrame, side: str) -> pd.DataFrame:
    """How much of the spread in team shot making is sampling noise.

    For a team with n attempts, the sampling variance of its mean residual is
    Var(points - xPPS) / n, and that variance is estimable from the team's own
    attempts. Averaging it over teams gives the variance a season of shot making
    would show even if every team were identical.
    """
    key = SIDE_KEY[side]
    tbl = side_table(scored, side)
    per_team = (
        scored.assign(res=lambda t: t["points"] - t["xpps"])
        .groupby(["season", key], observed=True)["res"]
        .agg(["var", "size"])
        .reset_index()
        .rename(columns={key: "team"})
    )
    per_team["noise_var"] = 1e4 * per_team["var"] / per_team["size"]
    rows = []
    for season, g in tbl.groupby("season", observed=True):
        nv = per_team.loc[per_team["season"] == season, "noise_var"].mean()
        obs = g["making"].var(ddof=1)
        rows.append({"season": season, "observed_var": obs, "noise_var": nv,
                     "noise_share": nv / obs,
                     "true_sd": np.sqrt(max(obs - nv, 0.0)),
                     "observed_sd": np.sqrt(obs)})
    return pd.DataFrame(rows)


def year_over_year(tbl: pd.DataFrame, reliability: dict | None = None) -> pd.DataFrame:
    """Correlate a franchise's season with its next one, for each component.

    The raw correlation confounds two things: how much of the trait a team keeps
    from one year to the next, and how precisely a single season measures the
    trait at all. Dividing by the within-season reliability separates them. It is
    the standard correction and it changes the reading here, because quality is
    measured almost perfectly and making is not.

    Rows are franchise pairs, so a relocation breaks the chain: New Jersey to
    Brooklyn in 2012-13 and New Orleans' rename in 2013-14 each cost one pair.
    """
    nxt = tbl[["season", "team", "quality", "making", "total"]].copy()
    nxt["season"] -= 1
    pair = tbl.merge(nxt, on=["season", "team"], suffixes=("", "_next"))
    row = {"side": tbl["side"].iloc[0], "pairs": len(pair)}
    for comp in ("quality", "making", "total"):
        r = pair[comp].corr(pair[f"{comp}_next"])
        row[f"{comp}_r"] = r
        if reliability is not None:
            row[f"{comp}_persist"] = r / reliability[comp]
    return pd.DataFrame([row])


def shrink(tbl: pd.DataFrame, making_reliability: float,
           quality_reliability: float = 1.0) -> pd.DataFrame:
    """Pull each component toward the league by one minus its reliability.

    This is the flat version of the usual regression estimate. Every team in a
    season plays close enough to the same number of games that a per-team
    shrinkage weight would move nothing, and a single published factor is easier
    to argue with.
    """
    out = tbl.copy()
    out["quality_adj"] = quality_reliability * out["quality"]
    out["making_adj"] = making_reliability * out["making"]
    out["total_adj"] = out["quality_adj"] + out["making_adj"]
    return out


def series_noise(scored: pd.DataFrame, season: int, side: str, attempts: int,
                 n_sims: int = 4000, seed: int = 0) -> pd.DataFrame:
    """Resample a series' worth of attempts and see how far making wanders.

    Draws `attempts` shots with replacement from each team's season and records
    the shot-making figure the sample produces. The spread of that distribution
    is what a seven-game sample does to the number on its own, before anybody
    has played differently.
    """
    key = SIDE_KEY[side]
    rng = np.random.default_rng(seed)
    base = league_baseline(scored).set_index("season")
    L_a, L_e = base.loc[season, "L_a"], base.loc[season, "L_e"]
    sel = scored[scored["season"] == season]
    rows = []
    for team, g in sel.groupby(key, observed=True):
        res = (g["points"] - g["xpps"]).to_numpy(dtype=float)
        draws = rng.choice(res, size=(n_sims, attempts), replace=True)
        sim = 100 * (draws.mean(axis=1) - (L_a - L_e))
        season_val = 100 * (res.mean() - (L_a - L_e))
        rows.append({"team": team, "season_making": season_val,
                     "sim_sd": float(sim.std(ddof=1)),
                     "p05": float(np.percentile(sim, 5)),
                     "p95": float(np.percentile(sim, 95))})
    return pd.DataFrame(rows).sort_values("season_making", ascending=False)


def attempts_per_game(scored: pd.DataFrame, season: int, side: str = "offence") -> float:
    key = SIDE_KEY[side]
    sel = scored[scored["season"] == season]
    per = sel.groupby([key, "game_id"], observed=True).size()
    return float(per.mean())
