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
GUIDE_HTML_TITLE_PATTERN = re.compile(r"\d+\.\s*[a-z_][a-z0-9_ -]*", re.IGNORECASE)
PLACEHOLDER_HTML_TITLES = {
    "draft",
    "draft |",
    "guide",
    "가이드",
    "include",
    "visual area",
    "placeholder",
    "general detail",
    "discussion path",
}
REQUIRED_TYPOGRAPHY_DIAGNOSTIC_FIELDS = {
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
}


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


def default_repo_mode() -> str:
    if (BASE_DIR / "scripts" / "compose_deck_plan_from_intake.py").exists():
        return "public"
    return "internal"


def artifact_path_optional(report: dict[str, Any], name: str) -> Path | None:
    artifacts = report.get("artifacts")
    assert_true(isinstance(artifacts, dict), "report missing artifacts")
    value = artifacts.get(name)
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    assert_true(path.is_absolute(), f"{name} artifact is not absolute: {value}")
    assert_true(path.exists(), f"{name} artifact does not exist: {value}")
    return path


def project_dir_from_report(report: dict[str, Any]) -> Path:
    absolute_paths = report.get("absolute_paths")
    value = absolute_paths.get("project") if isinstance(absolute_paths, dict) else None
    if not isinstance(value, str) or not value:
        report_path = artifact_path_optional(report, "report")
        if report_path is not None:
            value = str(report_path.parents[1])
        else:
            workspace_root = report.get("workspace_root")
            project_id = report.get("project_id")
            assert_true(isinstance(workspace_root, str) and isinstance(project_id, str), "report missing project path")
            value = str(Path(workspace_root) / "outputs" / "projects" / project_id)
    path = Path(value)
    assert_true(path.is_absolute(), f"project path is not absolute: {value}")
    assert_true(path.exists(), f"project path does not exist: {value}")
    return path


def quality_artifacts(report: dict[str, Any]) -> tuple[Path, Path, Path]:
    project_dir = project_dir_from_report(report)
    pptx = artifact_path_optional(report, "pptx") or project_dir / "generated.pptx"
    html_path = artifact_path_optional(report, "html") or project_dir / "html" / "guide.html"
    assert_true(pptx.exists(), f"quality-floor PPTX artifact does not exist: {pptx}")
    assert_true(html_path.exists(), f"quality-floor HTML artifact does not exist: {html_path}")
    return pptx, html_path, project_dir


def preview_render_warning(project_dir: Path) -> dict[str, Any] | None:
    qa_path = project_dir / "final-qa.json"
    if not qa_path.exists():
        return None
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    preview = qa.get("preview_report")
    if not isinstance(preview, dict):
        return None
    if preview.get("status") != "blocked_render_failed" or preview.get("validation_blocker") is not True:
        return None
    return {
        "status": preview.get("status"),
        "validation_blocker": preview.get("validation_blocker"),
        "fallback_reason": preview.get("fallback_reason"),
        "render_attempts": preview.get("render_attempts"),
        "final_qa": qa_path.as_posix(),
    }


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


def validate_html_title_policy(case_id: str, titles: list[str], primary_titles: list[str], *, repo_mode: str) -> str:
    placeholder_titles = [
        title
        for title in titles
        if title.casefold() in PLACEHOLDER_HTML_TITLES or title.casefold().startswith("draft |")
    ]
    assert_true(not placeholder_titles, f"{case_id} HTML exposes placeholder h2 titles: {placeholder_titles}")
    if repo_mode == "public":
        assert_true(
            len(titles) == len(primary_titles),
            f"{case_id} HTML/PPTX title count mismatch: {len(titles)} != {len(primary_titles)}; {titles}",
        )
        assert_true(titles == primary_titles, f"{case_id} HTML/PPTX title divergence: {titles} != {primary_titles}")
        return "parity"
    if len(titles) == len(primary_titles) and titles == primary_titles:
        return "parity"
    assert_true(
        titles and all(GUIDE_HTML_TITLE_PATTERN.fullmatch(title) for title in titles),
        f"{case_id} internal guide HTML exception requires archetype h2 titles: {titles}",
    )
    return "internal_guide_html_exception"


def expect_public_html_policy_failure(case_id: str, titles: list[str], primary_titles: list[str]) -> dict[str, str]:
    try:
        validate_html_title_policy(case_id, titles, primary_titles, repo_mode="public")
    except AssertionError as exc:
        return {"case_id": case_id, "status": "pass", "failure": str(exc)}
    raise AssertionError(f"{case_id} negative HTML parity test unexpectedly passed")


def validate_public_html_policy_negative_tests() -> list[dict[str, str]]:
    return [
        expect_public_html_policy_failure("negative_title_count_mismatch", ["Only One"], ["One", "Two"]),
        expect_public_html_policy_failure("negative_placeholder_h2", ["Visual area", "Two"], ["One", "Two"]),
    ]


