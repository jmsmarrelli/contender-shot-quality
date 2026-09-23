# Method

Longer notes on the choices that move results. The README has the findings; this
is the argument for believing them, and the places where I do not.

---

## 1. The estimand

For a team-season on one side of the ball, with `a` and `e` the mean actual and
expected points per attempt and `L_a`, `L_e` the same for the league in that
season:

```
quality = 100 (e - L_e)
making  = 100 [(a - e) - (L_a - L_e)]
total   = 100 (a - L_a) = quality + making
```

The bracketed subtraction in `making` is not cosmetic. The model carries no
season term, so the league's own residual `L_a - L_e` is nonzero and drifts — it
runs from −0.007 points per attempt in 2010-11 to +0.053 in 2024-25
(`output/season_yardstick.csv`). Omitting it would hand every team in 2024-25 five
extra points per 100 of "shot making" that is really the league's era drift, and
the three lines above would stop adding up.

On defense the same formulas are applied to the shots a team faced, and the sign
convention is *not* flipped. A positive defensive number means the opponent got
more than the league average. Flipping it for readability would break the
identity.

---

## 2. The model

`HistGradientBoostingClassifier` on `P(make)`, times 2 or 3.

**Out of fold, with folds grouped by game.** Five `GroupKFold` folds on
`game_id`, so no attempt is ever scored by a model that saw another attempt from
the same game. Splitting on rows instead would let the model memorise a game's
particular shooting night and quietly move it from the residual into the
expectation, which is exactly the quantity the project is trying to measure.

**No season feature.** If season entered the model, the league's year-to-year
change in conversion would be absorbed into the expectation and every team's
making figure would be measured against a moving standard. Figure 06 is what that
choice buys: the yardstick stays still and the league's own drift becomes
visible.

**Geometry only.** The `geo` specification uses distance, court position
(`abs_x`, `y`), angle, and whether the attempt is worth three. The alternative,
`full`, adds action family, period, seconds left and venue. `full` is the better
classifier — log loss 0.6361 against 0.6534, AUC 0.665 against 0.634 — and it is
the wrong model here, because its best feature is a label whose meaning moved
inside the sample. See section 3.

**Calibration.** Across twenty equal-count bins the geometry model's mean
predicted and observed make rates differ by at most 0.0024
(`output/calibration.csv`). A model can be well calibrated in aggregate and still
be wrong in a corner of the floor; this says only that nothing is systematically
off.

---

## 3. The action-label problem

`output/action_labels.csv` is the share of attempts in each of eleven action
families, by season. The interesting boundary is 2014-15 to 2015-16:

| | 2014-15 | 2015-16 |
|---|---|---|
| Jump shot | 55.07% | 48.20% |
| Pull-up | 3.50% | 6.20% |
| Floater | 1.48% | 3.84% |
| Cut / roll layup | 1.82% | 4.39% |

Across the whole sample, "Layup" falls from 12.65% of all attempts to 1.58% and
"Bank" from 1.39% to 0.17%, while "Driving layup" doubles. These are not changes
in how the game is played over one summer. They are the league's play-by-play
vocabulary splitting into finer categories, and the finer categories eat the
coarse ones.

A model that reads action type across that boundary learns some basketball and
some calendar, and there is no way to tell from the fit which is which. Since
geometry has a fixed meaning — the arc is in the same place in both files — the
published model reads geometry.

The cost of that choice is bounded rather than assumed. `run_03_teams.py` fits
`full` as well and compares the 2024-25 team figures both ways
(`output/spec_sensitivity.csv`):

| Side | Component | Pearson | Spearman | Mean gap | Worst rank move |
|---|---|---|---|---|---|
| Offense | quality | 0.932 | 0.907 | 0.50 | 11 |
| Offense | making | 0.988 | 0.968 | 0.50 | 6 |
| Defense | quality | 0.975 | 0.966 | 0.35 | 7 |
| Defense | making | 0.987 | 0.986 | 0.35 | 3 |

Nothing in the README depends on a distinction smaller than half a point per 100.

---

## 4. Coordinates

Three of the fifteen season files — 2019-20, 2020-21, 2021-22 — are published
with `LOC_X` and `LOC_Y` divided by ten and the origin shifted, which is what you
get by applying the league's raw-units conversion twice.
`features.normalise_coordinates` detects the compression on every season by
checking whether the maximum absolute x is plausible for a fifty-foot court, and
inverts it. The independent check is the file's own `SHOT_DISTANCE` column,
rounded to the foot: after the repair the recomputed distance agrees with it to
within 0.49 feet on average in every season, and the build raises if any season
exceeds one foot.

Distance is recomputed from coordinates rather than read from `SHOT_DISTANCE`,
because the published column is rounded and the rounding puts visible banding in
the model's distance splits.

---

## 5. Split-half reliability

For a given half-size `n`, draw `2n` attempts without replacement from a
team-season, split them into two disjoint halves, compute quality and making on
each, and correlate across team-seasons. Average over repetitions — 200 for the
full-length figures, 60 for each point on the curve.

Two details:

**The sample of teams is fixed across the curve.** Every point uses only
team-seasons with enough attempts to supply the *largest* split. Without that,
the curve would be a statement about which teams drop out as the split grows,
which would flatter the small samples (short seasons have fewer attempts and
often more extreme teams).

**Spearman-Brown steps a half to a whole**: `r_full = 2r / (1 + r)`. Reported as
the `*_full` columns in `output/split_half.csv`. It assumes the two halves are
parallel measurements, which random splitting of a single season makes about as
true as it gets.

---

## 6. The noise floor

