# M4 D3 baseline comparison — 11 October 2026

Offline comparison implemented and executed on the fixed D2 seed-42 splits. This is applied statistical modeling on synthetic known-student data, not evidence of real-college effectiveness. Prediction API, risk screen and trusted artifact lifecycle remain unimplemented.

## Method

The five D1 features enter a median-imputation → standardization → logistic-regression pipeline. All fitted statistics use the 4,320 training examples only. C=1, lbfgs, max_iter=1000 and seed=42 were fixed before the evaluation. Convergence warnings fail the run. The threshold maximizes validation F1 over 0.05–0.95 in steps of 0.05, choosing the higher threshold on ties. The selected threshold was **0.35**. Test labels do not enter fitting or threshold selection.

Baselines: a training-prior DummyClassifier with a fixed 0.5 threshold, and the fixed rule that trailing attendance below 75% predicts future risk. The rule uses hard 0/1 scores for probability metrics; its Brier score is therefore an error rate, not a calibrated probability assessment. No baseline hyperparameter was tuned on test data. Implementation uses scikit-learn's documented [SimpleImputer](https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html) and [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).

## Untuned test results

2,160 examples; 805 positive labels (37.27%). Full validation/test metrics, provenance, dependency versions, preprocessing statistics and coefficients are in [raw results](m4-evaluation.json).

| Method | Precision | Recall | F1 | Average precision | Brier score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training prior | Undefined (no positive predictions) | 0.000 | 0.000 | 0.373 | 0.235 |
| Current-rate rule | 0.612 | 0.658 | 0.634 | 0.530 | 0.283 |
| Logistic regression | 0.565 | 0.773 | 0.653 | 0.635 | 0.186 |

Confusion matrices use `[[TN, FP], [FN, TP]]`: prior `[[1355, 0], [805, 0]]`; rule `[[1019, 336], [275, 530]]`; logistic `[[876, 479], [183, 622]]`. Logistic regression has a modest F1 increase and greater recall, at the cost of 143 additional false positives. No statistical significance or deployment recommendation is established.

Average precision is the non-interpolated precision–recall summary, explicitly named rather than claimed as trapezoidal PR-AUC. It is null when either class is absent. Other undefined metric denominators produce null. Single-class training/validation prevents fitting/threshold selection with a clear error.

## Verification and reproduction

Nine evaluation regression cases pass, including independent confusion/Brier arithmetic, undefined metrics, deterministic threshold ties, training-only imputation/scaling statistics and a test-label mutation proving the model and threshold unchanged. Combined M4/generator/state/simulation suite: **120 passed**. Ruff passed. Database/frontend suites were not rerun for this offline-only change.

Install the optional offline ML dependencies before running the evaluation **or the complete backend test suite**:

```powershell
uv pip install --python .venv/Scripts/python.exe -r backend/requirements-ml.lock
.\.venv\Scripts\python.exe scripts/evaluate_m4.py
```

The existing application dependencies remain in `backend/requirements.lock`; ML dependencies have a separate pinned lock. The script regenerates data and trains in memory, writing only aggregate JSON evidence. It does not save/load pickle or joblib model artifacts, access a database, or serve predictions.

## Remaining D4 work

Repeated students and overlapping within-partition horizons make rows correlated. Student-group uncertainty intervals, separately seeded/shifted attendance evaluation, explicit imbalance stress tests and sparse-history reporting remain open. Sparse history and weekly labs are excluded under D1, not assigned invented scores. Test results must not be used to retune this run; future modeling experiments need a new held-out evaluation protocol. D5 artifact persistence/API and D6 risk UI follow evaluation work.
