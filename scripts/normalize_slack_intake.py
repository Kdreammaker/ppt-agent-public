from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
CONTRACT_PATH = BASE_DIR / "config" / "slack_intake_contract.json"
DECK_INTAKE_SCHEMA_REF = "config/deck_intake.schema.json"
SUPPORTED_MODES = {"auto", "assistant"}
RAW_PATH_RE = re.compile(r"([A-Za-z]:\\|/Users/|/home/|\\\\)")

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.intake_models import validate_deck_intake


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "slack_request"


def request_id_for(raw: dict[str, Any]) -> str:
    existing = raw.get("request_id")
    if isinstance(existing, str) and existing.strip():
        return slugify(existing)
    channel = slugify(str(raw.get("channel_id") or "channel"))
    ts = slugify(str(raw.get("message_ts") or "message"))
    return f"slack_{channel}_{ts}"[:80]


def as_list(value: Any, default: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or default
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in re.split(r"[,;\n]+", value) if item.strip()] or default
    return default


def as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def first_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    for separator in (". ", "\n", " - ", ": "):
        if separator in cleaned:
            return cleaned.split(separator, 1)[0].strip()
    return cleaned[:72].strip()


def normalize(raw: dict[str, Any], *, output_root: Path | None = None) -> dict[str, Any]:
    contract = load_json(CONTRACT_PATH)
    defaults = contract.get("defaults", {})
    errors: list[str] = []
    warnings: list[str] = []
    defaulted_fields: list[str] = []
    blocked_asset_boundary_issues: list[str] = []

    for field in contract.get("required_raw_fields", []):
        if raw.get(field) in (None, ""):
            errors.append(f"missing required raw field: {field}")

    text = str(raw.get("text") or "").strip()
    if RAW_PATH_RE.search(text):
        blocked_asset_boundary_issues.append("Slack text appears to reference a raw local path; request approved manifest or materialized export package instead.")

    operating_mode = str(raw.get("operating_mode") or defaults.get("operating_mode") or "assistant").strip().lower()
    if operating_mode not in SUPPORTED_MODES:
        errors.append(f"unsupported operating_mode: {operating_mode}")

    request_id = request_id_for(raw)
    project_root = output_root or (BASE_DIR / "outputs" / "projects" / request_id)
    title = str(raw.get("title") or "").strip()
    if not title and text:
        title = first_sentence(text)
        defaulted_fields.append("title")
    if not title:
        errors.append("missing title and no text available for fallback")

    primary_goal = str(raw.get("primary_goal") or "").strip()
    if not primary_goal and text:
        primary_goal = text
        defaulted_fields.append("primary_goal")
    if not primary_goal:
        errors.append("missing primary_goal and no text available for fallback")

    audience = str(raw.get("audience") or "leadership").strip()
    if not raw.get("audience"):
        defaulted_fields.append("audience")

    deck_type = str(raw.get("deck_type") or defaults.get("deck_type") or "report").strip()
    industry = str(raw.get("industry") or defaults.get("industry") or "business").strip()
    tone = as_list(raw.get("tone"), list(defaults.get("tone") or ["executive"]))
    slide_count = max(1, as_int(raw.get("slide_count"), int(defaults.get("slide_count_max", 8))))
    slide_min = max(1, min(slide_count, int(defaults.get("slide_count_min", 5))))
    slide_max = max(slide_min, slide_count)
    approval_mode = str(raw.get("approval_mode") or defaults.get("approval_mode") or ("assistant" if operating_mode == "assistant" else "none"))
    if operating_mode == "auto" and "approval_mode" not in raw:
        approval_mode = "none"

    brand_profile_id = raw.get("brand_profile_id")
    approved_asset_manifest_id = raw.get("approved_asset_manifest_id")
    notes_parts = [
        f"slack_request_id={request_id}",
        f"operating_mode={operating_mode}",
    ]
    if isinstance(brand_profile_id, str) and brand_profile_id.strip():
        notes_parts.append(f"brand_profile_id={brand_profile_id.strip()}")
    if isinstance(approved_asset_manifest_id, str) and approved_asset_manifest_id.strip():
        notes_parts.append(f"approved_asset_manifest_id={approved_asset_manifest_id.strip()}")
    if blocked_asset_boundary_issues:
        notes_parts.append("asset_boundary=approved_manifest_required")

    intake = {
        "$schema": DECK_INTAKE_SCHEMA_REF,
        "intake_version": "1.0",
        "name": title,
        "audience": {
            "primary": audience,
            "secondary": [],
            "knowledge_level": defaults.get("knowledge_level", "informed"),
            "decision_role": defaults.get("decision_role", "decision_maker"),
        },
        "presentation_context": {
            "setting": "Slack maker request",
            "delivery_mode": defaults.get("delivery_mode", "async_readout"),
            "duration_minutes": None,
            "presenter_role": None,
            "locale": str(raw.get("locale") or "ko-KR"),
        },
        "primary_goal": primary_goal,
        "deck_type": deck_type,
        "industry": industry,
        "tone": tone,
        "slide_count_range": {"min": slide_min, "max": slide_max},
        "brand_or_template_scope": {
            "preferred_scope": None,
            "preferred_template_keys": [],
            "required_template_library": None,
            "theme_path": None,
            "notes": "; ".join(notes_parts),
        },
        "content_density": str(raw.get("content_density") or defaults.get("content_density") or "medium"),
        "variation_level": "single_path" if operating_mode == "auto" else "light_variants",
        "review_requirements": {
            "needs_variant_review": operating_mode == "assistant",
            "requires_rationale_report": True,
            "requires_slot_map": True,
            "reviewers": [str(raw.get("user_id"))] if raw.get("user_id") else [],
            "approval_mode": approval_mode,
        },
        "must_include": as_list(raw.get("must_include"), [primary_goal]),
        "must_avoid": as_list(raw.get("must_avoid"), []),
        "source_materials": [
            {
                "path": str(item.get("path")),
                "kind": str(item.get("kind") or "other"),
                "description": item.get("description"),
            }
            for item in raw.get("attachments", [])
            if isinstance(item, dict) and item.get("path")
        ],
        "output_preferences": {
            "output_spec_path": f"data/specs/{request_id}_spec.json",
            "output_deck_path": f"outputs/decks/{request_id}.pptx",
            "required_reports": [
                "slide_selection_rationale",
                "deck_slot_map",
                "quality_gate_summary",
            ],
        },
        "notes": "\n".join(notes_parts),
    }

    status = "normalized"
    try:
        validate_deck_intake(intake)
    except Exception as exc:  # pydantic carries field details; keep the report compact.
        errors.append(f"deck intake validation failed: {exc}")

    if blocked_asset_boundary_issues:
        status = "blocked_asset_boundary_issue"
    elif errors:
        status = "malformed"
    elif defaulted_fields and operating_mode == "assistant":
        status = "needs_clarification"
        warnings.append("Assistant request used defaults; ask a short clarification before unattended final build.")

    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "status": status,
        "operating_mode": operating_mode,
        "defaulted_fields": defaulted_fields,
        "warnings": warnings,
        "errors": errors,
        "blocked_asset_boundary_issues": blocked_asset_boundary_issues,
        "artifact_paths": {
            "request_summary": (project_root / "intake" / "slack_request_summary.json").resolve().as_posix(),
            "deck_intake": (project_root / "intake" / "deck_intake.json").resolve().as_posix(),
            "normalization_report": (project_root / "reports" / "slack_intake_normalization.json").resolve().as_posix(),
        },
        "raw_summary": {
            "workspace_id": raw.get("workspace_id"),
            "channel_id": raw.get("channel_id"),
            "user_id": raw.get("user_id"),
            "message_ts": raw.get("message_ts"),
            "text_chars": len(text),
            "attachments": len(raw.get("attachments", [])) if isinstance(raw.get("attachments"), list) else 0,
        },
        "normalized_intake": intake,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize a Slack maker request into a deck intake artifact.")
    parser.add_argument("request_json")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    request_path = Path(args.request_json)
    if not request_path.is_absolute():
        request_path = (BASE_DIR / request_path).resolve()
    output_root = Path(args.output_root).resolve() if args.output_root else None
    raw = load_json(request_path)
    report = normalize(raw, output_root=output_root)

    artifacts = report["artifact_paths"]
    write_json(Path(artifacts["request_summary"]), {"schema_version": "1.0", "request_id": report["request_id"], "raw_summary": report["raw_summary"]})
    write_json(Path(artifacts["deck_intake"]), report["normalized_intake"])
    write_json(Path(artifacts["normalization_report"]), {key: value for key, value in report.items() if key != "normalized_intake"})
    print(json.dumps({key: value for key, value in report.items() if key != "normalized_intake"}, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "normalized" or (args.check and report["status"] in {"needs_clarification", "blocked_asset_boundary_issue", "malformed"}) else 2


if __name__ == "__main__":
    raise SystemExit(main())
