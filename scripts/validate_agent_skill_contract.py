from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


REQUIRED_SKILL_PHRASES = [
    "Assistant mode is the default",
    "Auto mode must generate two distinct PPTX variants",
    "guide-data.public.json is the primary machine input",
    "HTML guide output is human review evidence only",
    "Do not insert an HTML guide screenshot into PPTX content",
    "Sparse Request Intake",
    "intent-profile.json",
    "routing-report.json",
    "Optional AI nearest-label matching must stay inside",
]


def main() -> int:
    skill_path = BASE_DIR / "skills" / "ppt-agent" / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(skill_path)
    text = skill_path.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_SKILL_PHRASES if phrase not in text]

    report = {
        "status": "pass" if not missing else "fail",
        "skill_path": "skills/ppt-agent/SKILL.md",
        "checked_phrases": REQUIRED_SKILL_PHRASES,
        "missing": missing,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
