from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.typography_diagnostics import annotate_title_body_ratio, diagnose_text_box, diagnostics_summary


REQUIRED_DIAGNOSTIC_FIELDS = {
    "role",
    "locale",
    "font_size",
    "min_pt",
    "default_pt",
    "max_pt",
    "weighted_cjk_latin_units",
    "estimated_lines",
    "target_lines",
    "max_lines",
    "box_width",
    "box_height",
    "overflow_risk",
    "korean_broken_token_risk",
    "title_body_ratio_risk",
    "render_font_size",
    "fit_status",
    "target_units",
    "max_units",
    "line_capacity_units",
    "safe_wrapped_text",
    "safe_wrapped_lines",
    "safe_wrap_applied",
    "emergency_break_used",
    "compression_request",
}
SUMMARY_FIELDS = (
    "items",
    "overflow_risk_count",
    "korean_broken_token_risk_count",
    "title_body_ratio_risk_count",
    "degraded_output_exception_count",
    "compression_request_count",
    "safe_wrap_count",
    "font_size_adjustment_count",
)
REQUIRED_SUMMARY_FIELDS = set(SUMMARY_FIELDS)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert_true(isinstance(data, dict), f"{path} must contain a JSON object")
    return data


def assert_diagnostic_shape(item: dict[str, Any], *, source: str) -> None:
    missing = sorted(REQUIRED_DIAGNOSTIC_FIELDS - set(item))
    assert_true(not missing, f"{source} missing typography diagnostic fields: {missing}")
    assert_true(item["min_pt"] <= item["recommended_font_size"] <= item["max_pt"], f"{source} recommended font outside bounds")
    if item["font_size"] < item["min_pt"]:
        assert_true(item["degraded_output_exception"] is True, f"{source} below-min font was not flagged as degraded")
    assert_true(item["min_pt"] <= item["render_font_size"] <= item["max_pt"], f"{source} render font outside bounds")
    request = item.get("compression_request")
    if request is not None:
        assert_true(isinstance(request, dict), f"{source} compression_request must be an object")
        for key in ("slot_id", "role", "locale", "current_units", "target_units", "target_lines", "max_lines", "priority"):
            assert_true(key in request, f"{source} compression_request missing {key}")


def assert_summary_shape(summary: dict[str, Any], *, source: str) -> None:
    missing = sorted(REQUIRED_SUMMARY_FIELDS - set(summary))
    assert_true(not missing, f"{source} missing typography summary fields: {missing}")
    for key in SUMMARY_FIELDS:
        assert_true(isinstance(summary.get(key), int), f"{source} summary field {key} must be an integer")


def combine_summaries(summaries: list[dict[str, Any]]) -> dict[str, int]:
    aggregate = {key: 0 for key in SUMMARY_FIELDS}
    for summary in summaries:
        for key in SUMMARY_FIELDS:
            aggregate[key] += int(summary.get(key, 0))
    return aggregate


def validate_helper_cases() -> dict[str, Any]:
    title = diagnose_text_box(
        text="한국의 5월 제철 음식",
        role="title",
        locale="ko-KR",
        font_size=27,
        box_width=4.2,
        box_height=0.8,
    )
    body = diagnose_text_box(
        text="두릅\n무침",
        role="body",
        locale="ko-KR",
        font_size=10,
        box_width=0.42,
        box_height=0.4,
    )
    wrapped = diagnose_text_box(
        text="두릅 무침 제철 향과 식감을 한 줄씩 안전하게 나누는 설명",
        role="body",
        locale="ko-KR",
        font_size=12.5,
        box_width=1.2,
        box_height=0.65,
        max_lines=2,
    )
    compressed = diagnose_text_box(
        text="장어의 제철 이유와 맛과 추천 조리법을 아주 길게 설명하여 슬롯 예산을 넘는 본문입니다",
        role="body",
        locale="ko-KR",
        font_size=12.5,
        box_width=0.9,
        box_height=0.38,
        max_lines=1,
        slot_name="body_fixture",
    )
    annotate_title_body_ratio([title, body, wrapped, compressed])
    for name, item in {"title": title, "body": body, "wrapped": wrapped, "compressed": compressed}.items():
        assert_diagnostic_shape(item, source=f"helper:{name}")
    assert_true(body["degraded_output_exception"], "helper body below min_pt should be flagged")
    assert_true(body["korean_broken_token_risk"], "helper Korean broken-token fixture should be flagged")
    assert_true(wrapped["safe_wrap_applied"], "helper Korean wrapping fixture should emit safe line breaks")
    assert_true(compressed["compression_request"] is not None, "helper overflow fixture should emit compression handoff metadata")
    summary = diagnostics_summary([title, body, wrapped, compressed])
    assert_summary_shape(summary, source="helper:summary")
    return {"status": "pass", "items": 4, "summary": summary}


