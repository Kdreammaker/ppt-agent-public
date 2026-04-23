from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.render_template_thumbnails import OUTPUT_DIR, build_thumbnail_index

REFERENCE_CATALOG_PATH = BASE_DIR / "config" / "reference_catalog.json"
TEMPLATE_DNA_PATH = BASE_DIR / "config" / "template_design_dna.json"
PATTERN_CATALOG_PATH = BASE_DIR / "config" / "template_pattern_catalog.json"
ASSISTANT_POLICY_PATH = BASE_DIR / "config" / "mode_policies" / "assistant_mode_policy.json"
DEFAULT_INTAKE_PATH = BASE_DIR / "data" / "intake" / "report_exec_briefing.json"
DEFAULT_REPORT_JSON = BASE_DIR / "outputs" / "reports" / "assistant_visual_recommendations.json"
DEFAULT_REPORT_MD = BASE_DIR / "outputs" / "reports" / "assistant_visual_recommendations.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def relative(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def intent_summary(intake: dict[str, Any]) -> dict[str, Any]:
    scope = (
        intake.get("brand_or_template_scope", {}).get("preferred_scope")
        or intake.get("deck_type")
        or "generic"
    )
    return {
        "name": intake.get("name"),
        "deck_type": intake.get("deck_type"),
        "preferred_scope": scope,
        "tone": as_list(intake.get("tone")),
        "content_density": intake.get("content_density"),
        "audience": intake.get("audience", {}).get("primary"),
        "primary_goal": intake.get("primary_goal"),
    }


def enriched_slides(reference_catalog: dict[str, Any], template_dna: dict[str, Any]) -> list[dict[str, Any]]:
    dna_by_slide = template_dna.get("slides", {})
    slides: list[dict[str, Any]] = []
    for slide in reference_catalog.get("slides", []):
        merged = dict(slide)
        merged.update(dna_by_slide.get(slide.get("slide_id"), {}))
        slides.append(merged)
    return slides


def direction_label(slide: dict[str, Any]) -> str:
    return " / ".join(
        [
            str(slide.get("scope") or "unknown"),
            str(slide.get("structure") or slide.get("purpose") or "unknown"),
            str(slide.get("density") or "unknown"),
            str(slide.get("visual_weight") or "unknown"),
        ]
    )


def thumbnail_path(slide: dict[str, Any], output_dir: Path = OUTPUT_DIR) -> Path:
    slide_no = int(slide.get("library_slide_no") or 1)
    return output_dir / str(slide["library_id"]) / f"slide_{slide_no:02d}.png"


