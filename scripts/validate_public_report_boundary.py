from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.public_report_safety import public_report_issues


def public_boundary_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for suffix in ("*.json", "*.md"):
        for path in root.rglob(suffix):
            if not path.is_file():
                continue
            parts = set(path.parts)
            if "fixtures" in parts or ".ppt-agent" in parts:
                continue
            if "reports" in parts or path.name == "html_manifest.json":
                files.append(path)
    for path in root.rglob("*.html"):
        if not path.is_file():
            continue
        parts = set(path.parts)
        if "fixtures" in parts or ".ppt-agent" in parts:
            continue
        if "outputs" not in parts:
            continue
        files.append(path)
    return sorted(set(files))


def report_files(root: Path) -> list[Path]:
    return [
        path
        for path in public_boundary_files(root)
        if path.suffix in {".json", ".md"} and "reports" in set(path.parts)
    ]


def html_files(root: Path) -> list[Path]:
    return [path for path in public_boundary_files(root) if path.suffix == ".html"]


def manifest_files(root: Path) -> list[Path]:
    return [path for path in public_boundary_files(root) if path.name == "html_manifest.json"]


def validate(root: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    scanned = public_boundary_files(root)
    for path in scanned:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = sorted(set(public_report_issues(text)))
        if hits:
            issues.append(
                {
                    "path": path.resolve().relative_to(root.resolve()).as_posix(),
                    "issues": hits,
                }
            )
    if issues:
        raise AssertionError(f"public boundary scan failed: {issues[:10]}")
    return {
        "status": "pass",
        "scanned_root": root.as_posix(),
        "scanned_report_files": len(report_files(root)),
        "scanned_html_files": len(html_files(root)),
        "scanned_html_manifest_files": len(manifest_files(root)),
        "issues": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan generated public-facing reports, HTML, and manifests for private path and marker leaks.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    result = validate(Path(args.output_root).resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
