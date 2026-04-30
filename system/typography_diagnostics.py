from __future__ import annotations

import math
import re
import unicodedata
from typing import Any


ROLE_ALIASES = {
    "cover_title": "title",
    "hero_title": "title",
    "slide_title": "title",
    "section_title": "title",
    "headline": "title",
    "title": "title",
    "subtitle": "subtitle",
    "kicker": "subtitle",
    "section_header": "subtitle",
    "body": "body",
    "body_strong": "body",
    "summary": "body",
    "description": "body",
    "message": "body",
    "bullet": "bullet",
    "caption": "caption",
    "eyebrow": "caption",
    "tag": "caption",
    "metric": "metric",
    "footer": "footer",
    "footer_note": "footer",
}

TYPOGRAPHY_BOUNDS = {
    "cjk": {
        "title": {"min_pt": 22.0, "default_pt": 27.0, "max_pt": 32.0, "target_lines": 1, "max_lines": 2},
        "subtitle": {"min_pt": 13.0, "default_pt": 15.0, "max_pt": 18.0, "target_lines": 1, "max_lines": 2},
        "body": {"min_pt": 10.5, "default_pt": 12.5, "max_pt": 15.0, "target_lines": 3, "max_lines": 5},
        "bullet": {"min_pt": 10.5, "default_pt": 12.0, "max_pt": 14.0, "target_lines": 4, "max_lines": 6},
        "caption": {"min_pt": 8.5, "default_pt": 10.0, "max_pt": 12.0, "target_lines": 1, "max_lines": 2},
        "metric": {"min_pt": 24.0, "default_pt": 32.0, "max_pt": 40.0, "target_lines": 1, "max_lines": 1},
        "footer": {"min_pt": 7.5, "default_pt": 8.5, "max_pt": 10.0, "target_lines": 1, "max_lines": 1},
    },
    "latin": {
        "title": {"min_pt": 24.0, "default_pt": 30.0, "max_pt": 36.0, "target_lines": 1, "max_lines": 2},
        "subtitle": {"min_pt": 14.0, "default_pt": 17.0, "max_pt": 20.0, "target_lines": 1, "max_lines": 2},
        "body": {"min_pt": 11.0, "default_pt": 13.5, "max_pt": 16.0, "target_lines": 3, "max_lines": 5},
        "bullet": {"min_pt": 11.0, "default_pt": 13.0, "max_pt": 15.0, "target_lines": 4, "max_lines": 6},
        "caption": {"min_pt": 9.0, "default_pt": 10.5, "max_pt": 12.5, "target_lines": 1, "max_lines": 2},
        "metric": {"min_pt": 28.0, "default_pt": 36.0, "max_pt": 44.0, "target_lines": 1, "max_lines": 1},
        "footer": {"min_pt": 8.0, "default_pt": 9.0, "max_pt": 10.5, "target_lines": 1, "max_lines": 1},
    },
}

TITLE_BODY_RATIO_THRESHOLD = 2.4


def contains_cjk(text: str) -> bool:
    return any(unicodedata.east_asian_width(char) in {"F", "W"} for char in text)


def contains_korean(text: str) -> bool:
    return bool(re.search(r"[\uac00-\ud7af]", text or ""))


def locale_family(locale: str | None, text: str = "") -> str:
    lowered = (locale or "").lower()
    if lowered.startswith(("ko", "ja", "zh")) or contains_cjk(text):
        return "cjk"
    return "latin"


def normalize_role(role: str | None, slot_name: str | None = None) -> str:
    raw = (role or slot_name or "body").lower()
    if raw in ROLE_ALIASES:
        return ROLE_ALIASES[raw]
    for token, normalized in ROLE_ALIASES.items():
        if token in raw:
            return normalized
    return "body"


def default_bounds(role: str, locale: str | None, text: str = "") -> dict[str, float | int]:
    family = locale_family(locale, text)
    return dict(TYPOGRAPHY_BOUNDS[family].get(role, TYPOGRAPHY_BOUNDS[family]["body"]))


def char_units(char: str) -> float:
    if char in "\r\n":
        return 0.0
    if unicodedata.east_asian_width(char) in {"F", "W"}:
        return 1.0
    if char.isspace():
        return 0.35
    if unicodedata.category(char).startswith("P"):
        return 0.35
    return 0.55


def weighted_text_units(text: str) -> float:
    return round(sum(char_units(char) for char in str(text or "")), 2)


def line_capacity_units(font_size_pt: float, box_width_in: float | None, max_chars_per_line: int | None) -> float:
    if max_chars_per_line:
        return max(1.0, float(max_chars_per_line))
    if box_width_in:
        usable_width = max(0.3, float(box_width_in) - 0.08)
        return max(4.0, usable_width * 72.0 / max(float(font_size_pt), 1.0) * 1.72)
    return 42.0


def estimated_lines(text: str, font_size_pt: float, box_width_in: float | None = None, max_chars_per_line: int | None = None) -> int:
    capacity = line_capacity_units(font_size_pt, box_width_in, max_chars_per_line)
    line_count = 0
    for line in str(text or "").splitlines() or [""]:
        units = weighted_text_units(line)
        line_count += max(1, int(math.ceil(units / capacity)))
    return line_count


