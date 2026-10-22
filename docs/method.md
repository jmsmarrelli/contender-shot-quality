# Method and revision notes


A team can score efficiently because of the attempts it generates, how it converts them, or both. This study separates a shot-model expectation from actual-minus-expected scoring and compares selected Western teams in the 2024–25 regular season. “Contender” is the historical project label, not a current championship forecast.

## The historical comparison

Values below are points per 100 field-goal attempts relative to the season's league baseline. For the defensive rows, lower opponent scoring is better. The ranks are within that season's source sample.

[Result table](../output/contenders.csv)

The residual includes factors missing from the public shot model, including openness and defensive pressure. It is not a direct measurement of shooting skill or luck. Free throws, turnovers, rebounding and total possession efficiency are outside this field-goal decomposition.

## How the model is evaluated

[Result table](../output/model_fit.csv)

Game-grouped folds separate each scored shot from other shots in its game. The model evaluation is within the historical sample, not a pre-season or playoff forecast. The source coordinates and action labels require the documented era restrictions and sensitivity checks.

## What the resampling can establish

![Within-season split-sample consistency](../figures/02_reliability_curve.png)

Random subsets of the same team-season describe within-season consistency across sample sizes. They do not reproduce consecutive games or an unfamiliar playoff opponent.

![Independent-shot resampling](../figures/04_series_bands.png)

The bands resample individual regular-season attempts independently. Their sample size is chosen to resemble several games' worth of shots, but they omit game-level dependence, tactical adjustments, injuries and rotation changes. They are an illustrative sampling exercise, not playoff-series outcome probabilities. Overlap between bands is not a formal equivalence test.

Reliability-based shrinkage tables remain available as a sensitivity exercise. Applying a smaller-sample coefficient to a season estimate is a hypothetical adjustment, not evidence that the adjusted value predicts a series.

## Basketball use

These components help frame a scouting question: is the observed field-goal advantage associated with the available shot features or with conversion beyond them? Follow that question with film and possession-level measures before recommending a coverage change.

The release fixes dependency versions and refreshes the model tables, article and figures together. Use this version's outputs throughout; do not mix in the original unpinned model results.


The result tables are linked and rendered in the main article. Full algorithms and thresholds are in `src/`; source bytes are recorded in `data/source_manifest.json`.