def score_slide(slide: dict[str, Any], intent: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    preferred_scope = intent["preferred_scope"]
    slide_scope = slide.get("scope")
    if slide_scope == preferred_scope:
        score += 28
        reasons.append(f"scope match: {preferred_scope}")
    elif slide_scope == "generic":
        score += 12
        reasons.append("generic fallback")
    else:
        score += 5
        reasons.append(f"adjacent scope: {slide_scope}")

    tone_overlap = sorted(set(as_list(slide.get("tone"))) & set(as_list(intent.get("tone"))))
    if tone_overlap:
        score += 7 * len(tone_overlap)
        reasons.append("tone overlap: " + ", ".join(tone_overlap))

    density = str(slide.get("density") or "")
    intent_density = str(intent.get("content_density") or "")
    if density == intent_density:
        score += 8
        reasons.append(f"density match: {density}")
    elif density == "medium":
        score += 4
        reasons.append("medium-density compromise")

    quality_score = float(slide.get("quality_score") or 0)
    score += quality_score * 5
    reasons.append(f"quality_score={quality_score}")

    if slide.get("usage_policy") == "production_ready":
        score += 12
        reasons.append("production_ready")
    elif slide.get("usage_policy") == "structure_only":
        score -= 8
        reasons.append("structure_only caveat")
    elif slide.get("usage_policy") == "curate_before_use":
        score -= 30
        reasons.append("curate_before_use excluded")

    if slide.get("visual_weight") == "visual_first":
        score += 3
        reasons.append("visual-first option")

    return round(score, 4), reasons


def recommendation_options(
    *,
    intake: dict[str, Any],
    reference_catalog: dict[str, Any],
    template_dna: dict[str, Any],
    suggestion_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    intent = intent_summary(intake)
    candidates = []
    skipped_scope_matches: list[dict[str, Any]] = []
    for slide in enriched_slides(reference_catalog, template_dna):
        if slide.get("usage_policy") != "production_ready":
            if slide.get("scope") == intent["preferred_scope"]:
                skipped_scope_matches.append(
                    {
                        "slide_id": slide.get("slide_id"),
                        "template_key": slide.get("template_key"),
                        "usage_policy": slide.get("usage_policy"),
                        "reason": "not production_ready",
                    }
                )
            continue
        if not slide.get("slide_id", "").startswith("template_library_"):
            continue
        score, reasons = score_slide(slide, intent)
        candidates.append((score, reasons, slide))
    candidates.sort(key=lambda item: (-item[0], str(item[2].get("default_rank", 9999)), str(item[2].get("slide_id"))))

    selected: list[dict[str, Any]] = []
    seen_directions: set[str] = set()
    seen_libraries: set[str] = set()

    def add_candidate(score: float, reasons: list[str], slide: dict[str, Any]) -> bool:
        label = direction_label(slide)
        if label in seen_directions:
            return False
        selected.append(build_option(slide, score, reasons, label))
        seen_directions.add(label)
        seen_libraries.add(str(slide.get("library_id")))
        return True

    for score, reasons, slide in candidates:
        if add_candidate(score, reasons, slide):
            break

    for score, reasons, slide in candidates:
        if len(selected) >= suggestion_count:
            break
        if str(slide.get("library_id")) in seen_libraries:
            continue
        add_candidate(score, reasons, slide)

    for score, reasons, slide in candidates:
        if len(selected) >= suggestion_count:
            break
        add_candidate(score, reasons, slide)

    rejected = [
        {
            "slide_id": slide.get("slide_id"),
            "template_key": slide.get("template_key"),
            "score": score,
            "direction": direction_label(slide),
            "reason": "near-duplicate direction" if direction_label(slide) in seen_directions else "ranked below selected options",
        }
        for score, _reasons, slide in candidates[: max(12, suggestion_count * 4)]
        if slide.get("slide_id") not in {option["slide_id"] for option in selected}
    ]
    if skipped_scope_matches:
        note = (
            f"Exact `{intent['preferred_scope']}` scope templates exist but are not production_ready; "
            "recommendations use production_ready adjacent scopes instead."
        )
        for option in selected:
            option["scope_gap_notes"] = [note]
    return selected, rejected


def build_option(slide: dict[str, Any], score: float, reasons: list[str], label: str) -> dict[str, Any]:
    thumb = thumbnail_path(slide)
    return {
        "slide_id": slide.get("slide_id"),
        "template_key": slide.get("template_key"),
        "library_id": slide.get("library_id"),
        "scope": slide.get("scope"),
        "purpose": slide.get("purpose"),
        "variant": slide.get("variant"),
        "direction": label,
        "score": score,
        "reasons": reasons,
        "usage_policy": slide.get("usage_policy"),
        "quality_score": slide.get("quality_score"),
        "density": slide.get("density"),
        "structure": slide.get("structure"),
        "visual_weight": slide.get("visual_weight"),
        "tone": as_list(slide.get("tone")),
        "thumbnail_path": relative(thumb),
        "thumbnail_exists": thumb.exists(),
        "source_metadata": {
            "reference_catalog": "config/reference_catalog.json",
            "template_design_dna": "config/template_design_dna.json",
        },
    }


def build_report(intake_path: Path, report_json: Path, report_md: Path, check: bool) -> dict[str, Any]:
    build_thumbnail_index(check=True)
    intake = load_json(intake_path)
    reference_catalog = load_json(REFERENCE_CATALOG_PATH)
    template_dna = load_json(TEMPLATE_DNA_PATH)
    pattern_catalog = load_json(PATTERN_CATALOG_PATH)
    assistant_policy = load_json(ASSISTANT_POLICY_PATH)
    suggestion_count = int(assistant_policy.get("template_suggestion_count", 3))
    selected, rejected = recommendation_options(
        intake=intake,
        reference_catalog=reference_catalog,
        template_dna=template_dna,
        suggestion_count=suggestion_count,
    )
    distinct_directions = sorted({option["direction"] for option in selected})
    report = {
        "schema_version": "1.0",
        "mode": "assistant",
        "intake_path": relative(intake_path),
        "intent": intent_summary(intake),
        "artifact_status": {
            "reference_catalog_slides": len(reference_catalog.get("slides", [])),
            "template_design_dna_slides": len(template_dna.get("slides", {})),
            "template_pattern_count": len(pattern_catalog.get("patterns", [])),
            "assistant_policy_path": relative(ASSISTANT_POLICY_PATH),
            "thumbnail_index_path": "outputs/previews/template_index/INDEX.md",
        },
        "recommendations": selected,
        "rejected_sample": rejected,
        "summary": {
            "requested_options": suggestion_count,
            "recommendations": len(selected),
            "distinct_directions": len(distinct_directions),
            "raw_or_candidate_sources_exposed": False,
        },
    }

    if check:
        errors = validate_report(report)
        if errors:
            raise AssertionError("; ".join(errors))

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report_md.write_text(markdown_report(report), encoding="utf-8")
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    recommendations = report.get("recommendations", [])
    if len(recommendations) < 3:
        errors.append(f"expected at least 3 recommendations, got {len(recommendations)}")
    directions = [option.get("direction") for option in recommendations]
    if len(set(directions)) != len(directions):
        errors.append("recommendations are not directionally distinct")
    for option in recommendations:
        if not str(option.get("slide_id", "")).startswith("template_library_"):
            errors.append(f"non-production template id exposed: {option.get('slide_id')}")
        if option.get("usage_policy") == "curate_before_use":
            errors.append(f"curate_before_use option exposed: {option.get('slide_id')}")
        if option.get("usage_policy") != "production_ready":
            errors.append(f"non-production-ready option exposed: {option.get('slide_id')}")
        if not option.get("thumbnail_exists"):
            errors.append(f"missing thumbnail: {option.get('thumbnail_path')}")
    if report.get("summary", {}).get("raw_or_candidate_sources_exposed"):
        errors.append("raw/candidate sources exposed")
    return errors


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Assistant Visual Recommendations",
        "",
        f"- Intake: `{report['intake_path']}`",
        f"- Mode: `{report['mode']}`",
        f"- Intent: {report['intent'].get('name')} ({report['intent'].get('deck_type')})",
        f"- Preferred scope: `{report['intent'].get('preferred_scope')}`",
        f"- Pattern count: `{report['artifact_status'].get('template_pattern_count')}`",
        "",
        "## Options",
        "",
    ]
    for index, option in enumerate(report.get("recommendations", []), start=1):
        reasons = "; ".join(option.get("reasons", []))
        lines.extend(
            [
                f"### Option {index}: {option['direction']}",
                "",
                f"- Slide: `{option['slide_id']}`",
                f"- Template key: `{option['template_key']}`",
                f"- Purpose/variant: `{option['purpose']}` / `{option['variant']}`",
                f"- Usage: `{option['usage_policy']}`",
                f"- Thumbnail: `{option['thumbnail_path']}`",
                f"- Score: `{option['score']}`",
                f"- Rationale: {reasons}",
                f"- Caveat: {'; '.join(option.get('scope_gap_notes', ['none']))}",
                "",
            ]
        )
    lines.extend(
        [
            "## Guardrails",
            "",
            "- Recommendations cite production template library IDs and finalized JSON metadata only.",
            "- Raw/generated/candidate references are not exposed as selectable options.",
            "- Non-`production_ready` templates are excluded from unattended recommendations.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an Assistant Mode visual template recommendation artifact.")
    parser.add_argument("--intake", default=str(DEFAULT_INTAKE_PATH.relative_to(BASE_DIR)))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON.relative_to(BASE_DIR)))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD.relative_to(BASE_DIR)))
    parser.add_argument("--sample", action="store_true", help="Use the default sample intake.")
    parser.add_argument("--check", action="store_true", help="Assert recommendation completeness and guardrails.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    intake_path = DEFAULT_INTAKE_PATH if args.sample else (BASE_DIR / args.intake).resolve()
    report = build_report(
        intake_path=intake_path,
        report_json=(BASE_DIR / args.report_json).resolve(),
        report_md=(BASE_DIR / args.report_md).resolve(),
        check=args.check,
    )
    print((BASE_DIR / args.report_json).resolve())
    print(f"assistant_recommendations={report['summary']['recommendations']}")
    print(f"assistant_distinct_directions={report['summary']['distinct_directions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