def validate_final_qa(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    diagnostics = payload.get("typography_diagnostics")
    assert_true(isinstance(diagnostics, dict), f"{path} missing typography_diagnostics")
    assert_true(diagnostics.get("blocking") is False, f"{path} typography diagnostics must be non-blocking")
    items = diagnostics.get("items")
    assert_true(isinstance(items, list) and items, f"{path} typography diagnostics has no items")
    summary = diagnostics.get("summary")
    assert_true(isinstance(summary, dict), f"{path} missing typography diagnostics summary")
    assert_summary_shape(summary, source=f"{path}:summary")
    for index, item in enumerate(items[:5]):
        assert_true(isinstance(item, dict), f"{path} diagnostic item {index} is not an object")
        assert_diagnostic_shape(item, source=f"{path}:items[{index}]")
    return {"path": path.as_posix(), "items": len(items), "status": diagnostics.get("status"), "summary": summary}


def validate_deck_slot_map(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload.get("summary", {}).get("typography_diagnostics")
    assert_true(isinstance(summary, dict), f"{path} missing typography diagnostics summary")
    assert_summary_shape(summary, source=f"{path}:summary")
    text_slots = [
        slot
        for slot in payload.get("slots", [])
        if isinstance(slot, dict) and slot.get("slot_kind") == "text"
    ]
    assert_true(text_slots, f"{path} has no text slots to validate")
    checked = 0
    for slot in text_slots:
        diagnostic = slot.get("typography_diagnostics")
        assert_true(isinstance(diagnostic, dict), f"{path} text slot missing typography diagnostics")
        assert_diagnostic_shape(diagnostic, source=f"{path}:{slot.get('slot_name')}")
        checked += 1
    return {"path": path.as_posix(), "text_slots": checked, "summary": summary}


def validate_report_tree(root: Path) -> dict[str, Any]:
    assert_true(root.exists(), f"report root does not exist: {root}")
    final_qa_paths = sorted(root.rglob("final-qa.json"))
    slot_map_paths = sorted(root.rglob("deck_slot_map.json"))
    assert_true(final_qa_paths or slot_map_paths, f"{root} has no final-qa.json or deck_slot_map.json reports")
    final_qa_reports = [validate_final_qa(path) for path in final_qa_paths]
    slot_maps = [validate_deck_slot_map(path) for path in slot_map_paths]
    summaries = [item["summary"] for item in final_qa_reports] + [item["summary"] for item in slot_maps]
    return {
        "final_qa_reports": final_qa_reports,
        "deck_slot_maps": slot_maps,
        "aggregate_summary": combine_summaries(summaries),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate non-blocking typography diagnostic payloads.")
    parser.add_argument("--report-root", action="append", default=[], help="Root to scan for final-qa.json and deck_slot_map.json reports.")
    args = parser.parse_args(argv)

    result = {
        "helper_cases": validate_helper_cases(),
        "report_roots": [
            {"root": str(Path(root).resolve()), **validate_report_tree(Path(root).resolve())}
            for root in args.report_root
        ],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
