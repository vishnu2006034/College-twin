from datetime import timedelta

import numpy as np
import pytest

from app.generator import GeneratorConfig, generate
from app.risk_dataset import TemporalPlan, extract_examples, partition_examples
from app.risk_evaluation import arrays, evaluate, fit_models, metrics, select_threshold


@pytest.fixture(scope="module")
def data():
    rows = extract_examples(generate(GeneratorConfig(students_per_section=1)))
    start = rows[0].cutoff
    plan = TemporalPlan(validation_start=start + timedelta(weeks=8),
                        test_start=start + timedelta(weeks=12),
                        test_end=start + timedelta(weeks=16))
    return rows, plan


def test_independent_confusion_and_probability_arithmetic():
    result = metrics([0, 0, 1, 1], [.1, .6, .4, .8], [0, 1, 0, 1])
    assert result["confusion_matrix"] == [[1, 1], [1, 1]]
    assert result["precision"] == result["recall"] == result["f1"] == .5
    assert result["brier_score"] == pytest.approx((.01 + .36 + .36 + .04) / 4)
    assert result["average_precision"] == pytest.approx(5 / 6)


def test_undefined_metrics_not_fabricated():
    result = metrics([0, 0], [.1, .2], [0, 0])
    assert result["average_precision"] is None
    assert result["precision"] is None
    assert result["recall"] is None
    assert result["f1"] is None
    assert result["both_classes_present"] is False


def test_threshold_uses_validation_f1_and_deterministic_ties():
    assert select_threshold(np.array([0, 1]), np.array([.2, .8])) == .8
    with pytest.raises(ValueError):
        select_threshold(np.array([1, 1]), np.array([.2, .8]))


def test_preprocessing_statistics_are_training_only(data):
    rows, plan = data
    split = partition_examples(rows, plan)["partitions"]
    model, _, _ = fit_models(split["train"], split["validation"])
    x, _ = arrays(split["train"])
    medians = np.nanmedian(x, axis=0)
    expected = np.where(np.isnan(x), medians, x)
    np.testing.assert_allclose(model.named_steps["simpleimputer"].statistics_, medians)
    np.testing.assert_allclose(model.named_steps["standardscaler"].mean_, expected.mean(axis=0))


def test_test_labels_cannot_change_model_or_threshold(data):
    rows, plan = data
    baseline = evaluate(rows, plan)
    changed = []
    for row in rows:
        calculation = row.calculation
        if row.cutoff >= plan.test_start and calculation.label is not None:
            calculation = calculation.model_copy(update={"label": not calculation.label})
        changed.append(row.model_copy(update={"calculation": calculation}))
    result = evaluate(changed, plan)
    for key in ("logistic_threshold", "training_imputation_medians", "training_scaler_means",
                "logistic_coefficients", "logistic_intercept"):
        assert result[key] == baseline[key]
    assert result["results"]["validation"] == baseline["results"]["validation"]
    assert result["results"]["test"] != baseline["results"]["test"]


def test_one_class_training_and_empty_input_rejected(data):
    rows, plan = data
    split = partition_examples(rows, plan)["partitions"]
    train = [r.model_copy(update={"calculation": r.calculation.model_copy(update={"label": True})})
             for r in split["train"]]
    with pytest.raises(ValueError, match="training classes"):
        fit_models(train, split["validation"])
    with pytest.raises(ValueError):
        arrays([])


@pytest.mark.parametrize("scores", [[float("nan")], [1.1], [-.1]])
def test_invalid_probability_rejected(scores):
    with pytest.raises(ValueError):
        metrics([1], scores, [1])
