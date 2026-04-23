from __future__ import annotations

import json
from pathlib import Path

import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.deck_models import deck_spec_json_schema

SCHEMA_PATH = BASE_DIR / "config" / "deck_spec.schema.json"


def main() -> int:
    schema = deck_spec_json_schema()
    schema["$id"] = "https://local.ppt-test/deck_spec.schema.json"
    schema["title"] = "PPTX Deck Spec"
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    print(SCHEMA_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
