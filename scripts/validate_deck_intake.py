from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.intake_models import validate_deck_intake

DEFAULT_INTAKE_DIR = BASE_DIR / "data" / "intake"
SCHEMA_PATH = BASE_DIR / "config" / "deck_intake.schema.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def default_intake_paths() -> list[Path]:
    return sorted(DEFAULT_INTAKE_DIR.glob("*.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate deck intake JSON files.")
    parser.add_argument("paths", nargs="*", help="Intake JSON files. Defaults to data/intake/*.json.")
    return parser.parse_args()


def format_error(path: Path, error: ValidationError) -> str:
    lines = [f"{path}: validation failed"]
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"])
        lines.append(f"  - {location}: {item['msg']}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if not SCHEMA_PATH.exists():
        raise SystemExit(f"Missing schema: {SCHEMA_PATH}")
    load_json(SCHEMA_PATH)

    paths = [BASE_DIR / path if not Path(path).is_absolute() else Path(path) for path in args.paths]
    if not paths:
        paths = default_intake_paths()
    if not paths:
        raise SystemExit("No intake files found. Add JSON files under data/intake/ or pass paths explicitly.")

    failures: list[str] = []
    for path in paths:
        try:
            intake = validate_deck_intake(load_json(path))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{path}: {exc}")
            continue
        except ValidationError as exc:
            failures.append(format_error(path, exc))
            continue

        print(
            "ok "
            + json.dumps(
                {
                    "path": str(path.relative_to(BASE_DIR)),
                    "name": intake.name,
                    "deck_type": intake.deck_type.value,
                    "industry": intake.industry.value,
                    "slides": {
                        "min": intake.slide_count_range.min,
                        "max": intake.slide_count_range.max,
                    },
                    "variation_level": intake.variation_level.value,
                },
                ensure_ascii=False,
            )
        )

    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        return 1

    print(f"validated_intake_files={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