def korean_broken_token_risk(text: str, *, box_width_in: float | None, font_size_pt: float, max_chars_per_line: int | None = None) -> tuple[bool, list[str]]:
    if not contains_korean(text):
        return False, []
    reasons: list[str] = []
    lines = str(text or "").splitlines()
    for left, right in zip(lines, lines[1:], strict=False):
        if left and right and contains_korean(left[-1]) and contains_korean(right[0]):
            reasons.append("explicit_line_break_splits_hangul_sequence")
            break
    capacity = line_capacity_units(font_size_pt, box_width_in, max_chars_per_line)
    for token in re.findall(r"[\uac00-\ud7afA-Za-z0-9]+", text or ""):
        if contains_korean(token) and weighted_text_units(token) > capacity:
            reasons.append("single_korean_token_exceeds_estimated_line_capacity")
            break
    return bool(reasons), reasons


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def diagnose_text_box(
    *,
    text: Any,
    role: str | None,
    locale: str | None,
    font_size: float | None,
    min_pt: float | None = None,
    default_pt: float | None = None,
    max_pt: float | None = None,
    target_lines: int | None = None,
    max_lines: int | None = None,
    box_width: float | None = None,
    box_height: float | None = None,
    max_chars_per_line: int | None = None,
    slot_name: str | None = None,
) -> dict[str, Any]:
    value = "" if text is None else str(text)
    normalized_role = normalize_role(role, slot_name)
    bounds = default_bounds(normalized_role, locale, value)
    resolved_min = float(min_pt if min_pt is not None else bounds["min_pt"])
    resolved_default = float(default_pt if default_pt is not None else bounds["default_pt"])
    resolved_max = float(max_pt if max_pt is not None else bounds["max_pt"])
    resolved_font = float(font_size if font_size is not None else resolved_default)
    resolved_target = int(target_lines if target_lines is not None else bounds["target_lines"])
    resolved_max_lines = int(max_lines if max_lines is not None else bounds["max_lines"])
    lines = estimated_lines(value, resolved_font, box_width, max_chars_per_line)
    estimated_height = round((resolved_font / 72.0) * 1.18 * lines + 0.08, 3)
    overflow_reasons: list[str] = []
    if lines > resolved_max_lines:
        overflow_reasons.append("estimated_lines_exceed_max_lines")
    if box_height is not None and estimated_height > float(box_height):
        overflow_reasons.append("estimated_text_height_exceeds_box_height")
    if resolved_font < resolved_min:
        overflow_reasons.append("font_size_below_min_pt")
    if resolved_font > resolved_max:
        overflow_reasons.append("font_size_above_max_pt")
    korean_risk, korean_reasons = korean_broken_token_risk(
        value,
        box_width_in=box_width,
        font_size_pt=resolved_font,
        max_chars_per_line=max_chars_per_line,
    )
    return {
        "role": normalized_role,
        "locale": locale or ("ko-KR" if contains_korean(value) else "und"),
        "font_size": resolved_font,
        "min_pt": resolved_min,
        "default_pt": resolved_default,
        "max_pt": resolved_max,
        "recommended_font_size": round(clamp(resolved_font, resolved_min, resolved_max), 2),
        "degraded_output_exception": resolved_font < resolved_min,
        "weighted_cjk_latin_units": weighted_text_units(value),
        "estimated_lines": lines,
        "target_lines": resolved_target,
        "max_lines": resolved_max_lines,
        "box_width": box_width,
        "box_height": box_height,
        "estimated_text_height": estimated_height,
        "overflow_risk": bool(overflow_reasons),
        "overflow_reasons": overflow_reasons,
        "korean_broken_token_risk": korean_risk,
        "korean_broken_token_reasons": korean_reasons,
        "title_body_ratio": None,
        "title_body_ratio_risk": False,
    }


def annotate_title_body_ratio(diagnostics: list[dict[str, Any]], *, threshold: float = TITLE_BODY_RATIO_THRESHOLD) -> list[dict[str, Any]]:
    by_slide: dict[Any, list[dict[str, Any]]] = {}
    for item in diagnostics:
        by_slide.setdefault(item.get("slide_number"), []).append(item)
    for items in by_slide.values():
        title_sizes = [float(item["font_size"]) for item in items if item.get("role") == "title" and item.get("font_size")]
        body_sizes = [float(item["font_size"]) for item in items if item.get("role") in {"body", "bullet"} and item.get("font_size")]
        if not title_sizes or not body_sizes:
            continue
        ratio = round(max(title_sizes) / max(min(body_sizes), 0.1), 2)
        risk = ratio > threshold
        for item in items:
            item["title_body_ratio"] = ratio
            item["title_body_ratio_risk"] = risk
    return diagnostics


def diagnostics_summary(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "items": len(diagnostics),
        "overflow_risks": sum(1 for item in diagnostics if item.get("overflow_risk")),
        "korean_broken_token_risks": sum(1 for item in diagnostics if item.get("korean_broken_token_risk")),
        "title_body_ratio_risks": sum(1 for item in diagnostics if item.get("title_body_ratio_risk")),
        "degraded_output_exceptions": sum(1 for item in diagnostics if item.get("degraded_output_exception")),
    }
