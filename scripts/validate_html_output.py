from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SCREENSHOT_ROOT = BASE_DIR / "outputs" / "playwright" / "html_validation"


class DeckHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.slide_sections = 0
        self.output_role = ""
        self.slide_count_attr = ""
        self.meta_role = ""
        self.buttons = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = set(attr.get("class", "").split())
        if tag == "section" and "deck-slide" in classes:
            self.slide_sections += 1
        if attr.get("data-output-role"):
            self.output_role = attr["data-output-role"]
        if attr.get("data-slide-count"):
            self.slide_count_attr = attr["data-slide-count"]
        if tag == "meta" and attr.get("name") == "ppt-output-role":
            self.meta_role = attr.get("content", "")
        if tag == "button":
            self.buttons += 1


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def base_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def validate_html(html_path: Path, manifest_path: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    html_path = html_path.resolve()
    manifest_path = manifest_path.resolve()
    if not html_path.exists():
        return {"html_path": base_relative(html_path), "manifest_path": base_relative(manifest_path)}, [f"HTML path does not exist: {html_path}"]
    if not manifest_path.exists():
        return {"html_path": base_relative(html_path), "manifest_path": base_relative(manifest_path)}, [f"HTML manifest does not exist: {manifest_path}"]

    html = html_path.read_text(encoding="utf-8")
    manifest = load_json(manifest_path)
    parser = DeckHtmlParser()
    parser.feed(html)

    if "<!doctype html>" not in html[:80].lower():
        errors.append("HTML output must start with <!doctype html>")
    if parser.output_role != "final_html":
        errors.append("HTML root must declare data-output-role=final_html")
    if parser.meta_role != "final_html":
        errors.append("HTML metadata must declare ppt-output-role=final_html")
    if manifest.get("output_role") != "final_html":
        errors.append("Manifest output_role must be final_html")
    if manifest.get("html_path") != base_relative(html_path):
        errors.append("Manifest html_path must match the validated HTML path")
    expected_slides = int(manifest.get("slide_count") or 0)
    if expected_slides <= 0:
        errors.append("Manifest slide_count must be positive")
    if parser.slide_sections != expected_slides:
        errors.append(f"HTML slide section count {parser.slide_sections} does not match manifest slide_count {expected_slides}")
    if parser.slide_count_attr != str(expected_slides):
        errors.append("HTML data-slide-count must match manifest slide_count")
    if parser.buttons < 2:
        errors.append("HTML output should expose previous/next presentation controls")
    if re.search(r"""(?:src|href)\s*=\s*["']https?://""", html, flags=re.IGNORECASE):
        errors.append("HTML output must not depend on remote src/href assets")
    if "external_asset_registry" in html.lower():
        errors.append("HTML output must not hard-code the external asset workspace path")

    report = {
        "html_path": base_relative(html_path),
        "manifest_path": base_relative(manifest_path),
        "slide_sections": parser.slide_sections,
        "manifest_slide_count": expected_slides,
        "output_role": manifest.get("output_role"),
        "asset_policy": manifest.get("asset_policy"),
        "browser_screenshot": None,
    }
    return report, errors


def run_playwright_screenshot(html_path: Path, screenshot_path: Path) -> dict[str, Any]:
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx is required for Playwright screenshot validation")
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        npx,
        "--yes",
        "playwright",
        "screenshot",
        "--browser=chromium",
        "--viewport-size=1440,900",
        html_path.resolve().as_uri(),
        str(screenshot_path),
    ]
    subprocess.run(command, cwd=BASE_DIR, check=True, timeout=120)
    if not screenshot_path.exists() or screenshot_path.stat().st_size <= 1024:
        raise RuntimeError(f"Playwright screenshot was not created or is too small: {screenshot_path}")
    return {
        "command": ["npx", "--yes", "playwright", "screenshot", "--browser=chromium", "--viewport-size=1440,900", html_path.resolve().as_uri(), base_relative(screenshot_path)],
        "screenshot_path": base_relative(screenshot_path),
        "bytes": screenshot_path.stat().st_size,
    }


def write_report(path: Path, report: dict[str, Any], errors: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "errors": len(errors),
            "browser_screenshot": bool(report.get("browser_screenshot")),
        },
        **report,
        "errors": errors,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate generated HTML deck output.")
    parser.add_argument("html_path")
    parser.add_argument("--manifest", default=None, help="Defaults to html_manifest.json next to the HTML file.")
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--browser-screenshot", action="store_true")
    parser.add_argument("--screenshot-path", default=None)
    args = parser.parse_args(argv)

    html_path = Path(args.html_path)
    manifest_path = Path(args.manifest) if args.manifest else html_path.with_name("html_manifest.json")
    report, errors = validate_html(html_path, manifest_path)
    if args.browser_screenshot and not errors:
        screenshot_path = (
            Path(args.screenshot_path)
            if args.screenshot_path
            else DEFAULT_SCREENSHOT_ROOT / f"{html_path.parent.name}.png"
        )
        try:
            report["browser_screenshot"] = run_playwright_screenshot(html_path, screenshot_path)
        except Exception as exc:
            errors.append(f"Playwright screenshot validation failed: {exc}")
    output_json = Path(args.output_json) if args.output_json else BASE_DIR / "outputs" / "reports" / f"{html_path.parent.name}_html_validation.json"
    write_report(output_json, report, errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"html_output=valid slides={report['slide_sections']} report={output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
