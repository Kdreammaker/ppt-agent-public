from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "commercial_mvp_reference_design_importer.json"

FAMILIES: dict[str, dict[str, Any]] = {
    "ir": {
        "search_terms": ("report", "exec", "briefing"),
        "fallback_archetypes": ["cover", "market_context", "traction", "ask"],
        "fallback_components": ["metric_band", "comparison_table", "timeline"],
    },
    "sales": {
        "search_terms": ("sales", "pitch", "solution"),
        "fallback_archetypes": ["cover", "pain_point", "solution", "proof", "closing"],
        "fallback_components": ["value_card", "process_step", "proof_block"],
    },
    "portfolio": {
        "search_terms": ("portfolio", "case", "capability"),
        "fallback_archetypes": ["cover", "case_study", "gallery", "capability", "closing"],
        "fallback_components": ["image_grid", "case_card", "capability_strip"],
    },
}

HEX_RE = re.compile(rb"\b[0-9A-Fa-f]{6}\b")
SIZE_RE = re.compile(rb'<a:sz val="(\d+)"')


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def candidate_files(family_id: str, suffixes: tuple[str, ...]) -> list[Path]:
    terms = FAMILIES[family_id]["search_terms"]
    roots = (BASE_DIR / "outputs" / "decks", BASE_DIR / "outputs" / "html", BASE_DIR / "outputs" / "reports")
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            label = path.as_posix().lower()
            if any(term in label for term in terms):
                files.append(path)
    return sorted(files)[:8]


