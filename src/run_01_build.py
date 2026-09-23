"""Stage 1 - the coordinate era, turned into model-ready rows.

    python src/run_01_build.py

Reads the fifteen seasons whose coordinates are comparable, repairs the three
that are published on a compressed scale, drops heaves and backcourt attempts,
and writes one row per attempt with the geometry the model uses.

Writes data/processed/shots.csv.gz, output/build_audit.csv and
output/action_labels.csv.

The action-label table is not decoration. The model below is fit on geometry
alone, and the reason is in that file: the league's vocabulary for describing a
shot keeps moving even inside this window, so a model that reads action type
reads the calendar as well as the shot.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import OUT, PROC, RAW, SEASONS  # noqa: E402
import features  # noqa: E402

KEEP = ["season", "game_id", "game_date", "player_id", "player", "team_abbrev",
        "opponent", "x", "y", "dist", "abs_x", "angle", "is_three", "zone",
        "family", "period", "secs_left", "is_home", "made", "points"]


def main() -> None:
    frames, audit, labels = [], [], []
    for season in SEASONS:
        path = RAW / f"NBA_{season}_Shots.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}. See data/README.md.")
        t0 = time.time()
        raw = pd.read_csv(path, low_memory=False)
        n_raw = len(raw)
        d = features.build(raw)

        # Which team was defending. The two abbreviations are on every row, so
        # the defender is whichever of them the shooter is not.
        d["opponent"] = np.where(d["team_abbrev"].astype(str) == raw["HOME_TEAM"].to_numpy(),
                                 raw["AWAY_TEAM"].to_numpy(), raw["HOME_TEAM"].to_numpy())

        heaves = int(((d["secs_left"] <= 2.0) & (d["dist"] >= 30.0)).sum())
        backcourt = int(d["zone"].astype(str).eq("Backcourt").sum())
        kept = d.loc[~d["excluded"], KEEP]
        frames.append(kept)

        share = (kept["family"].value_counts(normalize=True) * 100).round(2)
        labels.append(share.rename(season))

        audit.append({"season": season, "raw_rows": n_raw, "kept": len(kept),
                      "dropped": n_raw - len(kept),
                      "heaves": heaves, "backcourt": backcourt,
                      "rescaled": bool(d.attrs["rescaled"]),
                      "distance_gap_ft": round(d.attrs["distance_gap"], 3),
                      "games": int(kept["game_id"].nunique()),
                      "seconds": round(time.time() - t0, 1)})
        print(f"  {season}: {len(kept):,} attempts, {audit[-1]['dropped']} dropped "
              f"({audit[-1]['seconds']}s)", flush=True)

    shots = pd.concat(frames, ignore_index=True)
    shots.to_csv(PROC / "shots.csv.gz", index=False, compression="gzip")

    cov = pd.DataFrame(audit)
    cov.to_csv(OUT / "build_audit.csv", index=False)

    lab = pd.concat(labels, axis=1).fillna(0.0)
    lab.index.name = "action_family"
    lab.to_csv(OUT / "action_labels.csv")

    print(f"\n{len(shots):,} attempts, {shots['game_id'].nunique():,} games, "
          f"{shots['season'].min()}-{shots['season'].max()}")
    print()
    print(cov.to_string(index=False))
    print()
    print("action family share of attempts, %")
    print(lab.to_string())


if __name__ == "__main__":
    main()
