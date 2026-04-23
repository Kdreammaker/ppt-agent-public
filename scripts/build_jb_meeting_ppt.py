from __future__ import annotations

from pathlib import Path

from build_deck import build_deck_from_spec


WORKDIR = Path(__file__).resolve().parents[1]
SPEC_PATH = WORKDIR / "data" / "specs" / "jb_meeting_deck_spec.json"


def main() -> Path:
    return build_deck_from_spec(SPEC_PATH)


if __name__ == "__main__":
    print(main())
