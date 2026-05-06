from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


CONTRACT_ID = "ppt-maker.public-setup-summary.v0"
OUTPUT_INTENTS = ("design_visual", "editable_office", "balanced")
CLASSIFICATIONS = (
    "native_editable_required",
    "editable_shape_table_allowed",
    "design_visual_allowed",
    "not_applicable",
)
PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/Users/"),
    re.compile(r"/home/"),
    re.compile(r"\bdrive[_-]?id\b", re.IGNORECASE),
    re.compile(r"\bsource_attachment\b", re.IGNORECASE),
    re.compile(r"\braw_payload\b", re.IGNORECASE),
    re.compile(r"\bprivate_prompt\b", re.IGNORECASE),
    re.compile(r"\baccess_token\b", re.IGNORECASE),
    re.compile(r"\brefresh_token\b", re.IGNORECASE),
    re.compile(r"\bapproved_asset_ref\b", re.IGNORECASE),
    re.compile(r"\bpreferred_asset_ref\b", re.IGNORECASE),
    re.compile(r"\bunapproved_asset_records\b", re.IGNORECASE),
)


class PublicSetupSummaryError(ValueError):
    """Raised when public setup summary input is unsafe or malformed."""


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()


def load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise PublicSetupSummaryError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def public_safe(payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False)
    hits = [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(raw)]
    if hits:
        raise PublicSetupSummaryError(f"public setup summary contains private marker patterns: {hits}")


def as_counts(value: Any, keys: tuple[str, ...]) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    counts: dict[str, int] = {}
    for key in keys:
        raw = source.get(key, 0)
        counts[key] = raw if isinstance(raw, int) and raw >= 0 else 0
    return counts


def setup_output_intents(setup_summary: dict[str, Any]) -> dict[str, Any]:
    options = setup_summary.get("output_intent_options")
    if isinstance(options, dict) and options.get("available") == list(OUTPUT_INTENTS):
        default = options.get("default") if options.get("default") in OUTPUT_INTENTS else "balanced"
    else:
        default = "balanced"
    return {
        "available": list(OUTPUT_INTENTS),
        "default": default,
        "behavior": "explanatory_metadata_only_no_renderer_change",
    }


def setup_sample_checkpoint(setup_summary: dict[str, Any]) -> dict[str, Any]:
    checkpoint = setup_summary.get("one_slide_sample_review_checkpoint")
    if not isinstance(checkpoint, dict):
        checkpoint = {}
    return {
        "recommended": bool(checkpoint.get("recommended", True)),
        "requires_explicit_approval_before_full_build": bool(
            checkpoint.get("requires_explicit_approval_before_full_build", True)
        ),
        "purpose": "Review one representative slide before committing to a full deck build.",
    }


def uploaded_knowledge_assets(setup_summary: dict[str, Any]) -> dict[str, Any]:
    summary = setup_summary.get("uploaded_knowledge_assets_summary")
    if not isinstance(summary, dict):
        summary = {}
    asset_state = as_counts(
        summary.get("asset_state_summary"),
        ("approved", "requested", "unknown"),
    )
    reference_count = summary.get("reference_file_count", 0)
    return {
        "reference_file_count": reference_count if isinstance(reference_count, int) and reference_count >= 0 else 0,
        "asset_state_summary": asset_state,
        "counts_only": True,
        "raw_sources_included": False,
    }


def editable_output_roles(setup_summary: dict[str, Any]) -> dict[str, Any]:
    roles = setup_summary.get("editable_output_explanation")
    if not isinstance(roles, dict):
        roles = {}
    return {
        "pptx": roles.get("pptx") or "native_editable_primary_output",
        "html": roles.get("html") or "review_or_presentation_companion",
        "shared_ir_role": roles.get("shared_ir_role") or "read_only_explanation_and_qa",
        "html_screenshot_used_in_pptx": False,
    }


def editable_chart_table_readiness(editable_readiness: dict[str, Any]) -> dict[str, Any]:
    diagnostics = editable_readiness.get("diagnostics_summary")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    return {
        "classification_values": list(CLASSIFICATIONS),
        "classification_counts": as_counts(diagnostics.get("classification_counts"), CLASSIFICATIONS),
        "candidate_count": diagnostics.get("candidate_count", 0)
        if isinstance(diagnostics.get("candidate_count"), int)
        else 0,
        "summary_only": True,
        "native_chart_table_rendering_enabled": False,
        "behavior": "explanatory_metadata_only_no_renderer_change",
    }


def artifact_status(path: Path | None) -> str:
    return path.name if path and path.exists() else "not_available"


def build_summary(
    *,
    setup_summary_path: Path | None = None,
    editable_readiness_path: Path | None = None,
) -> dict[str, Any]:
    setup_summary = load_json(setup_summary_path)
    editable_readiness = load_json(editable_readiness_path)
    payload = {
        "contract": CONTRACT_ID,
        "generated_at": utc_now(),
        "status": "ready",
        "source_artifacts": {
            "setup_ux_summary": artifact_status(setup_summary_path),
            "editable_office_readiness": artifact_status(editable_readiness_path),
        },
        "output_intent_options": setup_output_intents(setup_summary),
        "one_slide_sample_checkpoint": setup_sample_checkpoint(setup_summary),
        "uploaded_knowledge_assets_summary": uploaded_knowledge_assets(setup_summary),
        "editable_output_roles": editable_output_roles(setup_summary),
        "editable_chart_table_readiness": editable_chart_table_readiness(editable_readiness),
        "public_private_hygiene": {
            "raw_refs_included": False,
            "local_paths_included": False,
            "drive_ids_included": False,
            "tokens_included": False,
            "raw_payloads_included": False,
            "private_prompts_included": False,
            "unapproved_asset_records_included": False,
        },
        "non_goals": {
            "renderer_layout_or_content_changed": False,
            "native_editable_chart_table_rendering_enabled": False,
            "shared_ir_renderer_consumption_enabled": False,
            "auto_two_variant_policy_redesigned": False,
            "b49_asset_request_ux_enabled": False,
        },
    }
    public_safe(payload)
    return payload


def default_output(workspace: Path | None) -> Path:
    if workspace:
        return workspace / "outputs" / "reports" / "public_setup_summary.json"
    return Path("outputs") / "reports" / "public_setup_summary.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a public-safe setup UX summary report.")
    parser.add_argument("--workspace", help="Workspace root for default output location.")
    parser.add_argument("--setup-ux-summary", help="Optional internal setup-ux-summary.json to summarize.")
    parser.add_argument("--editable-office-readiness", help="Optional editable-office-readiness.json to summarize.")
    parser.add_argument("--output", help="Output JSON path.")
    args = parser.parse_args(argv)

    workspace = resolve_path(args.workspace)
    output = resolve_path(args.output) or default_output(workspace)
    assert output is not None
    payload = build_summary(
        setup_summary_path=resolve_path(args.setup_ux_summary),
        editable_readiness_path=resolve_path(args.editable_office_readiness),
    )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "report": output.name,
                "contract": payload["contract"],
                "output_intents": payload["output_intent_options"]["available"],
                "editable_chart_table_counts": payload["editable_chart_table_readiness"]["classification_counts"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
