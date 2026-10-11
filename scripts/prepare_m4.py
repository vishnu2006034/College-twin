"""Generate deterministic M4 D2 evidence without fitting or persisting any model."""

import json
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

def main():
    from app.generator import GeneratorConfig, generate
    from app.risk_dataset import (
        TemporalPlan,
        extract_examples,
        partition_examples,
        summarize,
    )

    config = GeneratorConfig()
    dataset = generate(config)
    rows = extract_examples(dataset)
    start = rows[0].cutoff
    plan = TemporalPlan(validation_start=start + timedelta(weeks=8),
                        test_start=start + timedelta(weeks=12),
                        test_end=start + timedelta(weeks=16))
    report = {
        "scope": "Synthetic generator v1; weekly midnight IST cutoffs; no model fitted",
        "config": config.model_dump(mode="json"),
        "edition_id": rows[0].edition_id, "edition_hash": rows[0].edition_hash,
        "policy": rows[0].policy.model_dump(mode="json"),
        "split_plan": plan.model_dump(mode="json"),
        **summarize(rows, partition_examples(rows, plan)),
    }
    path = ROOT / "docs" / "m4-dataset-verification.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