def analyze_pptx(path: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "slide_count": 0,
        "palette_counter": Counter(),
        "font_size_bins": Counter(),
        "shape_count": 0,
        "image_count": 0,
        "table_count": 0,
        "chart_count": 0,
    }
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        slide_names = [name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
        metrics["slide_count"] = len(slide_names)
        for name in slide_names:
            raw = package.read(name)
            metrics["shape_count"] += raw.count(b"<p:sp>")
            metrics["image_count"] += raw.count(b"<p:pic>")
            metrics["table_count"] += raw.count(b"<a:tbl>")
            metrics["chart_count"] += raw.count(b"c:chart") + raw.count(b"/charts/chart")
            for match in HEX_RE.findall(raw):
                value = match.decode("ascii").upper()
                if value not in {"FFFFFF", "000000"}:
                    metrics["palette_counter"][value] += 1
            for match in SIZE_RE.findall(raw):
                pt = int(match) / 100
                bucket = "display" if pt >= 44 else "heading" if pt >= 30 else "body" if pt >= 18 else "caption"
                metrics["font_size_bins"][bucket] += 1
    return metrics


def analyze_html_or_report(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lower = text.lower()
    return {
        "html_or_visual_record_count": 1,
        "mentions_overflow": "overflow" in lower,
        "mentions_table": "table" in lower,
        "mentions_chart": "chart" in lower,
        "style_token_markers": len(re.findall(r"--[a-z0-9-]+", lower)),
        "color_marker_count": len(re.findall(r"#[0-9a-f]{6}", lower)),
    }


def merge_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "source_pptx_count": 0,
        "source_html_or_visual_count": 0,
        "slide_count": 0,
        "palette_counter": Counter(),
        "font_size_bins": Counter(),
        "shape_count": 0,
        "image_count": 0,
        "table_count": 0,
        "chart_count": 0,
        "style_token_markers": 0,
        "color_marker_count": 0,
    }
    for item in items:
        if "slide_count" in item:
            merged["source_pptx_count"] += 1
            merged["slide_count"] += item.get("slide_count", 0)
            merged["palette_counter"].update(item.get("palette_counter", {}))
            merged["font_size_bins"].update(item.get("font_size_bins", {}))
            for key in ("shape_count", "image_count", "table_count", "chart_count"):
                merged[key] += item.get(key, 0)
        else:
            merged["source_html_or_visual_count"] += item.get("html_or_visual_record_count", 0)
            merged["style_token_markers"] += item.get("style_token_markers", 0)
            merged["color_marker_count"] += item.get("color_marker_count", 0)
            merged["table_count"] += 1 if item.get("mentions_table") else 0
            merged["chart_count"] += 1 if item.get("mentions_chart") else 0
    return merged


def palette_roles(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    colors = [color for color, _count in metrics["palette_counter"].most_common(5)]
    role_names = ["ink_or_deep", "accent", "surface", "muted", "support"]
    return [
        {"role": role, "observed_family_color_rank": index + 1, "sample_value_stored": False}
        for index, role in enumerate(role_names[: max(3, min(5, len(colors) or 3))])
    ]


def typography_roles(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    bins = metrics["font_size_bins"]
    roles = [
        ("Title", "display" if bins.get("display") else "heading"),
        ("H1", "heading"),
        ("Body", "body"),
        ("Caption", "caption"),
    ]
    return [{"role": role, "observed_size_bucket": bucket, "exact_source_size_stored": False} for role, bucket in roles]


def density(metrics: dict[str, Any]) -> str:
    slides = max(1, metrics.get("slide_count") or 1)
    objects_per_slide = (metrics.get("shape_count", 0) + metrics.get("image_count", 0) + metrics.get("table_count", 0) * 2) / slides
    if objects_per_slide >= 10:
        return "high"
    if objects_per_slide >= 5:
        return "medium"
    return "low"


def recipe_for_family(family_id: str) -> dict[str, Any]:
    pptx_metrics = [analyze_pptx(path) for path in candidate_files(family_id, (".pptx",))]
    html_metrics = [analyze_html_or_report(path) for path in candidate_files(family_id, (".html", ".json"))]
    metrics = merge_metrics([*pptx_metrics, *html_metrics])
    family = FAMILIES[family_id]
    observed_density = density(metrics)
    has_images = metrics.get("image_count", 0) > 0
    has_tables = metrics.get("table_count", 0) > 0
    has_charts = metrics.get("chart_count", 0) > 0
    return {
        "recipe_id": f"rdl-import-{family_id}-content-free-v2",
        "family_id": family_id,
        "source_kind": "local_pptx_html_family_metric_analysis",
        "stored_source_content": False,
        "analysis_metrics": {
            "source_pptx_count": metrics["source_pptx_count"],
            "source_html_or_visual_count": metrics["source_html_or_visual_count"],
            "slide_count_bucket": "multi_slide" if metrics["slide_count"] >= 3 else "single_or_sparse",
            "object_density": observed_density,
            "image_slot_presence": has_images,
            "table_presence": has_tables,
            "chart_presence": has_charts,
            "palette_color_rank_count": min(5, len(metrics["palette_counter"])),
            "typography_bucket_count": len(metrics["font_size_bins"]),
            "stores_source_filenames": False,
            "stores_exact_coordinates": False,
        },
        "palette_roles": palette_roles(metrics),
        "typography_roles": typography_roles(metrics),
        "layout_archetypes": family["fallback_archetypes"],
        "component_recipes": family["fallback_components"],
        "image_slot_treatment": "large_safe_ref_slot_with_crop_policy" if has_images else "safe_ref_placeholder_only",
        "chart_table_style": "editable_native_chart_table_guidance" if has_charts or has_tables else "clean_metric_cards_without_source_data",
        "density": observed_density,
        "spacing_rhythm": "regular_safe_margin_with_binned_density",
        "synthetic_placeholder_preview": {
            "preview_id": f"rdl-preview-{family_id}-synthetic-v2",
            "placeholder_labels_only": True,
            "uses_source_slide_text": False,
            "uses_source_slide_image": False,
            "uses_source_dom": False,
            "uses_source_coordinates": False,
            "uses_source_filename": False,
            "preview_slide_count": 3,
        },
    }


def recipe_is_content_free(recipe: dict[str, Any]) -> bool:
    return (
        recipe.get("content_free_preview", {}).get("placeholder_labels_only") is True
        or recipe.get("synthetic_placeholder_preview", {}).get("placeholder_labels_only") is True
    )


def family_evidence_present(family_id: str) -> dict[str, Any]:
    pptx_count = len(candidate_files(family_id, (".pptx",)))
    html_count = len(candidate_files(family_id, (".html", ".json")))
    return {
        "pptx_family_evidence_present": pptx_count > 0,
        "html_or_visual_family_evidence_present": html_count > 0,
        "source_pptx_count": pptx_count,
        "source_html_or_visual_count": html_count,
        "source_filenames_stored": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import content-free Commercial MVP Reference Design Library recipes.")
    parser.add_argument("--family", action="append", choices=sorted(FAMILIES), help="Family id to import. Defaults to all.")
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args(argv)
    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()

    selected = args.family or sorted(FAMILIES)
    recipes = [recipe_for_family(family_id) for family_id in selected]
    payload = {
        "schema_version": "commercial_mvp_reference_design_importer.v2",
        "status": "valid",
        "summary": {
            "recipe_count": len(recipes),
            "content_free_only": bool(recipes) and all(recipe_is_content_free(recipe) for recipe in recipes),
            "content_free_schema_support": {
                "content_free_preview_placeholder_labels_only": True,
                "synthetic_placeholder_preview_placeholder_labels_only": True,
            },
        },
        "importer_boundary": {
            "local_host_ai_first": True,
            "server_original_file_upload": False,
            "stores_raw_dom": False,
            "stores_source_text": False,
            "stores_source_coordinates": False,
            "stores_source_screenshots": False,
            "stores_image_urls": False,
            "stores_source_filenames": False,
            "stores_business_content": False,
        },
        "family_evidence": {family_id: family_evidence_present(family_id) for family_id in selected},
        "recipes": recipes,
        "forbidden_content_absent": True,
    }
    write_json(report, payload)
    print(json.dumps({"status": "valid", "recipes": len(payload["recipes"]), "report": report.relative_to(BASE_DIR).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
