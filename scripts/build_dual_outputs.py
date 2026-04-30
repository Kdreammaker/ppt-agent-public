from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.build_deck import build_deck_from_spec
from scripts.build_html_deck import build_html


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def run_validation(args: list[str]) -> dict[str, Any]:
    result = subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, check=False)
    return {
        "command": ["python" if item == sys.executable else item for item in args],
        "status": "passed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdout_head": (result.stdout or "").strip().splitlines()[:5],
        "stderr_head": (result.stderr or "").strip().splitlines()[:5],
    }


def summary_paths(deck_id: str, report_dir: Path) -> tuple[Path, Path]:
    return report_dir / f"{deck_id}_dual_output_summary.json", report_dir / f"{deck_id}_dual_output_summary.md"


def write_reports(payload: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Dual Output Build Summary",
        "",
        f"- status: {payload['status']}",
        f"- deck id: {payload['deck_id']}",
        f"- PPTX: {payload['artifact_paths']['pptx']}",
        f"- HTML: {payload['artifact_paths']['html']}",
        f"- validations: {len(payload['validation_results'])}",
    ]
    failures = [item for item in payload["validation_results"] if item.get("status") != "passed"]
    if failures:
        lines.append(f"- failed validations: {len(failures)}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_dual_outputs(
    spec_path: Path,
    *,
    validate: bool,
    report_dir: Path | None = None,
    html_output: Path | None = None,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    report_root = report_dir.resolve() if report_dir else BASE_DIR / "outputs" / "reports"
    pptx_path = build_deck_from_spec(spec_path, report_dir=report_root)
    html_path, html_manifest_path = build_html(spec_path, html_output.resolve() if html_output else None)
    deck_id = pptx_path.stem
    validation_results: list[dict[str, Any]] = []
    if validate:
        validation_results.append(
            run_validation([sys.executable, "scripts/validate_pptx_package.py", base_relative(pptx_path)])
        )
        validation_results.append(
            run_validation(
                [
                    sys.executable,
                    "scripts/validate_html_output.py",
                    base_relative(html_path),
                    "--manifest",
                    base_relative(html_manifest_path),
                    "--output-json",
                    str(report_root / f"{deck_id}_html_validation.json"),
                ]
            )
        )
    status = "passed" if all(item["status"] == "passed" for item in validation_results) else "failed"
    json_path, md_path = summary_paths(deck_id, report_root)
    payload = {
        "schema_version": "1.0",
        "command": "build_dual_outputs",
        "status": status,
        "deck_id": deck_id,
        "spec_path": base_relative(spec_path),
        "artifact_paths": {
            "pptx": base_relative(pptx_path),
            "html": base_relative(html_path),
            "html_manifest": base_relative(html_manifest_path),
            "summary_json": base_relative(json_path),
            "summary_md": base_relative(md_path),
        },
        "validation_summary": {
            "enabled": validate,
            "passed": sum(1 for item in validation_results if item["status"] == "passed"),
            "failed": sum(1 for item in validation_results if item["status"] == "failed"),
        },
        "validation_results": validation_results,
        "policy_summary": {
            "local_only": True,
            "gateway_required": False,
            "upload_allowed": False,
            "telemetry_enabled": False,
            "outputs": ["pptx", "html"],
        },
    }
    write_reports(payload, json_path, md_path)
    if status != "passed":
        raise RuntimeError(f"Dual output validation failed: {base_relative(json_path)}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local PPTX and HTML outputs from one deck spec.")
    parser.add_argument("spec_path")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--report-dir", default=None)
    parser.add_argument("--html-output", default=None)
    args = parser.parse_args(argv)
    payload = build_dual_outputs(
        Path(args.spec_path),
        validate=args.validate,
        report_dir=Path(args.report_dir) if args.report_dir else None,
        html_output=Path(args.html_output) if args.html_output else None,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
