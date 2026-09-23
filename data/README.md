# Data

One CSV per season at `data/raw/NBA_<season>_Shots.csv`, where `<season>` is the
year the season ended: `NBA_2025_Shots.csv` is 2024-25.

## Getting the files

```bash
git clone --depth 1 https://github.com/DomSamangy/NBA_Shots_04_24.git /tmp/nba_shots
mkdir -p data/raw
for z in /tmp/nba_shots/NBA_20{1[1-9],2[0-5]}_Shots.csv.zip; do
  unzip -o -q "$z" -d data/raw/
done
```

Fifteen seasons, about 600 MB unzipped, 3.07 million rows before filtering.
`data/raw/` and `data/processed/` are gitignored; every number the analysis
quotes is written to `output/` and committed.

The mirror ends with 2024-25 and carries the regular season only — every game id
in the 2024-25 file is a `0022400xxx`. Nothing here is measured on a playoff
game, including the seven-game arithmetic, which resamples regular-season
attempts.

## Why the sample starts at 2010-11

The model's features are geometry, so it can only be fit where the coordinates
mean the same thing. Before 2010-11 most rim attempts carry the rim's own
coordinate rather than the shooter's, and roughly a quarter of the file sits at
exactly zero feet. That boundary is documented at length in the sibling
`nba-shot-value` repository. Here the sample simply starts after it.

Three of the fifteen files — 2019-20, 2020-21 and 2021-22 — are published on a
compressed coordinate scale, with `LOC_X` and `LOC_Y` divided by ten and the
origin shifted. `features.normalise_coordinates` detects and inverts that on
every season rather than hard-coding the three, and `output/build_audit.csv`
records which seasons were repaired. The check is the file's own
`SHOT_DISTANCE` column: after the repair, the recomputed distance agrees with it
to within half a foot in all fifteen seasons, and the build raises if it ever
does not.

## The defect this project works around rather than repairs

The league's vocabulary for describing a shot kept moving inside the sample.
`output/action_labels.csv` has the whole table; the corners of it:

| Action family | 2010-11 | 2014-15 | 2015-16 | 2024-25 |
|---|---|---|---|---|
| Jump shot | 57.9% | 55.1% | 48.2% | 31.8% |
| Layup | 12.7% | 12.7% | 8.8% | 1.6% |
| Pull-up | 2.4% | 3.5% | 6.2% | 13.0% |
| Floater | 1.0% | 1.5% | 3.8% | 9.5% |
| Bank | 1.4% | 1.4% | 1.3% | 0.2% |

Players did not start taking six times as many floaters between two consecutive
seasons. The labels split. A model that reads `ACTION_TYPE` across that boundary
is reading the calendar, so the model used everywhere in this project reads
geometry only, and `output/spec_sensitivity.csv` reports what the other choice
would have done to the 2024-25 ordering.

## Filters applied in stage 1

| Filter | Rows |
|---|---|
| Heaves: 30 feet or more with two seconds or less on the clock | 12,222 |
| Backcourt attempts | 6,503 |
| Dropped in total (the two overlap heavily) | 12,347 |

Neither is a shot selection decision, and letting them into the model drags its
tail without teaching it anything about the looks a team generates.

## Columns used

| Column | Used for |
|---|---|
| `SEASON_1` | the season, labeled by ending year |
| `GAME_ID` | grouping the cross-validation folds, and counting games |
| `PLAYER_ID`, `PLAYER_NAME` | carried through, not used by any published table |
| `TEAM_NAME`, `HOME_TEAM`, `AWAY_TEAM` | who shot, and therefore who defended |
| `LOC_X`, `LOC_Y` | every geometric feature |
| `SHOT_DISTANCE` | the coordinate-repair check, and the heave filter |
| `BASIC_ZONE` | the zone attribution in figure 05, and the backcourt filter |
| `SHOT_TYPE`, `SHOT_MADE` | the label, and points |
| `ACTION_TYPE`, `QUARTER`, `MINS_LEFT`, `SECS_LEFT` | the sensitivity model only |

## What a shot file cannot see

**No defender.** Nothing in the file says who was guarding or how closely. Shot
quality here is the quality of the *look on the floor*, and any openness a team
manufactures lands in shot making instead. This is the single largest caveat in
the project and it is discussed in `docs/method.md`.

**No free throws, no turnovers, no offensive rebounds.** Everything is per shot
attempt, never per possession. A team that gets to the line, or takes care of
the ball, gets no credit here.
