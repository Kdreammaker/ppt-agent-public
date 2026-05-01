from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.typography_diagnostics import diagnose_text_box, diagnostics_summary
from validate_typography_diagnostics import assert_diagnostic_shape, assert_summary_shape, validate_report_tree


FIXTURE_CASES = (
    {
        "case_id": "bad_manual_hangul_break",
        "description": "Explicit manual line break splits the Korean word 고객데이터분석.",
        "text": "고객데이\n터분석 지표를 검토합니다",
        "role": "body",
        "box_width": 1.6,
        "box_height": 0.7,
        "max_lines": 3,
        "expected_risk": True,
        "expected_reason": "explicit_line_break_splits_hangul_sequence",
    },
    {
        "case_id": "safe_eojeol_wrapping_control",
        "description": "Korean sentence with spaces should wrap at 어절 boundaries without broken-token risk.",
        "text": "고객 데이터 분석과 운영 개선을 어절 단위로 안전하게 나누는 설명입니다",
        "role": "body",
        "box_width": 1.2,
        "box_height": 1.2,
        "max_lines": 5,
        "expected_risk": False,
        "expected_safe_wrap": True,
    },
    {
        "case_id": "bad_long_korean_token",
        "description": "A long Korean identifier-like token exceeds the estimated line capacity.",
        "text": "초개인화고객세분화자동화분석플랫폼",
        "role": "body",
        "box_width": 0.7,
        "box_height": 0.7,
        "max_lines": 3,
        "expected_risk": True,
        "expected_reason": "single_korean_token_exceeds_estimated_line_capacity",
    },
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_diagnostic(case: dict[str, Any], *, artifact_side: str) -> dict[str, Any]:
    diagnostic = diagnose_text_box(
        text=case["text"],
        role=case["role"],
        locale="ko-KR",
        font_size=12.5,
        box_width=case["box_width"],
        box_height=case["box_height"],
        max_lines=case["max_lines"],
        slot_name=f"{artifact_side}_{case['case_id']}",
    )
    diagnostic.update(
        {
            "fixture_case_id": case["case_id"],
            "fixture_description": case["description"],
            "fixture_artifact_side": artifact_side,
        }
    )
    assert_diagnostic_shape(diagnostic, source=f"{artifact_side}:{case['case_id']}")
    assert_true(
        diagnostic["korean_broken_token_risk"] is case["expected_risk"],
        f"{artifact_side}:{case['case_id']} expected korean_broken_token_risk={case['expected_risk']}",
    )
    expected_reason = case.get("expected_reason")
    if expected_reason:
        assert_true(
            expected_reason in diagnostic.get("korean_broken_token_reasons", []),
            f"{artifact_side}:{case['case_id']} missing reason {expected_reason}",
        )
    if case.get("expected_safe_wrap"):
        assert_true(diagnostic.get("safe_wrap_applied") is True, f"{artifact_side}:{case['case_id']} should safe-wrap")
    return diagnostic


def fixture_diagnostics(*, artifact_side: str) -> list[dict[str, Any]]:
    return [build_diagnostic(case, artifact_side=artifact_side) for case in FIXTURE_CASES]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_fixture_reports(output_root: Path) -> dict[str, str]:
    pptx_items = fixture_diagnostics(artifact_side="pptx")
    html_items = fixture_diagnostics(artifact_side="html_report")
    pptx_summary = diagnostics_summary(pptx_items)
    html_summary = diagnostics_summary(html_items)
    assert_summary_shape(pptx_summary, source="pptx:summary")
    assert_summary_shape(html_summary, source="html_report:summary")
    assert_true(pptx_summary["korean_broken_token_risk_count"] == 2, "pptx fixture should report two broken-token risks")
    assert_true(html_summary["korean_broken_token_risk_count"] == 2, "HTML/report fixture should report two broken-token risks")

    final_qa_path = output_root / "pptx_side" / "workspace" / "outputs" / "projects" / "korean-broken-token-fixture" / "final-qa.json"
    deck_slot_map_path = output_root / "html_report_side" / "workspace" / "outputs" / "reports" / "deck_slot_map.json"
    write_json(
        final_qa_path,
        {
            "status": "warning",
            "fixture": "korean_broken_token",
            "typography_diagnostics": {
                "status": "warning",
                "blocking": False,
                "summary": pptx_summary,
                "items": pptx_items,
            },
        },
    )
    write_json(
        deck_slot_map_path,
        {
            "fixture": "korean_broken_token",
            "summary": {"typography_diagnostics": html_summary},
            "slots": [
                {
                    "slot_kind": "text",
                    "slot_name": item["fixture_case_id"],
                    "artifact_side": item["fixture_artifact_side"],
                    "text": next(case["text"] for case in FIXTURE_CASES if case["case_id"] == item["fixture_case_id"]),
                    "typography_diagnostics": item,
                }
                for item in html_items
            ],
        },
    )
    return {"final_qa": final_qa_path.as_posix(), "deck_slot_map": deck_slot_map_path.as_posix()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate Korean broken-token typography fixture evidence.")
    parser.add_argument("--output-root", required=True, help="Evidence root for generated fixture reports.")
    args = parser.parse_args(argv)

    output_root = Path(args.output_root).resolve()
    written = write_fixture_reports(output_root)
    report_validation = validate_report_tree(output_root)
    aggregate = report_validation["aggregate_summary"]
    assert_true(
        aggregate["korean_broken_token_risk_count"] == 4,
        f"fixture aggregate should report four duplicated artifact-side risks, got {aggregate['korean_broken_token_risk_count']}",
    )
    result = {
        "status": "pass",
        "output_root": str(output_root),
        "written": written,
        "decision": "evidence_only_policy_still_deferred",
        "report_validation": report_validation,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
