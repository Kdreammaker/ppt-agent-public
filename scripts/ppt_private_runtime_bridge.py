from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(command: list[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)


def request_id_from_summary(path: Path) -> str:
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return path.stem
    return str(payload.get("request_id") or path.stem)


def resolve_spec_ref(value: Any, public_spec_dir: Path, private_runtime: Path) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return value if isinstance(value, str) else None
    path = Path(value)
    resolved = path if path.is_absolute() else (public_spec_dir / path).resolve()
    if resolved.exists():
        return resolved.as_posix()
    candidate = private_runtime / value.replace("\\", "/").lstrip("./")
    if candidate.exists():
        return candidate.resolve().as_posix()
    name_candidate = private_runtime / "config" / Path(value).name
    if name_candidate.exists():
        return name_candidate.resolve().as_posix()
    return value


def copy_html_tree(source_index: Path, target_index: Path) -> None:
    if not source_index.exists():
        raise FileNotFoundError(f"private HTML output missing: {source_index}")
    if target_index.parent.exists():
        shutil.rmtree(target_index.parent)
    target_index.parent.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_index.parent, target_index.parent)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Public-safe bridge to an installed private PPT runtime checkout.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--private-runtime", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--html-output", required=True)
    parser.add_argument("--request-summary", required=True)
    parser.add_argument("--capability", default="private_template_library_build")
    parser.add_argument("--operating-mode", choices=["auto", "assistant"], default="assistant")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    private_runtime = Path(args.private_runtime).resolve()
    public_spec = Path(args.spec).resolve()
    public_output = Path(args.output).resolve()
    public_html_output = Path(args.html_output).resolve()
    request_summary = Path(args.request_summary).resolve()
    if not (private_runtime / "scripts" / "ppt_system.py").exists():
        raise SystemExit(f"private runtime is missing scripts/ppt_system.py: {private_runtime}")
    if not public_spec.exists():
        raise SystemExit(f"public spec does not exist: {public_spec}")

    request_id = request_id_from_summary(request_summary)
    private_request_root = private_runtime / "outputs" / "connector_requests" / request_id
    private_spec = private_request_root / "specs" / public_spec.name
    private_deck = private_runtime / "outputs" / "decks" / public_output.name
    private_html = private_runtime / "outputs" / "html" / public_output.stem / "index.html"

    spec_payload = load_json(public_spec)
    public_spec_dir = public_spec.parent.resolve()
    for key in ("theme_path", "reference_catalog_path", "blueprint_path"):
        resolved = resolve_spec_ref(spec_payload.get(key), public_spec_dir, private_runtime)
        if resolved is not None:
            spec_payload[key] = resolved
    spec_payload["output_path"] = private_deck.as_posix()
    write_json(private_spec, spec_payload)

    command = [
        sys.executable,
        str(private_runtime / "scripts" / "ppt_system.py"),
        "build-outputs",
        private_spec.as_posix(),
        "--validate",
        "--html-output",
        private_html.as_posix(),
    ]
    result = run(command, cwd=private_runtime, timeout=args.timeout_seconds)
    if result.returncode != 0:
        return result.returncode
    if not private_deck.exists():
        raise SystemExit(f"private PPTX output missing: {private_deck}")
    public_output.parent.mkdir(parents=True, exist_ok=True)
    if private_deck.resolve() != public_output.resolve():
        shutil.copy2(private_deck, public_output)
    if private_html.resolve() != public_html_output.resolve():
        copy_html_tree(private_html, public_html_output)

    payload = {
        "status": "ok",
        "capability": args.capability,
        "operating_mode": args.operating_mode,
        "artifact_paths": {
            "pptx": public_output.as_posix(),
            "html": public_html_output.as_posix(),
            "html_manifest": public_html_output.with_name("html_manifest.json").as_posix(),
        },
        "validation_summary": {
            "private_runtime_executed": True,
            "private_runtime_stdout_omitted": True,
            "public_artifacts_copied": True,
        },
        "policy_summary": {
            "tokens_printed": False,
            "raw_workspace_code_stored": False,
            "raw_private_payload_exposed": False,
            "private_runtime_path_stored_only_in_workspace_config": True,
        },
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