An independent, model-free bound on the same question. For a team with `n`
attempts, the sampling variance of its mean residual is `Var(points - xPPS) / n`,
and that per-shot variance is estimable from the team's own attempts. Average it
over the thirty teams in a season and compare to the observed variance of making
across those teams (`output/noise_share.csv`):

- 2024-25: observed SD 4.29, sampling SD 1.39, implied true SD **4.06**
- Across the fifteen seasons, sampling noise accounts for a mean of **13%** of the
  observed variance in team shot making.

This agrees with the split-half figure — a reliability of 0.83 implies 17% noise
— which is the point of computing it two ways.

The assumption is that a team's attempts are independent draws. They are not
quite: shots within a game share an opponent, a venue and a night's shooting
touch. Positive within-game correlation would make the true sampling variance
*larger* than this estimate, so 13% is a floor on the noise and 4.06 is a ceiling
on the true spread.

---

## 7. Correcting the year-over-year correlation

The raw year-to-year correlation confounds two things: how much of a trait a team
keeps, and how precisely one season measures the trait at all. The standard
correction divides by the reliability:

```
persistence = r(season t, season t+1) / reliability(one season)
```

This is the disattenuation formula with the same variable on both sides, so both
reliabilities are equal and the denominator is not squared under a root. Applied
to `output/split_half.csv` and `output/year_over_year.csv`, it gives the
corrected column in the README's second table.

What it licenses: a comparison between components measured with different
precision. Offensive quality is measured at 0.98 and making at 0.83, so their raw
correlations of 0.63 and 0.65 are not comparable as they stand.

What it does not license: treating 0.78 as a forecast. It is the correlation you
would observe between two *perfectly measured* seasons, and no such season
exists. For projection, the raw number is the one to use.

There is also a substantive confound underneath the whole exercise, and it is the
biggest limitation in the project. A public shot file has no defender data, so
every point of value a team creates by getting a shooter open lands in "making"
rather than "quality". Some of making's persistence is therefore persistent
spacing, not persistent shooting. I cannot separate them here, and I would not
trust anyone who claimed to without tracking data.

---

## 8. The seven-game resample

`quality.series_noise` draws `n` attempts with replacement from a team's own
2024-25 residuals and records the making figure the sample produces, four
thousand times. `n = 622` is the league's mean attempts per team-game in 2024-25
(88.9) times seven.

What this holds fixed is the team's shot distribution and its true conversion.
The only thing varying is which attempts you happened to see. That makes it a
**floor on the uncertainty**, not a forecast of a series: a playoff opponent
changes the distribution deliberately, rotations shorten, and the same seven
games are played against one defense rather than a season's worth. Every one of
those adds variance.

Regular-season attempts are used because they are the only attempts in the file.
The mirror carries no playoff games.

---

## 9. Shrinkage

`quality.shrink` multiplies each component by a single published reliability
factor. It is deliberately the flat version rather than a per-team empirical
Bayes weight: every team in a season plays 82 games and takes within a few
hundred attempts of the same number, so a per-team weight would move the ordering
by nothing and would make the estimator harder to argue with.

Two factors are applied to the same season. The season-length factor (0.83)
barely moves anything — a maximum of three places. The series-length factor
(0.38, with quality shrunk at 0.84 to match) is the interesting one, and the
README's rise-and-fall table is the difference between them.

---

## 10. Zone attribution

`zone_surplus` splits a team's quality into per-zone contributions:

```
from_mix  = 100 (team_share - league_share) (league_value_in_zone - league_value_overall)
from_look = 100  team_share (team_value_in_zone - league_value_in_zone)
```

The first is shot selection in the ordinary sense: shooting more often from a
zone the league scores well in. The second is finding better looks than the
league *inside* a zone — a rim attempt is not a fixed thing, and a team that gets
to the restricted area on cuts rather than contested drives will score above the
zone's league value before anyone shoots.

The two sum exactly to the team's quality figure, because the shares and the
league shares each sum to one. This is checked implicitly by the row totals in
figure 05 matching `output/team_offence.csv`.

---

## 11. What this cannot see

- **Free throws, turnovers, offensive rebounds.** Everything is per shot attempt.
  A team that gets to the line or takes care of the ball gets no credit here, and
  none of these numbers is an offensive or defensive rating.
- **Who was guarding.** Section 7.
- **Playoffs.** Regular season only, through 2024-25.
- **Franchise continuity.** Year-over-year pairs are matched on the three-letter
  abbreviation, so New Jersey to Brooklyn and New Orleans' rename each break the
  chain. 418 pairs rather than 420.
- **Injuries and rotations.** A team-season is one number. San Antonio's 2024-25
  is a season in which their defensive centerpiece missed the second half of the
  year, and nothing here adjusts for that.

---

## 12. What I expected to find and did not

I started this expecting shot making to be mostly noise at team level, on the
strength of how badly opponent three-point percentage repeats — the finding in
the sibling `okc-defence` repo, where it comes back at 0.16 year to year. It is
not. Over a full season, team shot making splits at 0.83 and repeats at 0.65, and
once you correct for measurement it is the more persistent of the two components
on both sides of the ball.

The reason the two results coexist: opponent three-point percentage is a small,
noisy slice of defensive making, and the rest of it — everything inside the arc —
repeats far better. Aggregating to the whole shot chart aggregates away the part
that does not stick.

What survives from the naive version is the part that matters for a playoff
series, and it survives for a different reason than I thought. Making is not
unreal. It is just slow, and a series is short: two 622-attempt samples of the
same team agree at 0.38, which is not enough to rank anybody.