def assert_typography_diagnostic_item(item: dict[str, Any], *, source: str) -> None:
    missing = sorted(REQUIRED_TYPOGRAPHY_DIAGNOSTIC_FIELDS - set(item))
    assert_true(not missing, f"{source} missing typography diagnostic fields: {missing}")
    assert_true(item["min_pt"] <= item["recommended_font_size"] <= item["max_pt"], f"{source} recommended font size outside bounds")
    if item["font_size"] < item["min_pt"]:
        assert_true(item.get("degraded_output_exception") is True, f"{source} below-min font should be explicit degraded-output exception")


def validate_typography_diagnostics(report: dict[str, Any], project_dir: Path, *, repo_mode: str) -> dict[str, Any]:
    qa_path = project_dir / "final-qa.json"
    if qa_path.exists():
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        diagnostics = qa.get("typography_diagnostics")
        assert_true(isinstance(diagnostics, dict), f"{qa_path} missing typography_diagnostics")
        assert_true(diagnostics.get("blocking") is False, f"{qa_path} typography diagnostics must be non-blocking")
        items = diagnostics.get("items")
        assert_true(isinstance(items, list) and items, f"{qa_path} typography diagnostics has no items")
        for index, item in enumerate(items[:5]):
            assert_true(isinstance(item, dict), f"{qa_path} typography diagnostic item is not an object")
            assert_typography_diagnostic_item(item, source=f"{qa_path}:items[{index}]")
        return {"source": "final_qa", "items": len(items), "status": diagnostics.get("status")}

    absolute_paths = report.get("absolute_paths")
    workspace_root = report.get("workspace_root")
    if not workspace_root and isinstance(absolute_paths, dict):
        workspace_root = absolute_paths.get("workspace")
    if not workspace_root and len(project_dir.parents) >= 3:
        workspace_root = project_dir.parents[2].as_posix()
    assert_true(isinstance(workspace_root, str) and workspace_root, "report missing workspace_root for typography diagnostics")
    slot_map = Path(workspace_root) / "outputs" / "reports" / "deck_slot_map.json"
    assert_true(repo_mode == "public", "missing final-qa typography diagnostics is only expected for public plan/spec route")
    assert_true(slot_map.exists(), f"public typography diagnostics slot map missing: {slot_map}")
    payload = json.loads(slot_map.read_text(encoding="utf-8"))
    summary = payload.get("summary", {}).get("typography_diagnostics")
    assert_true(isinstance(summary, dict), f"{slot_map} missing typography diagnostics summary")
    text_slots = [
        slot
        for slot in payload.get("slots", [])
        if isinstance(slot, dict) and slot.get("slot_kind") == "text"
    ]
    assert_true(text_slots, f"{slot_map} has no text slots")
    for slot in text_slots[:8]:
        diagnostic = slot.get("typography_diagnostics")
        assert_true(isinstance(diagnostic, dict), f"{slot_map} text slot missing typography diagnostics")
        assert_typography_diagnostic_item(diagnostic, source=f"{slot_map}:{slot.get('slot_name')}")
    return {"source": "deck_slot_map", "items": len(text_slots), "summary": summary}


def validate_case(case: dict[str, Any], output_root: Path, *, repo_mode: str) -> dict[str, Any]:
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
    report = load_stdout_json(result)
    pptx, html_path, project_dir = quality_artifacts(report)
    warning = None
    if result.returncode != 0 or report.get("status") != "built":
        warning = preview_render_warning(project_dir)
        assert_true(
            repo_mode == "internal" and warning is not None,
            (
                f"{case['case_id']} did not build cleanly: returncode={result.returncode}, "
                f"status={report.get('status')}, stderr={result.stderr.strip()}"
            ),
        )

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
    html_mode = validate_html_title_policy(case["case_id"], titles, primary_titles, repo_mode=repo_mode)
    typography_diagnostics = validate_typography_diagnostics(report, project_dir, repo_mode=repo_mode)
    payload = {
        "case_id": case["case_id"],
        "build_status": report.get("status"),
        "pptx": pptx.as_posix(),
        "html": html_path.as_posix(),
        "primary_titles": primary_titles,
        "text_density": densities,
        "html_title_mode": html_mode,
        "typography_diagnostics": typography_diagnostics,
    }
    if warning is not None:
        payload["preview_render_warning"] = warning
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public renderer minimum visual quality floor.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--repo-mode", choices=["public", "internal"], default=default_repo_mode())
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    cases = [validate_case(case, output_root / str(case["case_id"]), repo_mode=args.repo_mode) for case in CASES]
    negative_tests = validate_public_html_policy_negative_tests()
    print(
        json.dumps(
            {
                "status": "pass",
                "quality_floor": {
                    "repo_mode": args.repo_mode,
                    "cases": cases,
                    "public_html_policy_negative_tests": negative_tests,
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
