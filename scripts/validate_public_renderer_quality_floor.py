from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]

CASES = [
    {
        "case_id": "korean_explicit_list",
        "project_id": "quality-floor-korean-list",
        "expected_slide_count": 10,
        "prompt": (
            "한국의 5월 제철 음식으로 슬라이드 총 10장 구성. "
            "1번 슬라이드는 표지. 2번 슬라이드는 목차. "
            "3번부터 10번까지는 각 슬라이드에 다음 제철 음식 하나씩 소개: "
            "두릅, 죽순, 오이, 멍게, 주꾸미, 장어, 매실, 참외. "
            "각 음식의 제철 이유, 맛, 추천 조리법을 간단히 포함."
        ),
    },
    {
        "case_id": "english_business_update",
        "project_id": "quality-floor-business-update",
        "expected_slide_count": 6,
        "prompt": (
            "Create a 6-slide executive business update about quarterly operations. "
            "Focus on strategic priorities, progress updates, risk controls, staffing model, success metrics."
        ),
    },
    {
        "case_id": "visual_editorial_consumer",
        "project_id": "quality-floor-editorial-coffee",
        "expected_slide_count": 6,
        "prompt": (
            "Create a 6-slide visual editorial consumer guide about weekend coffee brewing rituals. "
            "Focus on pour-over setup, grind size, water temperature, blooming, serving mood."
        ),
    },
]

GENERIC_PRIMARY_LABELS = {
    "가이드",
    "guide",
    "include",
    "discussion path",
    "general detail",
    "visual area",
    "placeholder",
    "untitled deck",
}
RAW_OR_DEBUG_PATTERNS = [
    re.compile(r"\b(?:create|make|generate|build)\s+(?:an?\s+)?\d{1,2}\s*[- ]?\s*(?:slide|slides|page|pages)", re.IGNORECASE),
    re.compile(r"슬라이드\s*총?\s*\d{1,2}\s*(?:장|쪽|페이지|슬라이드)?\s*구성"),
    re.compile(r"\d{1,2}\s*번\s*슬라이드(?:는|은)?"),
    re.compile(r"\d{1,2}\s*번\s*부터\s*\d{1,2}\s*번\s*까지(?:는|은)?"),
    re.compile(r"\b(?:slot|template|asset|debug)[_-]", re.IGNORECASE),
    re.compile(r"\bDraft\s*\|", re.IGNORECASE),
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def load_stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    payload = json.loads(result.stdout)
    assert_true(isinstance(payload, dict), "ppt_make stdout JSON must be an object")
    return payload


def artifact_path(report: dict[str, Any], name: str) -> Path:
    artifacts = report.get("artifacts")
    assert_true(isinstance(artifacts, dict), "report missing artifacts")
    value = artifacts.get(name)
    assert_true(isinstance(value, str) and value, f"report missing artifact {name}")
    path = Path(value)
    assert_true(path.is_absolute(), f"{name} artifact is not absolute: {value}")
    assert_true(path.exists(), f"{name} artifact does not exist: {value}")
    return path


def pptx_slide_texts(path: Path) -> list[list[str]]:
    slides: list[list[str]] = []
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)],
            key=lambda value: int(re.search(r"(\d+)", value).group(1)),
        )
        for name in names:
            root = ET.fromstring(archive.read(name))
            slides.append(
                [
                    normalize(node.text or "")
                    for node in root.iter()
                    if node.tag.endswith("}t") and node.text and normalize(node.text)
                ]
            )
    return slides


def is_auxiliary_text(value: str) -> bool:
    text = normalize(value)
    return bool(
        not text
        or re.fullmatch(r"\d{1,2}", text)
        or text.startswith("Draft |")
        or re.search(r"\|\s*\d{1,2}/\d{1,2}$", text)
    )


def has_raw_or_debug_text(value: str) -> bool:
    return any(pattern.search(value) for pattern in RAW_OR_DEBUG_PATTERNS)


def primary_title(texts: list[str]) -> str:
    for text in texts:
        if not is_auxiliary_text(text):
            return normalize(text)
    return ""


