# Comparing team shot expectations and residual conversion

A team can score efficiently because of the attempts it generates, how it converts them, or both. This study separates a shot-model expectation from actual-minus-expected scoring and compares selected Western teams in the 2024–25 regular season. “Contender” is the historical project label, not a current championship forecast.

## The historical comparison

Values below are points per 100 field-goal attempts relative to the season's league baseline. For the defensive rows, lower opponent scoring is better. The ranks are within that season's source sample.

{{table:contenders.csv|side,team,att,quality,making,total,quality_rank,making_rank}}

The residual includes factors missing from the public shot model, including openness and defensive pressure. It is not a direct measurement of shooting skill or luck. Free throws, turnovers, rebounding and total possession efficiency are outside this field-goal decomposition.

## How the model is evaluated

{{table:model_fit.csv|spec,log_loss,brier,auc}}

Game-grouped folds separate each scored shot from other shots in its game. The model evaluation is within the historical sample, not a pre-season or playoff forecast. The source coordinates and action labels require the documented era restrictions and sensitivity checks.

## What the resampling can establish

![Within-season split-sample consistency](figures/02_reliability_curve.png)

Random subsets of the same team-season describe within-season consistency across sample sizes. They do not reproduce consecutive games or an unfamiliar playoff opponent.

![Independent-shot resampling](figures/04_series_bands.png)

The bands resample individual regular-season attempts independently. Their sample size is chosen to resemble several games' worth of shots, but they omit game-level dependence, tactical adjustments, injuries and rotation changes. They are an illustrative sampling exercise, not playoff-series outcome probabilities. Overlap between bands is not a formal equivalence test.

Reliability-based shrinkage tables remain available as a sensitivity exercise. Applying a smaller-sample coefficient to a season estimate is a hypothetical adjustment, not evidence that the adjusted value predicts a series.

## Basketball use

These components help frame a scouting question: is the observed field-goal advantage associated with the available shot features or with conversion beyond them? Follow that question with film and possession-level measures before recommending a coverage change.



## Reproduce

The historical analysis used Python 3.12 with the pinned dependencies below. From this repository:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make fetch-data PY=python
make all PY=python
make report site PY=python
```

`make all` verifies source hashes before running the analyses in order. A missing or changed input stops the build. Data downloads need network access; article rendering uses the included result tables. See [the source manifest](data/source_manifest.json), [method notes](docs/method.md) and [current validation record](VALIDATION_CURRENT.md) for the distinction between a source rebuild and checks of delivered outputs.

Season keys in CSV files use the **ending year**: `2025` means 2024–25. Display tables use full season labels. The MIT license covers code; third-party data retain their providers' rights and terms.

[Portfolio](https://github.com/jmsmarrelli/basketball-analytics) · [AI assistance and provenance](PROVENANCE.md)
