from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"

WORKSPACE_DIRS = [
    ".ppt-agent",
    "assets/fonts",
    "assets/images",
    "assets/logos",
    "assets/references",
    "assets/slides",
    "assets/documents",
    "data/intake",
    "data/specs",
    "outputs/decks",
    "outputs/html",
    "outputs/reports",
]


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def workspace_rel(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def default_asset_manifest(workspace: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "workspace_root": workspace.as_posix(),
        "assets": [],
        "policy": {
            "source_type": "user_upload",
            "license_status_default": "user_responsibility",
            "private_upload_allowed_default": False,
            "public_reports_use_asset_ids": True,
        },
    }


def default_uploads_jsonl(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def default_private_connector(workspace: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "workspace_root": workspace.as_posix(),
        "connector_enabled": False,
        "public_safe_summary_only": True,
        "private_runtime": {
            "configured_by": "scripts/ppt_private_connector.py",
            "raw_private_payloads_stored": False,
            "private_assets_materialized_in_public_repo": False,
        },
        "asset_toolkit": {
            "configured_by": "public ai-asset-contribution-gate setup",
            "local_connector_file": ".assetctl-private-connector.local.json",
            "local_connector_file_committed": False,
        },
    }


def run_workspace_init(workspace: Path, force_readme: bool) -> None:
    command = [
        sys.executable,
        str(BASE_DIR / "scripts" / "ppt_cli_workspace.py"),
        "init",
        "--workspace",
        workspace.as_posix(),
        "--force-readme",
    ]
    if not force_readme:
        command.pop()
    result = subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "workspace init failed")


def copytree_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name in {".git", ".venv", "venv", "__pycache__", "outputs", "graphify-out"}:
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        else:
            shutil.copy2(item, target)


def public_source_root() -> Path:
    export_builder = BASE_DIR / "scripts" / "build_clean_release_export.py"
    export_root = BASE_DIR / "outputs" / "clean_release_export" / "ppt-agent-public"
    if export_builder.exists():
        result = subprocess.run(
            [sys.executable, str(export_builder), "--check"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if result.returncode == 0 and export_root.exists():
            return export_root
    return BASE_DIR


def bootstrap_public_repo(public_repo: Path) -> None:
    source = public_source_root()
    if source.resolve() == BASE_DIR.resolve():
        try:
            public_repo.resolve().relative_to(BASE_DIR.resolve())
        except ValueError:
            pass
        else:
            raise ValueError("--target must be outside the current public repo checkout")
    public_repo.mkdir(parents=True, exist_ok=True)
    copytree_contents(source, public_repo)


def create_workspace_tree(workspace: Path, *, force: bool) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    for relative in WORKSPACE_DIRS:
        (workspace / relative).mkdir(parents=True, exist_ok=True)

    run_workspace_init(workspace, force_readme=force)

    config_path = workspace / ".ppt-agent" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.exists() else {}
    config.update(
        {
            "schema_version": SCHEMA_VERSION,
            "workspace_root": workspace.as_posix(),
            "workspace_layout": "public_install_v1",
            "workspace_asset_manifest": ".ppt-agent/asset_manifest.json",
            "uploads_log": ".ppt-agent/uploads.jsonl",
            "private_connector": ".ppt-agent/private_connector.json",
            "outputs": {
                "specs": "data/specs/",
                "pptx": "outputs/decks/",
                "html": "outputs/html/",
                "reports": "outputs/reports/",
                "legacy_specs": "specs/",
                "legacy_pptx": "decks/",
                "legacy_html": "html/",
                "legacy_reports": "reports/",
            },
        }
    )
    write_json(config_path, config)

    asset_manifest_path = workspace / ".ppt-agent" / "asset_manifest.json"
    if force or not asset_manifest_path.exists():
        write_json(asset_manifest_path, default_asset_manifest(workspace))
    default_uploads_jsonl(workspace / ".ppt-agent" / "uploads.jsonl")

    private_connector_path = workspace / ".ppt-agent" / "private_connector.json"
    if force or not private_connector_path.exists():
        write_json(private_connector_path, default_private_connector(workspace))

    report = {
        "schema_version": SCHEMA_VERSION,
        "command": "ppt_install",
        "status": "installed",
        "generated_at": utc_now(),
        "workspace_root": workspace.as_posix(),
        "artifact_paths": {
            "config": ".ppt-agent/config.json",
            "consent": ".ppt-agent/consent.json",
            "asset_manifest": ".ppt-agent/asset_manifest.json",
            "uploads": ".ppt-agent/uploads.jsonl",
            "private_connector": ".ppt-agent/private_connector.json",
            "install_report": "outputs/reports/ppt_install_report.json",
        },
        "created_directories": WORKSPACE_DIRS,
        "policy_summary": {
            "user_assets_stay_in_workspace": True,
            "public_repo_contains_user_assets": False,
            "absolute_paths_allowed_only_in_workspace_local_config": True,
        },
    }
    write_json(workspace / "outputs" / "reports" / "ppt_install_report.json", report)
    return report


def command_install(args: argparse.Namespace) -> int:
    if args.target:
        install_root = resolve_path(args.target)
        public_repo = install_root / "ppt-agent-public"
        workspace = install_root / "workspace"
        bootstrap_public_repo(public_repo)
        marker = {
            "schema_version": SCHEMA_VERSION,
            "created_at": utc_now(),
            "source_repo": BASE_DIR.name,
            "note": "Public-safe repo files were bootstrapped from the clean public export when available.",
        }
        write_json(public_repo / ".ppt-agent-public-install.json", marker)
    else:
        if not args.workspace:
            raise SystemExit("--workspace is required when --target is not provided")
        workspace = resolve_path(args.workspace)
        install_root = workspace.parent
        public_repo = BASE_DIR

    report = create_workspace_tree(workspace, force=args.force)
    report["install_root"] = install_root.as_posix()
    report["public_repo"] = public_repo.as_posix()
    write_json(workspace / "outputs" / "reports" / "ppt_install_report.json", report)
    print(json.dumps({"status": "installed", "workspace": workspace.as_posix(), "report": "outputs/reports/ppt_install_report.json"}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install/bootstrap a public PPT Agent workspace tree.")
    parser.add_argument("--target", help="Install root that will contain ppt-agent-public/ and workspace/.")
    parser.add_argument("--workspace", help="Workspace path for an already-cloned repo install.")
    parser.add_argument("--force", action="store_true", help="Overwrite workspace-local bootstrap files.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return command_install(args)


if __name__ == "__main__":
    raise SystemExit(main())
