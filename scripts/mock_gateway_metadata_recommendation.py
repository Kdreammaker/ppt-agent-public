from __future__ import annotations

import argparse
import json
import uuid
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "gateway_metadata_recommendation_mock.json"
B49_REPORT_PATH = BASE_DIR / "outputs" / "reports" / "reference_quality_dna.json"
DEFAULT_SPEC_PATH = BASE_DIR / "data" / "specs" / "business_growth_review_spec.json"
DEFAULT_REPORT_JSON = BASE_DIR / "outputs" / "reports" / "gateway_metadata_recommendation_mock.json"
DEFAULT_REPORT_MD = BASE_DIR / "outputs" / "reports" / "gateway_metadata_recommendation_mock.md"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def relative(path: Path) -> str:
    return path.resolve().relative_to(BASE_DIR).as_posix()


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def infer_industry(spec: dict[str, Any]) -> str:
    recipe = str(spec.get("recipe", ""))
    if recipe.startswith("industry:"):
        return recipe.split(":", 1)[1]
    return "other"


def infer_deck_type(spec: dict[str, Any]) -> str:
    industry = infer_industry(spec)
    if industry in {"business", "finance"}:
        return "business"
    return industry or "other"


def summarize_asset_intents(spec: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = []
    for intent in spec.get("asset_intents", []):
        if not isinstance(intent, dict):
            continue
        summaries.append(
            {
                "role": intent.get("role"),
                "asset_class": intent.get("asset_class"),
                "asset_id": intent.get("asset_id"),
                "slide_number": intent.get("slide_number"),
                "purpose": intent.get("purpose"),
                "source_policy": intent.get("source_policy"),
                "materialization": intent.get("materialization"),
                "license_action": intent.get("license_action"),
                "risk_level": intent.get("risk_level"),
            }
        )
    return summaries


def summarize_reference_dna(b49_report: dict[str, Any], slide_purposes: list[str], limit: int = 8) -> list[dict[str, Any]]:
    purpose_set = set(slide_purposes)
    records = b49_report.get("eligible_lightweight_dna", {}).get("records", [])
    selected = []
    for record in records:
        if record.get("purpose") not in purpose_set:
            continue
        dna = record.get("lightweight_dna", {})
        selected.append(
            {
                "slide_id": record.get("slide_id"),
                "template_key": record.get("template_key"),
                "purpose": record.get("purpose"),
                "scope": record.get("scope"),
                "quality_score": record.get("quality_score"),
                "usage_policy": record.get("usage_policy"),
                "layout_role": dna.get("layout_role"),
                "visual_density": dna.get("visual_density"),
                "palette_hints": as_list(dna.get("palette_hints"))[:4],
                "image_treatment": dna.get("image_treatment"),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def build_metadata_request(
    *,
    spec: dict[str, Any],
    b49_report: dict[str, Any],
    config: dict[str, Any],
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key_to_purpose = {
        str(record.get("template_key")): str(record.get("purpose"))
        for record in b49_report.get("eligible_lightweight_dna", {}).get("records", [])
        if record.get("template_key") and record.get("purpose")
    }
    slide_purposes = []
    for slide in spec.get("slides", []):
        if not isinstance(slide, dict):
            continue
        template_key = str(slide.get("template_key") or "")
        selector_purpose = slide.get("slide_selector", {}).get("purpose") if isinstance(slide.get("slide_selector"), dict) else None
        slide_purposes.append(key_to_purpose.get(template_key) or str(selector_purpose or "content"))
    request = {
        "request_id": f"mock_rec_{uuid.uuid4().hex[:12]}",
        "request_type": config.get("request_type", "recommend_templates"),
        "workspace_policy": "gateway_metadata_mock",
        "operating_mode": "gateway_ai",
        "deck_type": infer_deck_type(spec),
        "industry": infer_industry(spec),
        "tone": ["executive", "analytical"],
        "slide_count": len(spec.get("slides", [])),
        "slide_purposes": slide_purposes,
        "asset_intent_summaries": summarize_asset_intents(spec),
        "quality_gap_summary": b49_report.get("quality_gap_summary", {}),
        "reference_dna_summaries": summarize_reference_dna(b49_report, slide_purposes),
        "entitlement_handle": {
            "activation_model": "workspace_code_only",
            "workspace_code_mask": "BETA...0001",
            "raw_code_included": False,
        },
        "preflight_payload_preview": {
            "payload_class": "metadata_only",
            "request_type": config.get("request_type", "recommend_templates"),
            "field_names": list(config.get("allowed_request_fields", [])),
            "forbidden_fields_present": [],
            "file_upload_allowed": False,
            "full_content_upload_allowed": False,
            "gateway_call_enabled": bool(config.get("gateway_call_enabled", False)),
            "real_gateway_recommendation_enabled": bool(config.get("real_gateway_recommendation_enabled", False)),
        },
        "consent": dict(config.get("consent", {})),
    }
    if extra_fields:
        request.update(extra_fields)
    return request


def validate_request(config: dict[str, Any], request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    forbidden = set(config.get("forbidden_request_fields", []))
    allowed = set(config.get("allowed_request_fields", []))
    for key in request:
        if key in forbidden:
            errors.append(f"forbidden request field present: {key}")
        if key not in allowed and key not in forbidden:
            errors.append(f"unexpected request field present: {key}")
    consent = request.get("consent", {})
    if not isinstance(consent, dict):
        errors.append("consent must be an object")
    else:
        for key in ("file_upload_allowed", "full_content_upload_allowed", "telemetry_enabled", "learning_collection_enabled"):
            if consent.get(key) is not False:
                errors.append(f"consent.{key} must be false")
    entitlement = request.get("entitlement_handle", {})
    if not isinstance(entitlement, dict) or entitlement.get("raw_code_included") is not False:
        errors.append("entitlement handle must not include raw workspace code")
    preview = request.get("preflight_payload_preview", {})
    if not isinstance(preview, dict):
        errors.append("preflight payload preview must be present")
    else:
        if preview.get("payload_class") != "metadata_only":
            errors.append("preflight payload preview must be metadata_only")
        if preview.get("file_upload_allowed") is not False or preview.get("full_content_upload_allowed") is not False:
            errors.append("preflight payload preview must show uploads disabled")
        if preview.get("real_gateway_recommendation_enabled") is not False:
            errors.append("real gateway recommendation must remain disabled")
    if not request.get("reference_dna_summaries"):
        errors.append("request must include at least one B49 reference DNA summary")
    for summary in request.get("reference_dna_summaries", []):
        if summary.get("usage_policy") != "production_ready":
            errors.append(f"non-production DNA summary included: {summary.get('slide_id')}")
    serialized = json.dumps(request, ensure_ascii=False)
    for token in ("<html", "PK\x03\x04", "assets/slides/references/"):
        if token in serialized:
            errors.append(f"forbidden payload token found: {token!r}")
    return errors


def mock_response(config: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    responses = config.get("mock_responses", {})
    return {
        "request_id": request.get("request_id"),
        "status": "mocked",
        "gateway_call_performed": False,
        "fixture_backed_only": True,
        "recommendations": [
            responses.get("template_recommendation", {}),
            responses.get("palette_recommendation", {}),
            responses.get("asset_class_recommendation", {}),
            responses.get("review_suggestion", {}),
        ],
        "policy_summary": {
            "metadata_only": True,
            "file_upload_allowed": False,
            "raw_reference_paths_allowed": False,
            "uses_b49_reference_dna": True,
            "real_gateway_recommendation_enabled": False,
            "fallback_behavior": config.get("local_fallback_behavior", {}),
        },
    }


def build_report(config: dict[str, Any], spec: dict[str, Any], b49_report: dict[str, Any]) -> dict[str, Any]:
    fixture_results = []
    valid_request = build_metadata_request(spec=spec, b49_report=b49_report, config=config)
    for fixture in config.get("fixtures", []):
        request = build_metadata_request(
            spec=spec,
            b49_report=b49_report,
            config=config,
            extra_fields=fixture.get("extra_request_fields"),
        )
        errors = validate_request(config, request)
        actual = "invalid" if errors else "valid"
        fixture_results.append(
            {
                "name": fixture.get("name"),
                "expected": fixture.get("expected"),
                "actual": actual,
                "errors": errors,
            }
        )
    errors = [
        f"{item['name']} expected {item['expected']} got {item['actual']}: {item['errors']}"
        for item in fixture_results
        if item["expected"] != item["actual"]
    ]
    request_errors = validate_request(config, valid_request)
    errors.extend(request_errors)
    response = mock_response(config, valid_request)
    return {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {
            "errors": len(errors),
            "fixture_results": len(fixture_results),
            "valid_fixtures": sum(1 for item in fixture_results if item["actual"] == "valid"),
            "invalid_fixtures": sum(1 for item in fixture_results if item["actual"] == "invalid"),
            "asset_intent_summaries": len(valid_request.get("asset_intent_summaries", [])),
            "reference_dna_summaries": len(valid_request.get("reference_dna_summaries", [])),
        },
        "errors": errors,
        "metadata_request": valid_request,
        "mock_response": response,
        "fixture_results": fixture_results,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Gateway Metadata-Only Recommendation Mock",
        "",
        f"- Status: `{report['status']}`",
        f"- Fixture results: `{summary['fixture_results']}`",
        f"- Asset intent summaries: `{summary['asset_intent_summaries']}`",
        f"- Reference DNA summaries: `{summary['reference_dna_summaries']}`",
        f"- Gateway call performed: `{report['mock_response']['gateway_call_performed']}`",
        "",
        "## Policy",
        "",
        "- Request is metadata-only and fixture-backed.",
        "- Full specs, generated HTML, binary PPTX, local image binaries, raw reference paths, and raw workspace codes are rejected.",
        "- B49 production-ready lightweight DNA summaries are allowed.",
        "",
    ]
    if report["errors"]:
        lines.append("## Errors")
        lines.append("")
        lines.extend(f"- {error}" for error in report["errors"])
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a metadata-only gateway recommendation mock report.")
    parser.add_argument("--config", default=CONFIG_PATH.as_posix())
    parser.add_argument("--spec", default=DEFAULT_SPEC_PATH.as_posix())
    parser.add_argument("--b49-report", default=B49_REPORT_PATH.as_posix())
    parser.add_argument("--report-json", default=DEFAULT_REPORT_JSON.as_posix())
    parser.add_argument("--report-md", default=DEFAULT_REPORT_MD.as_posix())
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (BASE_DIR / config_path).resolve()
    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = (BASE_DIR / spec_path).resolve()
    b49_path = Path(args.b49_report)
    if not b49_path.is_absolute():
        b49_path = (BASE_DIR / b49_path).resolve()
    report_json = Path(args.report_json)
    if not report_json.is_absolute():
        report_json = (BASE_DIR / report_json).resolve()
    report_md = Path(args.report_md)
    if not report_md.is_absolute():
        report_md = (BASE_DIR / report_md).resolve()

    config = load_json(config_path)
    spec = load_json(spec_path)
    b49_report = load_json(b49_path)
    report = build_report(config, spec, b49_report)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_md.write_text(markdown_report(report), encoding="utf-8")
    if args.check and report["errors"]:
        for error in report["errors"]:
            print(f"ERROR: {error}")
        return 1
    print(
        "gateway_metadata_recommendation_mock=valid "
        f"fixtures={report['summary']['fixture_results']} "
        f"dna={report['summary']['reference_dna_summaries']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