def meaningful_texts(texts: list[str]) -> list[str]:
    output: list[str] = []
    for text in texts:
        cleaned = normalize(text)
        if is_auxiliary_text(cleaned):
            continue
        if cleaned.endswith(" focus"):
            continue
        if cleaned.casefold() in GENERIC_PRIMARY_LABELS:
            continue
        if has_raw_or_debug_text(cleaned):
            continue
        output.append(cleaned)
    return output


def html_titles(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    titles: list[str] = []
    for raw in re.findall(r"<h2[^>]*>(.*?)</h2>", text, flags=re.IGNORECASE | re.DOTALL):
        titles.append(normalize(re.sub(r"<[^>]+>", "", raw)))
    return titles


def validate_case(case: dict[str, Any], output_root: Path) -> dict[str, Any]:
    workspace = output_root / "workspace"
    result = run(
        [
            sys.executable,
            "scripts/ppt_make.py",
            str(case["prompt"]),
            "--workspace",
            workspace.as_posix(),
            "--mode",
            "assistant",
            "--build-approved",
            "--project-id",
            str(case["project_id"]),
        ]
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report = load_stdout_json(result)
    assert_true(report.get("status") == "built", f"{case['case_id']} did not build")

    pptx = artifact_path(report, "pptx")
    html_path = artifact_path(report, "html")
    slides = pptx_slide_texts(pptx)
    expected_count = int(case["expected_slide_count"])
    assert_true(len(slides) == expected_count, f"{case['case_id']} slide count {len(slides)} != {expected_count}")

    primary_titles = [primary_title(texts) for texts in slides]
    assert_true(all(primary_titles), f"{case['case_id']} has missing primary titles: {primary_titles}")
    bad_primary = [
        {"slide": index + 1, "title": title}
        for index, title in enumerate(primary_titles)
        if title.casefold() in GENERIC_PRIMARY_LABELS or has_raw_or_debug_text(title)
    ]
    assert_true(not bad_primary, f"{case['case_id']} has generic/raw primary titles: {bad_primary}")
    duplicate_titles = sorted({title.casefold() for title in primary_titles if primary_titles.count(title) > 1})
    assert_true(not duplicate_titles, f"{case['case_id']} has duplicate primary titles: {duplicate_titles}")

    densities: list[int] = []
    blank_or_sparse: list[dict[str, Any]] = []
    for index, texts in enumerate(slides):
        meaningful = meaningful_texts(texts)
        density = sum(len(item) for item in dict.fromkeys(meaningful))
        densities.append(density)
        minimum = 10 if index == 0 else 18
        if density < minimum:
            blank_or_sparse.append({"slide": index + 1, "density": density, "texts": meaningful[:5]})
    assert_true(not blank_or_sparse, f"{case['case_id']} has blank/sparse slides: {blank_or_sparse}")

    primary_title_set = {title for title in primary_titles}
    repeated = [
        {"text": text, "count": sum(1 for slide in slides if text in meaningful_texts(slide))}
        for text in sorted({item for slide in slides for item in meaningful_texts(slide)})
        if text not in primary_title_set
        and len(text) >= 18 and sum(1 for slide in slides if text in meaningful_texts(slide)) > max(4, int(len(slides) * 0.8))
    ]
    assert_true(not repeated, f"{case['case_id']} has repeated boilerplate text: {repeated[:5]}")

    titles = html_titles(html_path)
    html_mode = "explicit_exception"
    if len(titles) == len(primary_titles) and not all(re.fullmatch(r"\d+\.\s*[a-z_]+", title, flags=re.IGNORECASE) for title in titles):
        assert_true(titles == primary_titles, f"{case['case_id']} HTML/PPTX title divergence: {titles} != {primary_titles}")
        html_mode = "parity"
    return {
        "case_id": case["case_id"],
        "pptx": pptx.as_posix(),
        "html": html_path.as_posix(),
        "primary_titles": primary_titles,
        "text_density": densities,
        "html_title_mode": html_mode,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public renderer minimum visual quality floor.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    cases = [validate_case(case, output_root / str(case["case_id"])) for case in CASES]
    print(json.dumps({"status": "pass", "quality_floor": {"cases": cases}}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
