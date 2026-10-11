"""Offline M4 baseline comparison. No serialized executable models or API changes."""

import warnings

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.risk_dataset import ExampleRow, TemporalPlan, partition_examples

FEATURES = (
    "attendance_rate", "observed_sessions", "consecutive_absences", "attendance_trend", "coverage",
)
THRESHOLDS = tuple(i / 100 for i in range(5, 96, 5))


def arrays(rows: list[ExampleRow]):
    if not rows or any(r.calculation.features is None or r.calculation.label is None for r in rows):
        raise ValueError("Evaluation requires nonempty eligible examples")
    x = np.array([[getattr(r.calculation.features, key) for key in FEATURES] for r in rows],
                 dtype=float)
    y = np.array([int(r.calculation.label) for r in rows])
    return x, y


def metrics(y, scores, predictions):
    y, scores, predictions = np.asarray(y), np.asarray(scores), np.asarray(predictions)
    if not len(y) or scores.shape != y.shape or predictions.shape != y.shape:
        raise ValueError("Metric arrays must have equal nonzero length")
    if not np.isin(y, [0, 1]).all() or not np.isin(predictions, [0, 1]).all():
        raise ValueError("Labels must be binary")
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Scores must be finite and between zero and one")
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y, predictions, labels=[0, 1]).ravel())
    two_classes = len(np.unique(y)) == 2
    return {
        "examples": len(y), "prevalence": float(y.mean()),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "average_precision": float(average_precision_score(y, scores)) if two_classes else None,
        "brier_score": float(brier_score_loss(y, scores)),
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "both_classes_present": two_classes,
    }


def select_threshold(y_validation, scores):
    if len(np.unique(y_validation)) != 2:
        raise ValueError("Threshold selection requires both validation classes")
    # Predeclared grid; maximize validation F1, then prefer the higher threshold.
    return max(THRESHOLDS, key=lambda t: (
        metrics(y_validation, scores, np.asarray(scores) >= t)["f1"] or 0, t,
    ))


def fit_models(train, validation):
    x_train, y_train = arrays(train)
    x_validation, y_validation = arrays(validation)
    if len(np.unique(y_train)) != 2:
        raise ValueError("Logistic regression requires both training classes")
    model = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(), LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=42),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(x_train, y_train)
    dummy = DummyClassifier(strategy="prior").fit(x_train, y_train)
    threshold = select_threshold(y_validation, model.predict_proba(x_validation)[:, 1])
    return model, dummy, threshold


def evaluate(rows: list[ExampleRow], plan: TemporalPlan) -> dict:
    split = partition_examples(rows, plan)["partitions"]
    # Test rows cannot enter the fitting/selection interface.
    model, dummy, threshold = fit_models(split["train"], split["validation"])
    result = {
        "features": list(FEATURES), "logistic_threshold": threshold,
        "selection": "Validation F1 on 0.05..0.95 step 0.05; ties choose higher threshold",
        "parameters": {"C": 1.0, "solver": "lbfgs", "max_iter": 1000, "random_state": 42},
        "training_imputation_medians": model.named_steps["simpleimputer"].statistics_.tolist(),
        "training_scaler_means": model.named_steps["standardscaler"].mean_.tolist(),
        "training_scaler_scales": model.named_steps["standardscaler"].scale_.tolist(),
        "logistic_coefficients": model.named_steps["logisticregression"].coef_[0].tolist(),
        "logistic_intercept": float(model.named_steps["logisticregression"].intercept_[0]),
        "results": {},
    }
    for name in ("validation", "test"):
        x, y = arrays(split[name])
        logistic_scores = model.predict_proba(x)[:, 1]
        prior = dummy.predict_proba(x)[:, 1]
        # The rule is deliberately fixed, not optimized using held-out outcomes.
        rule = (x[:, 0] < rows[0].policy.risk_threshold).astype(int)
        result["results"][name] = {
            "dummy_prior": metrics(y, prior, prior >= 0.5),
            "current_rate_rule": metrics(y, rule.astype(float), rule),
            "logistic_regression": metrics(y, logistic_scores, logistic_scores >= threshold),
        }
    return result
