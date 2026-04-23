from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
POLICY_PATH = BASE_DIR / "config" / "reference_quality_dna_policy.json"
REFERENCE_CATALOG_PATH = BASE_DIR / "config" / "reference_catalog.json"
TEMPLATE_DNA_PATH = BASE_DIR / "config" / "template_design_dna.json"
REFERENCE_ROOT = BASE_DIR / "assets" / "slides" / "references"
DEFAULT_REPORT_JSON = BASE_DIR / "outputs" / "reports" / "reference_quality_dna.json"
DEFAULT_REPORT_MD = BASE_DIR / "outputs" / "reports" / "reference_quality_dna.md"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def relative(path: Path) -> str:
    return path.resolve().relative_to(BASE_DIR).as_posix()


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def classify_reference_file(path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    name = path.name
    lowered = name.casefold()
    classification = str(policy.get("reference_folder_policy", {}).get("default_classification", "raw_only"))
    reasons = ["local reference folder files are analysis inputs only"]
    if "generated" in lowered:
        classification = "blocked"
        reasons.append("generated reference deck cannot become production-selectable")
    if path.suffix.lower() != ".pptx":
        classification = "blocked"
        reasons.append("non-pptx file is not eligible for reference deck analysis")
    return {
        "file_name": name,
        "relative_path": relative(path),
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "classification": classification,
        "may_be_summarized_locally": bool(policy.get("reference_folder_policy", {}).get("may_be_summarized_locally", True)),
        "may_be_exported_publicly": False,
        "production_selectable": False,
        "reasons": reasons,
    }


def inventory_reference_folder(policy: dict[str, Any]) -> dict[str, Any]:
    files = sorted([path for path in REFERENCE_ROOT.rglob("*") if path.is_file()]) if REFERENCE_ROOT.exists() else []
    records = [classify_reference_file(path, policy) for path in files]
    by_classification = Counter(record["classification"] for record in records)
    by_extension = Counter(record["extension"] for record in records)
    return {
        "root": relative(REFERENCE_ROOT) if REFERENCE_ROOT.exists() else "assets/slides/references",
        "file_count": len(records),
        "by_classification": dict(sorted(by_classification.items())),
        "by_extension": dict(sorted(by_extension.items())),
        "records": records,
    }


def palette_hints(slide: dict[str, Any]) -> list[str]:
    tags = {str(tag).lower() for tag in slide.get("style_tags", [])}
    library_id = str(slide.get("library_id", ""))
    if "finance" in tags or library_id == "template_library_02_v1":
        return ["navy", "orange_accent", "high_contrast"]
    if "portfolio" in tags or library_id == "template_library_03_v1":
        return ["white", "blue_accent", "neutral_gray"]
    if library_id == "template_library_01_v1":
        return ["white", "navy", "light_card_gray"]
    return ["neutral", "corporate", "low_chroma"]


def typography_hints(slide: dict[str, Any], dna: dict[str, Any]) -> list[str]:
    hints = ["clear_title_body_hierarchy"]
    density = str(slide.get("density") or dna.get("density") or "")
    if density == "dense":
        hints.append("small_body_text_requires_budgeting")
    if dna.get("visual_weight") == "visual_first":
        hints.append("large_title_with_short_supporting_copy")
    return hints


def chart_table_hints(slide: dict[str, Any], dna: dict[str, Any]) -> list[str]:
    capacity = dna.get("content_capacity", {}) if isinstance(dna.get("content_capacity"), dict) else {}
    hints: list[str] = []
    if slide.get("purpose") in {"chart", "market"} or capacity.get("chart_slots", 0):
        hints.append("evidence_chart_or_metric_page")
    if capacity.get("table_slots", 0):
        hints.append("editable_table_slot_available")
    if not hints:
        hints.append("no_primary_chart_table_signal")
    return hints


def image_treatment(slide: dict[str, Any], dna: dict[str, Any]) -> str:
    image_count = int(slide.get("image_count", 0) or 0)
    if image_count >= 8:
        return "icon_or_screenshot_heavy"
    if image_count >= 1 and dna.get("visual_weight") == "visual_first":
        return "hero_or_supporting_visual"
    if image_count >= 1:
        return "supporting_visual"
    return "text_or_shape_led"


def eligible_metadata(policy: dict[str, Any], reference_catalog: dict[str, Any], template_dna: dict[str, Any]) -> dict[str, Any]:
    min_score = float(policy.get("minimum_production_quality_score", 4.0))
    allowed_policies = set(policy.get("allowed_production_usage_policies", ["production_ready"]))
    dna_by_slide = template_dna.get("slides", {})
    records = []
    blocked = []
    for slide in reference_catalog.get("slides", []):
        slide_id = str(slide.get("slide_id"))
        dna = dna_by_slide.get(slide_id, {})
        usage_policy = slide.get("usage_policy")
        quality_score = float(slide.get("quality_score", 0) or 0)
        production_selectable = usage_policy in allowed_policies and quality_score >= min_score
        base = {
            "slide_id": slide_id,
            "template_key": slide.get("template_key"),
            "library_id": slide.get("library_id"),
            "purpose": slide.get("purpose"),
            "scope": slide.get("scope"),
            "quality_score": quality_score,
            "usage_policy": usage_policy,
            "production_selectable": production_selectable,
        }
        if not production_selectable:
            blocked.append({**base, "reason": "usage_policy_or_quality_score_not_eligible"})
            continue
        records.append(
            {
                **base,
                "lightweight_dna": {
                    "slide_archetype": slide.get("purpose"),
                    "layout_role": dna.get("structure") or slide.get("variant"),
                    "visual_density": slide.get("density") or dna.get("density"),
                    "palette_hints": palette_hints(slide),
                    "typography_hints": typography_hints(slide, dna),
                    "chart_table_style_hints": chart_table_hints(slide, dna),
                    "image_treatment": image_treatment(slide, dna),
                    "best_for": as_list(dna.get("best_for")),
                    "avoid_for": as_list(dna.get("avoid_for")),
                },
            }
        )
    by_purpose: dict[str, int] = defaultdict(int)
    by_scope: dict[str, int] = defaultdict(int)
    for record in records:
        by_purpose[str(record.get("purpose"))] += 1
        by_scope[str(record.get("scope"))] += 1
    return {
        "eligible_count": len(records),
        "blocked_count": len(blocked),
        "by_purpose": dict(sorted(by_purpose.items())),
        "by_scope": dict(sorted(by_scope.items())),
        "records": sorted(records, key=lambda item: (str(item.get("purpose")), -float(item.get("quality_score", 0)), str(item.get("slide_id")))),
        "blocked_sample": blocked[:25],
    }


def quality_gap_summary(policy: dict[str, Any]) -> dict[str, Any]:
    sources = [BASE_DIR / str(path) for path in policy.get("quality_gap_sources", [])]
    visual = read_json_optional(BASE_DIR / "outputs" / "reports" / "business_growth_review_visual_smoke.json")
    overflow = read_json_optional(BASE_DIR / "outputs" / "reports" / "business_growth_review_text_overflow.json")
    rationale = read_json_optional(BASE_DIR / "outputs" / "reports" / "business_growth_review_slide_selection_rationale.json")
    selected = rationale.get("slides", []) if isinstance(rationale.get("slides"), list) else []
    dense_selected = [
        {
            "slide_number": slide.get("slide_number"),
            "slide_id": slide.get("slide_id"),
            "density": (slide.get("candidate_templates") or [{}])[0].get("density"),
            "visual_weight": (slide.get("candidate_templates") or [{}])[0].get("visual_weight"),
        }
        for slide in selected
        if (slide.get("candidate_templates") or [{}])[0].get("density") == "dense"
    ]
    low_foreground = [
        {
            "slide": metric.get("slide"),
            "foreground_ratio": metric.get("foreground_ratio"),
            "stddev": metric.get("stddev"),
        }
        for metric in visual.get("image_metrics", [])
        if float(metric.get("foreground_ratio", 0) or 0) < 0.05
    ]
    gap_categories = []
    if dense_selected:
        gap_categories.append("layout_density")
    if low_foreground:
        gap_categories.append("visual_emptiness_or_low_foreground")
    if overflow.get("summary", {}).get("cutoff_events", 0):
        gap_categories.append("text_overflow")
    if not gap_categories:
        gap_categories.append("technical_gates_pass_but_human_visual_review_still_required")
    return {
        "source_paths": [str(path.relative_to(BASE_DIR)).replace("\\", "/") for path in sources if path.exists()],
        "slide_count": rationale.get("summary", {}).get("slides", visual.get("slide_count")),
        "selected_dense_slides": dense_selected,
        "low_foreground_slides": low_foreground,
        "text_cutoff_events": overflow.get("summary", {}).get("cutoff_events", 0),
        "gap_categories": gap_categories,
        "recommended_next_fix_path": [
            "prefer medium-density production templates for first beta demos",
            "add visual foreground/minimum-content checkpoint in B54 acceptance matrix",
            "treat gateway recommendation as downstream from reference eligibility, not a replacement for template cleanup",
        ],
    }


def build_report(policy: dict[str, Any]) -> dict[str, Any]:
    reference_catalog = load_json(REFERENCE_CATALOG_PATH)
    template_dna = load_json(TEMPLATE_DNA_PATH)
    inventory = inventory_reference_folder(policy)
    eligible = eligible_metadata(policy, reference_catalog, template_dna)
    quality_gap = quality_gap_summary(policy)
    errors = []
    if policy.get("raw_reference_assetization_allowed") is not False:
        errors.append("raw_reference_assetization_allowed must be false")
    if any(record.get("production_selectable") for record in inventory.get("records", [])):
        errors.append("raw reference folder file became production_selectable")
    if eligible.get("eligible_count", 0) <= 0:
        errors.append("no eligible lightweight DNA metadata records")
    return {
        "schema_version": "1.0",
        "policy_id": policy.get("policy_id"),
        "status": "valid" if not errors else "invalid",
        "summary": {
            "raw_reference_files": inventory.get("file_count", 0),
            "raw_reference_assetized": False,
            "eligible_dna_records": eligible.get("eligible_count", 0),
            "blocked_catalog_records": eligible.get("blocked_count", 0),
            "errors": len(errors),
        },
        "errors": errors,
        "policy_summary": {
            "raw_reference_direct_use_allowed": policy.get("raw_reference_direct_use_allowed"),
            "public_export_allowed_by_default": policy.get("public_export_allowed_by_default"),
            "minimum_production_quality_score": policy.get("minimum_production_quality_score"),
        },
        "reference_inventory": inventory,
        "eligible_lightweight_dna": eligible,
        "quality_gap_summary": quality_gap,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Reference Quality And Lightweight DNA",
        "",
        f"- Status: `{report['status']}`",
        f"- Raw reference files: `{summary['raw_reference_files']}`",
        f"- Raw reference assetized: `{summary['raw_reference_assetized']}`",
        f"- Eligible DNA records: `{summary['eligible_dna_records']}`",
        f"- Blocked catalog records: `{summary['blocked_catalog_records']}`",
        "",
        "## Guardrails",
        "",
        "- Raw reference files remain local analysis inputs only.",
        "- Production eligibility is based on finalized catalog metadata, not file presence under `assets/slides/references`.",
        "- B50 may consume only eligible lightweight DNA summaries.",
        "",
        "## Quality Gap Summary",
        "",
    ]
    gap = report["quality_gap_summary"]
    lines.append(f"- Gap categories: `{', '.join(gap.get('gap_categories', []))}`")
    lines.append(f"- Dense selected slides: `{len(gap.get('selected_dense_slides', []))}`")
    lines.append(f"- Low foreground slides: `{len(gap.get('low_foreground_slides', []))}`")
    lines.append("")
    lines.append("## Recommended Next Fix Path")
    lines.append("")
    for item in gap.get("recommended_next_fix_path", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reference quality and lightweight DNA report.")
    parser.add_argument("--policy", default=POLICY_PATH.as_posix())
    parser.add_argument("--report-json", default=DEFAULT_REPORT_JSON.as_posix())
    parser.add_argument("--report-md", default=DEFAULT_REPORT_MD.as_posix())
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main(argv: list[str] | None = None) -> int:
    args = parse_args()
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = (BASE_DIR / policy_path).resolve()
    report_json = Path(args.report_json)
    if not report_json.is_absolute():
        report_json = (BASE_DIR / report_json).resolve()
    report_md = Path(args.report_md)
    if not report_md.is_absolute():
        report_md = (BASE_DIR / report_md).resolve()

    policy = load_json(policy_path)
    report = build_report(policy)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_md.write_text(markdown_report(report), encoding="utf-8")
    if args.check and report["errors"]:
        for error in report["errors"]:
            print(f"ERROR: {error}")
        return 1
    print(
        "reference_quality_dna=valid "
        f"raw_files={report['summary']['raw_reference_files']} "
        f"eligible_dna={report['summary']['eligible_dna_records']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
