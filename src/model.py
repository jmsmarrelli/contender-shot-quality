"""The expected-value model.

xPPS is the points a league-average shooter would be expected to score on a
given attempt: P(make | where, how, when) times 2 or 3.

Three choices to be explicit about, because they are what separate this from a
zone lookup table:

* **Predictions are out-of-fold.** Folds are split by game, not by row, so no
  shot is scored by a model that saw another shot from the same game. Without
  this, a player's shot-making residual is partly the model memorising him.

* **No season term.** The model is a fixed yardstick held across 2010-2025. If
  season were a feature, league-wide changes in conversion would be absorbed
  into the expectation and every team's shot making would be measured against a
  standard that moves with it. This is the whole reason the decomposition works.

* **Two specifications, on purpose.** `GEO` uses geometry alone: distance, court
  position, angle, and whether the shot is worth three. `FULL` adds action type,
  period, clock and venue. FULL is the better classifier - lower log loss, higher
  AUC - and it is the wrong model here, because the league's action-type
  vocabulary changed underneath it inside this sample. Between 2014-15 and
  2015-16 the share of attempts logged as a plain "Jump shot" fell from 55% to
  48% and "Floater" more than doubled, and across the fifteen seasons "Layup"
  goes from 13% of all attempts to under 2% as the label splits into more
  specific ones. Feeding a model a feature whose definition drifts with the
  calendar is how you manufacture a trend. Geometry does not drift: the
  coordinate system and the arc are the same in every file. FULL is fit anyway,
  and run_03 reports what it would have done to the answer.

* **No defender data.** The public shot files carry location, action type and
  clock, and nothing about who was guarding. So "shot quality" here means the
  quality of the *look on the floor*, not of the possession. Openness is
  invisible, which is a real limit and is discussed in docs/method.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold

from config import N_FOLDS, SEED

GEO = {
    "numeric": ["dist", "abs_x", "y", "angle"],
    "binary": ["is_three"],
    "categorical": [],
}
FULL = {
    "numeric": ["dist", "abs_x", "y", "angle", "secs_left"],
    "binary": ["is_three", "is_home"],
    "categorical": ["family", "period"],
}
SPECS = {"geo": GEO, "full": FULL}


def features(spec: dict) -> list:
    return spec["numeric"] + spec["binary"] + spec["categorical"]


def design_matrix(df: pd.DataFrame, spec: dict = FULL) -> pd.DataFrame:
    X = df[features(spec)].copy()
    for col in spec["binary"]:
        X[col] = X[col].astype(int)
    for col in spec["categorical"]:
        X[col] = X[col].astype("category")
    return X


def new_estimator(**kw) -> HistGradientBoostingClassifier:
    params = dict(
        loss="log_loss",
        learning_rate=0.06,
        max_iter=400,
        max_leaf_nodes=48,
        min_samples_leaf=200,
        l2_regularization=1.0,
        early_stopping=True,
        n_iter_no_change=25,
        validation_fraction=0.08,
        categorical_features="from_dtype",
        random_state=SEED,
    )
    params.update(kw)
    return HistGradientBoostingClassifier(**params)


def fit_out_of_fold(df: pd.DataFrame, spec: dict = FULL, verbose: bool = True):
    """Return out-of-fold P(make) for every row, plus the per-fold estimators."""
    X = design_matrix(df, spec)
    y = df["made"].to_numpy().astype(int)
    groups = df["game_id"].to_numpy()

    oof = np.full(len(df), np.nan)
    models = []
    splitter = GroupKFold(n_splits=N_FOLDS)
    for k, (tr, te) in enumerate(splitter.split(X, y, groups), start=1):
        est = new_estimator()
        est.fit(X.iloc[tr], y[tr])
        oof[te] = est.predict_proba(X.iloc[te])[:, 1]
        models.append(est)
        if verbose:
            print(f"  fold {k}/{N_FOLDS}  train {len(tr):,}  score {len(te):,}  "
                  f"trees {est.n_iter_}")

    if np.isnan(oof).any():
        raise RuntimeError("some rows never landed in a test fold")
    return oof, models


def expected_points(p_make: np.ndarray, is_three: np.ndarray) -> np.ndarray:
    return p_make * np.where(is_three, 3.0, 2.0)


def calibration_table(p: np.ndarray, y: np.ndarray, bins: int = 20) -> pd.DataFrame:
    """Equal-count bins, so every row carries the same weight of evidence."""
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    return (
        pd.DataFrame({"bin": q, "p": p, "y": y})
        .groupby("bin", observed=True)
        .agg(n=("y", "size"), predicted=("p", "mean"), actual=("y", "mean"))
        .reset_index(drop=True)
    )
