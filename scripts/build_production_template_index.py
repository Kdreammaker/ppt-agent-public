from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BASE_DIR / "config" / "reference_catalog.json"
MANIFEST_PATH = BASE_DIR / "config" / "production_template_manifest.json"
GUIDE_PATH = BASE_DIR / "docs" / "PRODUCTION_TEMPLATE_GUIDE.md"

CORE_PURPOSES = [
    "cover",
    "toc",
    "summary",
    "issue",
    "analysis",
    "chart",
    "process",
    "strategy",
    "timeline",
    "market",
    "team",
    "closing",
]


def ranked(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        slides,
        key=lambda item: (
            0 if item.get("usage_policy") == "production_ready" else 1,
            -float(item.get("quality_score", 0)),
            item.get("default_rank", 999),
            item["slide_id"],
        ),
    )


def slim(slide: dict[str, Any]) -> dict[str, Any]:
    return {
        "slide_id": slide["slide_id"],
        "library_id": slide["library_id"],
        "template_key": slide["template_key"],
        "purpose": slide["purpose"],
        "variant": slide["variant"],
        "scope": slide["scope"],
        "style_tags": slide.get("style_tags", []),
        "density": slide.get("density"),
        "quality_score": slide.get("quality_score"),
        "design_tier": slide.get("design_tier"),
        "usage_policy": slide.get("usage_policy"),
        "library_path": slide["library_path"],
        "library_slide_no": slide["library_slide_no"],
        "design_notes": slide.get("design_notes", ""),
    }


def selector_for(slide: dict[str, Any]) -> dict[str, Any]:
    return {
        "purpose": slide["purpose"],
        "scope": slide["scope"],
        "preferred_variant": slide["variant"],
        "source_library": slide["library_id"],
        "min_quality_score": max(4.0, float(slide.get("quality_score", 4.0)) - 0.1),
        "usage_policies": ["production_ready"],
    }


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    by_purpose: dict[str, list[dict[str, Any]]] = defaultdict(list)
    production_ready = [
        slide
        for slide in catalog["slides"]
        if slide.get("usage_policy") == "production_ready" and float(slide.get("quality_score", 0)) >= 4.0
    ]
    for slide in catalog["slides"]:
        by_purpose[slide["purpose"]].append(slide)

    purpose_manifest: dict[str, Any] = {}
    for purpose in CORE_PURPOSES:
        candidates = ranked(by_purpose.get(purpose, []))
        ready = [slide for slide in candidates if slide.get("usage_policy") == "production_ready"]
        purpose_manifest[purpose] = {
            "coverage": "production_ready" if ready else "gap",
            "recommended": [slim(slide) for slide in ready[:4]],
            "fallback": [slim(slide) for slide in candidates[:3] if slide not in ready],
            "recommended_selector": selector_for(ready[0]) if ready else None,
        }

    manifest = {
        "version": "0.1",
        "workspace": BASE_DIR.as_posix(),
        "production_ready_count": len(production_ready),
        "purpose_manifest": purpose_manifest,
        "recommended_sets": {
            "data_story": [
                "template_library_02_v1.problem_story_v1",
                "template_library_02_v1.proof_metrics_v1",
                "template_library_02_v1.signal_speed_v1",
                "template_library_02_v1.roi_threepillars_v1",
                "template_library_02_v1.finance_closing_v1",
            ],
            "service_story": [
                "template_library_01_v1.channel_cover_v1",
                "template_library_01_v1.service_intro_cards_v1",
                "template_library_01_v1.data_method_v1",
                "template_library_01_v1.sales_strategy_steps_v1",
                "template_library_01_v1.discussion_closing_v1",
            ],
            "case_study": [
                "template_library_03_v1.portfolio_cover_v1",
                "template_library_03_v1.project_case_v1",
                "template_library_03_v1.project_case_v2",
                "template_library_03_v1.improvement_case_v1",
                "template_library_03_v1.portfolio_closing_v1",
            ],
        },
        "known_gaps": [
            purpose
            for purpose, info in purpose_manifest.items()
            if info["coverage"] == "gap"
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Production Template Guide",
        "",
        "이 문서는 `reference_catalog.json`의 품질 메타데이터를 기준으로 실제 deck 제작에 우선 사용할 슬라이드를 정리합니다.",
        "",
        f"- Production-ready slides: `{len(production_ready)}`",
        f"- Known gaps: `{', '.join(manifest['known_gaps']) or 'none'}`",
        "",
        "## 목적별 추천 후보",
        "",
    ]
    for purpose in CORE_PURPOSES:
        info = purpose_manifest[purpose]
        lines.append(f"### {purpose}")
        lines.append("")
        lines.append(f"- Coverage: `{info['coverage']}`")
        if info["recommended"]:
            for slide in info["recommended"]:
                lines.append(
                    f"- `{slide['slide_id']}` | variant=`{slide['variant']}` | score=`{slide['quality_score']}` | policy=`{slide['usage_policy']}`"
                )
        elif info["fallback"]:
            lines.append("- Production-ready 후보가 없어 fallback 후보만 있습니다.")
            for slide in info["fallback"]:
                lines.append(
                    f"- `{slide['slide_id']}` | variant=`{slide['variant']}` | score=`{slide['quality_score']}` | policy=`{slide['usage_policy']}`"
                )
        else:
            lines.append("- 후보가 없습니다.")
        lines.append("")

    lines.extend(
        [
            "## 사용 권장",
            "",
            "- 데이터/리스크/시장 논리는 `data_story` 세트를 우선 사용합니다.",
            "- 서비스 소개/프로세스/영업 제안은 `service_story` 세트를 우선 사용합니다.",
            "- 사례/성과/스크린샷 중심 내용은 `case_study` 세트를 우선 사용합니다.",
            "- `toc`, `timeline`, `market`은 아직 production-ready gap이므로 custom layout builder 또는 추가 reference 보강이 필요합니다.",
        ]
    )
    GUIDE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(MANIFEST_PATH)
    print(GUIDE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
