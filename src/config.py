"""Paths, seasons, the model's sample, and the teams the report is for."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
OUT = ROOT / "output"

for d in (RAW, PROC, FIG, OUT):
    d.mkdir(parents=True, exist_ok=True)

# Coordinates are only comparable from 2010-11 onward: before that, most attempts
# at the rim carry the rim's own coordinate rather than the shooter's, and a
# quarter of the whole file sits at exactly zero feet. A model whose features are
# geometry cannot be fit across that boundary, so the sample starts after it.
COORD_ERA_START = 2011
LAST_SEASON = 2025
SEASONS = list(range(COORD_ERA_START, LAST_SEASON + 1))

REPORT_SEASON = 2025
SUBJECT = "SAS"
CONTENDERS = ["OKC", "DEN", "HOU", "MIN", "LAL", "GSW"]
FULL_NAME = {
    "SAS": "San Antonio", "OKC": "Oklahoma City", "DEN": "Denver",
    "HOU": "Houston", "MIN": "Minnesota", "LAL": "LA Lakers", "GSW": "Golden State",
}

RIM_Y = 5.25
HEAVE_DIST = 30.0
HEAVE_SECS = 2.0

MIN_FGA_PLAYER = 300      # attempts for a player-season to be scored
N_FOLDS = 5
N_SPLITS = 200            # random split-half repetitions in the reliability curve
SEED = 20240117
