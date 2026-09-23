"""Stage 2 - fit the expected-value model and score every attempt out of fold.

    python src/run_02_model.py

Two specifications are fit. `geo` is geometry alone and is the yardstick every
later table uses. `full` adds action type, clock, period and venue; it is the
better classifier and it is carried through only so that stage 3 can check
whether the choice moves the answer.

Writes data/processed/scored.csv.gz, output/model_fit.csv,
output/calibration.csv and output/season_yardstick.csv.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import OUT, PROC  # noqa: E402
import model  # noqa: E402

COLS = ["season", "game_id", "player_id", "player", "team_abbrev", "opponent",
        "dist", "abs_x", "y", "angle", "is_three", "zone", "family", "period",
        "secs_left", "is_home", "made", "points"]

CARRY = ["season", "game_id", "player_id", "player", "team_abbrev", "opponent",
         "zone", "dist", "is_three", "made", "points"]


def scores(y: np.ndarray, p: np.ndarray) -> dict:
    return {
        "log_loss": round(float(log_loss(y, p)), 5),
        "brier": round(float(brier_score_loss(y, p)), 5),
        "auc": round(float(roc_auc_score(y, p)), 5),
    }


def main() -> None:
    t0 = time.time()
    d = pd.read_csv(PROC / "shots.csv.gz", usecols=COLS)
    d["family"] = d["family"].astype("category")
    print(f"{len(d):,} attempts loaded ({time.time() - t0:.0f}s)", flush=True)

    y = d["made"].to_numpy().astype(int)
    fit_rows = []
    for name, spec in (("geo", model.GEO), ("full", model.FULL)):
        print(f"\n{name}:", flush=True)
        t0 = time.time()
        p, _ = model.fit_out_of_fold(d, spec)
        d[f"p_{name}"] = p
        d[f"xpps_{name}"] = model.expected_points(p, d["is_three"].to_numpy())
        row = {"spec": name, "features": ", ".join(model.features(spec))}
        row.update(scores(y, p))
        row["seconds"] = round(time.time() - t0, 1)
        fit_rows.append(row)
        print(f"  {row['log_loss']=} {row['auc']=}", flush=True)

    # A model that always guessed the league's overall make rate, for scale.
    base = np.full(len(d), y.mean())
    row = {"spec": "constant", "features": "league make rate"}
    row.update(scores(y, base))
    row["seconds"] = 0.0
    fit_rows.append(row)

    fit = pd.DataFrame(fit_rows)
    fit.to_csv(OUT / "model_fit.csv", index=False)

    cal = model.calibration_table(d["p_geo"].to_numpy(), y)
    cal.to_csv(OUT / "calibration.csv", index=False)

    # The model carries no season term, so its residual by season *is* the
    # league's change in shot making. If this column were flat the decomposition
    # would be measuring nothing.
    yard = (
        d.groupby("season", observed=True)
        .agg(att=("made", "size"),
             actual=("points", "mean"),
             expected=("xpps_geo", "mean"),
             three_share=("is_three", "mean"))
        .assign(making=lambda t: t["actual"] - t["expected"])
        .round(4)
        .reset_index()
    )
    yard.to_csv(OUT / "season_yardstick.csv", index=False)

    out = d[CARRY + ["xpps_geo", "xpps_full"]]
    out.to_csv(PROC / "scored.csv.gz", index=False, compression="gzip")

    print()
    print(fit.drop(columns="features").to_string(index=False))
    print()
    print(yard.to_string(index=False))


if __name__ == "__main__":
    main()
