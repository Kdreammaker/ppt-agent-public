from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.strategy_router import classify_intent, create_request_intake, summarize_sources


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    taxonomy_path = BASE_DIR / "config" / "deck_intent_taxonomy.json"
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    families = {family["id"]: family for family in taxonomy["families"]}
    required_families = {
        "ir_pitch",
        "executive_report",
        "public_institution_report",
        "portfolio",
        "product_introduction",
        "sales_proposal",
        "education_training",
        "research_analysis",
        "marketing_campaign",
        "event_travel",
        "media_entertainment",
        "status_update",
    }
    assert_true(required_families.issubset(families), "taxonomy missing required families")
    assert_true(len(taxonomy.get("examples", [])) >= 40, "taxonomy needs at least 40 sparse examples")
    for family in taxonomy["families"]:
        assert_true(family.get("keywords"), f"family {family['id']} has no keywords")
        assert_true(family.get("subtypes"), f"family {family['id']} has no subtypes")
    failures = []
    for example in taxonomy["examples"]:
        intake = create_request_intake(example["text"], mode="assistant")
        summary = summarize_sources(example["text"], intake)
        intent = classify_intent(intake, summary)
        if intent["deck_family"] != example["family"] or intent["sector_subtype"] != example["subtype"]:
            failures.append(
                {
                    "text": example["text"],
                    "expected": [example["family"], example["subtype"]],
                    "actual": [intent["deck_family"], intent["sector_subtype"]],
                    "confidence": intent["confidence"],
                }
            )
    assert_true(not failures, f"taxonomy example classification failures: {failures[:5]}")
    print(json.dumps({"status": "pass", "families": len(families), "examples": len(taxonomy["examples"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
