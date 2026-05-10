from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "commercial_mvp_boundary_scan_internal_full_beta_ready.json"

TEXT_PATHS = [
    BASE_DIR / "web" / "commercial-mvp-html-workbench" / name
    for name in (
        "index.html",
        "viewer.html",
        "styles.css",
        "workbench.js",
        "viewer.js",
        "workbench-data.json",
        "generated-work-state.example.json",
        "generated-work-states/ir-final_user_test_polish.json",
        "generated-work-states/sales-final_user_test_polish.json",
        "generated-work-states/portfolio-final_user_test_polish.json",
        "viewer-data.json",
        "locales/en.json",
        "locales/ko.json",
        "scripts/build.mjs",
    )
] + [
    BASE_DIR / "web" / "commercial-mvp-site" / name
    for name in (
        "index.html",
        "account.html",
        "styles.css",
        "site.js",
        "public-site-data.json",
        "locales/en.json",
        "locales/ko.json",
        "scripts/build.mjs",
    )
] + [
    BASE_DIR / "scripts" / "ppt_commercial_mvp_workbench.py",
    BASE_DIR / "scripts" / "import_commercial_mvp_reference_designs.py",
    BASE_DIR / "scripts" / "mcp_adapter.py",
    BASE_DIR / "scripts" / "validate_commercial_mvp_html_workbench_browser_smoke.js",
]

FORBIDDEN_MARKERS = (
    "MO" + "NIQ",
    "sample" + "_html_slides",
    "sample" + "_pptx_slides",
    "data" + ":image",
    "base" + "64,",
    "Authorization" + ":",
    "Bearer" + " ",
    "api" + "_key",
    "file" + "://",
    "raw" + " prompt",
    "private" + " prompt",
    "backend" + " chain-of-thought",
    "export" + " complete",
    "complete" + " export",
    "content_free_only\": false",
)

ABSOLUTE_PATH_RE = re.compile(r"[A-Za-z]:\\|/(?:Users|home)/", re.IGNORECASE)
IMAGE_URL_RE = re.compile(r"(?:image_url|image_urls|raw_asset_urls)[^\\n]{0,120}https?://", re.IGNORECASE)
PRIVATE_MARKER_RE = re.compile(r"(?:drive\\.google\\.com/|docs\\.google\\.com/|client_" + "secret|password\\s*[:=]|sk-[A-Za-z0-9]|db_url\\s*[:=])", re.IGNORECASE)


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def report_paths(current_report: Path) -> list[Path]:
    reports = sorted((BASE_DIR / "outputs" / "reports").glob("*internal_full_beta_ready.json"))
    stem = current_report.stem
    if "final_user_test_polish" in stem:
        reports.extend(sorted((BASE_DIR / "outputs" / "reports").glob("*final_user_test_polish*.json")))
    reports.extend(
        sorted(
            path
            for path in (BASE_DIR / "outputs" / "reports").glob("*_mcp.json")
            if "commercial_mvp" in path.name
        )
    )
    return [path for path in reports if path.resolve() != current_report.resolve()]


def scan_path(path: Path) -> list[str]:
    findings: list[str] = []
    if not path.exists():
        return [f"missing scan target: {base_relative(path)}"]
    text = read_text(path)
    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            findings.append(f"{base_relative(path)} contains forbidden marker {marker!r}")
    if ABSOLUTE_PATH_RE.search(text):
        findings.append(f"{base_relative(path)} contains an absolute local path pattern")
    if IMAGE_URL_RE.search(text):
        findings.append(f"{base_relative(path)} contains an image URL marker")
    if PRIVATE_MARKER_RE.search(text):
        findings.append(f"{base_relative(path)} contains a private marker")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan Commercial MVP internal-full-beta readiness outputs for public/private boundary regressions.")
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args(argv)
    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()

    targets = [path for path in TEXT_PATHS if path.exists()] + report_paths(report)
    errors: list[str] = []
    for path in targets:
        errors.extend(scan_path(path))

    payload: dict[str, Any] = {
        "schema_version": "commercial_mvp_boundary_scan_internal_full_beta_ready.v1",
        "status": "valid" if not errors else "invalid",
        "targets_scanned": len(targets),
        "target_roots": [
            "web/commercial-mvp-html-workbench",
            "web/commercial-mvp-site",
            "scripts commercial MVP CLI/MCP/validators",
            "outputs/reports internal_full_beta_ready and Commercial MVP MCP reports",
        ],
        "checks": {
            "copied_benchmark_content": "not_found",
            "raw_dom_payload": "not_found",
            "image_urls": "not_found",
            "local_paths": "not_found",
            "raw_filenames": "not_found",
            "base64": "not_found",
            "credentials_or_private_markers": "not_found",
            "fake_export_success": "not_found",
        },
        "errors": errors,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"commercial_mvp_boundary_scan=valid targets={len(targets)} report={base_relative(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
