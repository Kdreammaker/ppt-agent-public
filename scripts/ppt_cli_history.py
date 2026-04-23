from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def default_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}"


def resolve_path(value: str, *, base: Path | None = None) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ((base or Path.cwd()) / path).resolve()
    return path


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def workspace_relative(workspace: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def manifest_path(workspace: Path, run_id: str) -> Path:
    return workspace / ".ppt-agent" / "runs" / run_id / "snapshot_manifest.json"


def command_snapshot(args: argparse.Namespace) -> int:
    workspace = resolve_path(args.workspace)
    spec = resolve_path(args.spec, base=workspace)
    if not spec.exists():
        raise FileNotFoundError(spec)
    run_id = args.run_id or default_run_id(spec.stem)
    run_dir = workspace / ".ppt-agent" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    spec_snapshot = run_dir / "spec_snapshot.json"
    shutil.copy2(spec, spec_snapshot)

    artifact_refs: dict[str, str] = {}
    for key, value in (("pptx", args.pptx), ("html", args.html), ("summary", args.summary)):
        if value:
            artifact_refs[key] = workspace_relative(workspace, resolve_path(value, base=workspace))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": utc_now(),
        "workspace_root": workspace.as_posix(),
        "spec_original_path": workspace_relative(workspace, spec),
        "spec_snapshot_path": workspace_relative(workspace, spec_snapshot),
        "artifact_refs": artifact_refs,
        "policy_summary": {
            "local_only": True,
            "gateway_touched": False,
            "upload_allowed": False,
            "binary_artifacts_copied": False,
        },
        "notes": args.notes,
    }
    path = manifest_path(workspace, run_id)
    write_json(path, manifest)
    print(
        json.dumps(
            {
                "command": "snapshot",
                "status": "passed",
                "run_id": run_id,
                "manifest": workspace_relative(workspace, path),
                "spec_snapshot": manifest["spec_snapshot_path"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def load_manifests(workspace: Path) -> list[dict[str, Any]]:
    root = workspace / ".ppt-agent" / "runs"
    if not root.exists():
        return []
    manifests: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/snapshot_manifest.json")):
        try:
            manifest = load_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        manifest["_manifest_path"] = workspace_relative(workspace, path)
        manifests.append(manifest)
    return sorted(manifests, key=lambda item: str(item.get("created_at", "")))


def command_history(args: argparse.Namespace) -> int:
    workspace = resolve_path(args.workspace)
    manifests = load_manifests(workspace)
    if args.limit and args.limit > 0:
        manifests = manifests[-args.limit :]
    payload = {
        "command": "history",
        "status": "passed",
        "workspace_root": workspace.as_posix(),
        "runs": [
            {
                "run_id": item.get("run_id"),
                "created_at": item.get("created_at"),
                "spec_original_path": item.get("spec_original_path"),
                "spec_snapshot_path": item.get("spec_snapshot_path"),
                "artifact_refs": item.get("artifact_refs", {}),
                "manifest_path": item.get("_manifest_path"),
            }
            for item in manifests
        ],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_rollback(args: argparse.Namespace) -> int:
    workspace = resolve_path(args.workspace)
    manifest = load_json(manifest_path(workspace, args.run_id))
    source = resolve_path(str(manifest["spec_snapshot_path"]), base=workspace)
    target = resolve_path(args.restore_spec, base=workspace) if args.restore_spec else resolve_path(str(manifest["spec_original_path"]), base=workspace)
    if not source.exists():
        raise FileNotFoundError(source)
    if target.exists() and not args.force:
        backup = target.with_suffix(target.suffix + ".rollback-backup")
        shutil.copy2(target, backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    payload = {
        "command": "rollback",
        "status": "passed",
        "run_id": args.run_id,
        "restored_spec": workspace_relative(workspace, target),
        "source_snapshot": workspace_relative(workspace, source),
        "policy_summary": {
            "local_only": True,
            "gateway_touched": False,
            "upload_allowed": False,
            "binary_artifacts_restored": False,
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local PPT workspace history and rollback commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--workspace", required=True)
    snapshot.add_argument("--spec", required=True)
    snapshot.add_argument("--run-id", default=None)
    snapshot.add_argument("--pptx", default=None)
    snapshot.add_argument("--html", default=None)
    snapshot.add_argument("--summary", default=None)
    snapshot.add_argument("--notes", default=None)
    snapshot.set_defaults(func=command_snapshot)

    history = subparsers.add_parser("history")
    history.add_argument("--workspace", required=True)
    history.add_argument("--limit", type=int, default=20)
    history.set_defaults(func=command_history)

    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("--workspace", required=True)
    rollback.add_argument("--run-id", required=True)
    rollback.add_argument("--restore-spec", default=None)
    rollback.add_argument("--force", action="store_true")
    rollback.set_defaults(func=command_rollback)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
