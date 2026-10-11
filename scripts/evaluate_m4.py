"""Reproduce M4 D3 fixed-split baseline/model comparison."""

import json
import platform
import sys
from datetime import timedelta
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    from app.generator import GeneratorConfig, generate
    from app.risk_dataset import TemporalPlan, extract_examples
    from app.risk_evaluation import evaluate

    config = GeneratorConfig()
    rows = extract_examples(generate(config))
    start = rows[0].cutoff
    plan = TemporalPlan(validation_start=start + timedelta(weeks=8),
                        test_start=start + timedelta(weeks=12),
                        test_end=start + timedelta(weeks=16))
    report = {
        "scope": "Synthetic known-student forecasting; no real-college effectiveness claim",
        "edition_id": rows[0].edition_id, "edition_hash": rows[0].edition_hash,
        "generator_version": rows[0].generator_version,
        "config": config.model_dump(mode="json"),
        "policy": rows[0].policy.model_dump(mode="json"),
        "plan": plan.model_dump(mode="json"),
        "versions": {name: version(name) for name in ("numpy", "scipy", "scikit-learn")},
        "python": platform.python_version(),
        **evaluate(rows, plan),
    }
    path = ROOT / "docs" / "m4-evaluation.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report["results"]["test"], indent=2))


if __name__ == "__main__":
    main()
