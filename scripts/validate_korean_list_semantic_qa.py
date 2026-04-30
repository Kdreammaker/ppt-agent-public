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
PROMPT = (
    "한국의 5월 제철 음식으로 슬라이드 총 10장 구성. "
    "1번 슬라이드는 표지. "
    "2번 슬라이드는 목차. "
    "3번부터 10번까지는 각 슬라이드에 다음 제철 음식 하나씩 소개: "
    "두릅, 죽순, 오이, 멍게, 주꾸미, 장어, 매실, 참외. "
    "각 음식의 제철 이유, 맛, 추천 조리법을 간단히 포함."
)
PROJECT_CHECKPOINT = "semantic-korean-list-checkpoint"
PROJECT_APPROVED = "semantic-korean-list-approved"
EXPECTED_TITLES = ["한국의 5월 제철 음식", "목차", "두릅", "죽순", "오이", "멍게", "주꾸미", "장어", "매실", "참외"]
META_PATTERNS = [
    re.compile(r"슬라이드\s*총?\s*\d{1,2}\s*(?:장|쪽|페이지|슬라이드)?\s*구성"),
    re.compile(r"\d{1,2}\s*번\s*슬라이드(?:는|은)?"),
    re.compile(r"\d{1,2}\s*번\s*부터\s*\d{1,2}\s*번\s*까지(?:는|은)?"),
    re.compile(r"각\s*슬라이드에\s*다음"),
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def parse_stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout was not JSON: {result.stdout[-1000:]}") from exc
    assert_true(isinstance(payload, dict), "stdout JSON must be an object")
    return payload


def artifact_path(report: dict[str, Any], name: str) -> Path | None:
    artifacts = report.get("artifacts")
    assert_true(isinstance(artifacts, dict), "ppt_make report missing artifacts")
    value = artifacts.get(name)
    if not value:
        return None
    path = Path(str(value))
    assert_true(path.is_absolute(), f"{name} artifact is not absolute: {value}")
    assert_true(path.exists(), f"{name} artifact does not exist: {value}")
    return path


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def html_titles(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    titles = []
    for raw in re.findall(r"<h2[^>]*>(.*?)</h2>", text, flags=re.IGNORECASE | re.DOTALL):
        cleaned = re.sub(r"<[^>]+>", "", raw)
        titles.append(normalize_title(cleaned))
    return titles


def html_visible_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_title(text)


def pptx_slide_texts(path: Path) -> list[list[str]]:
    slides: list[list[str]] = []
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)],
            key=lambda value: int(re.search(r"(\d+)", value).group(1)),
        )
        for name in names:
            root = ET.fromstring(archive.read(name))
            texts = [
                normalize_title(node.text or "")
                for node in root.iter()
                if node.tag.endswith("}t") and node.text and normalize_title(node.text)
            ]
            slides.append(texts)
    return slides


def title_candidates_from_guide(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    guide = json.loads(path.read_text(encoding="utf-8-sig"))
    slides = (((guide or {}).get("slide_plan") or {}).get("slides") or [])
    titles: list[str] = []
    for slide in slides:
        candidates = slide.get("visible_content_candidates") if isinstance(slide, dict) else None
        if isinstance(candidates, list) and candidates:
            titles.append(normalize_title(str(candidates[0])))
    return titles


def assert_no_meta_text(values: list[str], *, source: str) -> None:
    hits = []
    for value in values:
        for pattern in META_PATTERNS:
            if pattern.search(value):
                hits.append(value)
                break
    assert_true(not hits, f"{source} contains visible meta-command text: {hits[:5]}")


def assert_titles_are_semantic(titles: list[str], *, source: str) -> None:
    assert_true(titles == EXPECTED_TITLES, f"{source} titles diverged: {titles}")
    normalized = [normalize_title(title).casefold() for title in titles]
    duplicates = sorted({title for title in normalized if normalized.count(title) > 1})
    assert_true(not duplicates, f"{source} duplicate titles found: {duplicates}")
    assert_no_meta_text(titles, source=source)


def validate_checkpoint(workspace: Path) -> dict[str, Any]:
    result = run(
        [
            sys.executable,
            "scripts/ppt_make.py",
            PROMPT,
            "--workspace",
            workspace.as_posix(),
            "--mode",
            "assistant",
            "--project-id",
            PROJECT_CHECKPOINT,
        ]
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report = parse_stdout_json(result)
    assert_true(report.get("status") == "waiting_for_approval", f"unexpected checkpoint status: {report.get('status')}")
    assert_true(artifact_path(report, "pptx") is None, "checkpoint should not expose PPTX")
    assert_true(artifact_path(report, "html") is None, "checkpoint should not expose HTML")
    return {"project_id": PROJECT_CHECKPOINT, "status": report.get("status")}


def validate_approved(workspace: Path) -> dict[str, Any]:
    result = run(
        [
            sys.executable,
            "scripts/ppt_make.py",
            PROMPT,
            "--workspace",
            workspace.as_posix(),
            "--mode",
            "assistant",
            "--build-approved",
            "--project-id",
            PROJECT_APPROVED,
        ]
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report = parse_stdout_json(result)
    assert_true(report.get("status") == "built", f"unexpected approved status: {report.get('status')}")
    pptx = artifact_path(report, "pptx")
    html_path = artifact_path(report, "html")
    assert_true(pptx is not None, "approved build missing PPTX")
    assert_true(html_path is not None, "approved build missing HTML")

    slides = pptx_slide_texts(pptx)
    assert_true(len(slides) == len(EXPECTED_TITLES), f"unexpected PPTX slide count: {len(slides)}")
    blank = [index + 1 for index, texts in enumerate(slides) if not texts]
    assert_true(not blank, f"PPTX contains blank slides: {blank}")
    flattened = [" ".join(texts) for texts in slides]
    assert_no_meta_text(flattened, source="pptx")
    for index, expected in enumerate(EXPECTED_TITLES):
        assert_true(any(expected == text or expected in text for text in slides[index]), f"PPTX slide {index + 1} missing title {expected}")

    titles = html_titles(html_path)
    guide_titles = title_candidates_from_guide(artifact_path(report, "guide_packet"))
    if titles == EXPECTED_TITLES:
        title_source = "html"
        assert_titles_are_semantic(titles, source="html")
    else:
        title_source = "guide_packet"
        assert_titles_are_semantic(guide_titles, source="guide_packet")
    assert_no_meta_text([html_visible_text(html_path)], source="html")
    return {
        "project_id": PROJECT_APPROVED,
        "status": report.get("status"),
        "pptx": pptx.as_posix(),
        "html": html_path.as_posix(),
        "title_source": title_source,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Korean list prompt semantic deck hygiene.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    workspace = output_root / "workspace"
    result = {
        "status": "pass",
        "prompt": "may_seasonal_food_korea_10_slide_list",
        "expected_titles": EXPECTED_TITLES,
        "assistant_checkpoint": validate_checkpoint(workspace),
        "assistant_approved": validate_approved(workspace),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
