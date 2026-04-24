from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"

ASSET_TYPES = {
    "font": {
        "asset_class": "typography",
        "directory": "assets/fonts",
        "extensions": {".ttf", ".otf", ".woff", ".woff2"},
    },
    "image": {
        "asset_class": "image",
        "directory": "assets/images",
        "extensions": {".png", ".jpg", ".jpeg", ".webp", ".svg"},
    },
    "logo": {
        "asset_class": "image",
        "directory": "assets/logos",
        "extensions": {".png", ".jpg", ".jpeg", ".svg"},
    },
    "reference": {
        "asset_class": "reference",
        "directory": "assets/references",
        "extensions": {".pdf", ".docx", ".pptx", ".txt", ".md", ".json"},
    },
    "slides": {
        "asset_class": "slides",
        "directory": "assets/slides",
        "extensions": {".pptx", ".potx"},
    },
    "document": {
        "asset_class": "document",
        "directory": "assets/documents",
        "extensions": {".pdf", ".docx", ".txt", ".md"},
    },
}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%d")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "asset"


def resolve_workspace(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_path(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "asset_manifest.json"


def uploads_path(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "uploads.jsonl"


def default_manifest(workspace: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "workspace_root": workspace.as_posix(),
        "assets": [],
        "policy": {
            "source_type": "user_upload",
            "license_status_default": "user_responsibility",
            "private_upload_allowed_default": False,
        },
    }


def ensure_manifest(workspace: Path) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / ".ppt-agent").mkdir(parents=True, exist_ok=True)
    manifest = load_json(manifest_path(workspace)) or default_manifest(workspace)
    manifest.setdefault("schema_version", SCHEMA_VERSION)
    manifest.setdefault("workspace_root", workspace.as_posix())
    manifest.setdefault("assets", [])
    return manifest


def workspace_relative(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def unique_destination(workspace: Path, source: Path, asset_type: str) -> Path:
    spec = ASSET_TYPES[asset_type]
    folder = workspace / spec["directory"]
    folder.mkdir(parents=True, exist_ok=True)
    stem = slugify(source.stem)
    extension = source.suffix.lower()
    base_name = f"user_{date_stamp()}_{stem}{extension}"
    destination = folder / base_name
    counter = 2
    while destination.exists():
        destination = folder / f"user_{date_stamp()}_{stem}_{counter}{extension}"
        counter += 1
    return destination


def asset_id_for(asset_type: str, source: Path, digest: str) -> str:
    stem = slugify(source.stem)
    return f"user.{asset_type}.{stem}.{date_stamp()}.{digest[:10]}"


def append_upload_event(workspace: Path, event: dict[str, Any]) -> None:
    path = uploads_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def command_import(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    source = Path(args.file)
    if not source.is_absolute():
        source = (Path.cwd() / source).resolve()
    if not source.exists() or not source.is_file():
        raise SystemExit(f"source file does not exist: {source}")
    spec = ASSET_TYPES[args.type]
    if source.suffix.lower() not in spec["extensions"]:
        raise SystemExit(f"{args.type} does not accept {source.suffix}; allowed={sorted(spec['extensions'])}")

    manifest = ensure_manifest(workspace)
    digest = sha256_file(source)
    destination = unique_destination(workspace, source, args.type)
    shutil.copy2(source, destination)
    relative_path = workspace_relative(destination, workspace)
    record = {
        "asset_id": args.asset_id or asset_id_for(args.type, source, digest),
        "source_type": "user_upload",
        "asset_class": spec["asset_class"],
        "asset_type": args.type,
        "workspace_relative_path": relative_path,
        "sha256": digest,
        "size_bytes": destination.stat().st_size,
        "license_status": args.license_status,
        "allowed_for_ppt": True,
        "private_upload_allowed": False,
        "imported_at": utc_now(),
    }
    assets = [item for item in manifest.get("assets", []) if item.get("asset_id") != record["asset_id"]]
    assets.append(record)
    manifest["assets"] = assets
    manifest["updated_at"] = utc_now()
    write_json(manifest_path(workspace), manifest)
    append_upload_event(
        workspace,
        {
            "event": "import",
            "created_at": utc_now(),
            "asset_id": record["asset_id"],
            "asset_type": args.type,
            "workspace_relative_path": relative_path,
            "sha256": digest,
        },
    )
    print(json.dumps({"status": "imported", "asset": record}, indent=2, ensure_ascii=False))
    return 0


def validate_manifest(workspace: Path) -> tuple[dict[str, Any], list[str]]:
    manifest = ensure_manifest(workspace)
    errors: list[str] = []
    seen: set[str] = set()
    for index, asset in enumerate(manifest.get("assets", [])):
        label = f"assets[{index}]"
        if asset.get("source_type") != "user_upload":
            errors.append(f"{label}.source_type must be user_upload")
        asset_id = str(asset.get("asset_id") or "")
        if not asset_id:
            errors.append(f"{label}.asset_id is required")
        if asset_id in seen:
            errors.append(f"duplicate asset_id: {asset_id}")
        seen.add(asset_id)
        relative = str(asset.get("workspace_relative_path") or "")
        if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            errors.append(f"{label}.workspace_relative_path must be workspace-relative")
            continue
        file_path = workspace / relative
        if not file_path.exists():
            errors.append(f"{label} file is missing: {relative}")
            continue
        digest = sha256_file(file_path)
        if asset.get("sha256") != digest:
            errors.append(f"{label}.sha256 mismatch for {relative}")
        if asset.get("size_bytes") != file_path.stat().st_size:
            errors.append(f"{label}.size_bytes mismatch for {relative}")
        if asset.get("private_upload_allowed") is not False:
            errors.append(f"{label}.private_upload_allowed must be false by default")
    return manifest, errors


def command_list(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    manifest = ensure_manifest(workspace)
    print(json.dumps({"workspace": workspace.as_posix(), "assets": manifest.get("assets", [])}, indent=2, ensure_ascii=False))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    manifest, errors = validate_manifest(workspace)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "valid" if not errors else "invalid",
        "summary": {"assets": len(manifest.get("assets", [])), "errors": len(errors)},
        "errors": errors,
    }
    write_json(workspace / "outputs" / "reports" / "workspace_asset_manifest_validation.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


def find_asset(workspace: Path, asset_id: str) -> dict[str, Any] | None:
    manifest = ensure_manifest(workspace)
    for asset in manifest.get("assets", []):
        if asset.get("asset_id") == asset_id:
            return asset
    return None


def command_resolve(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    asset = find_asset(workspace, args.asset_id)
    if not asset:
        raise SystemExit(f"asset_id not found: {args.asset_id}")
    print(json.dumps({"asset_id": args.asset_id, "workspace_relative_path": asset.get("workspace_relative_path")}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import/list/validate workspace-local user assets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--workspace", required=True)
    import_parser.add_argument("--file", required=True)
    import_parser.add_argument("--type", required=True, choices=sorted(ASSET_TYPES))
    import_parser.add_argument("--asset-id", default=None)
    import_parser.add_argument("--license-status", default="user_responsibility")
    import_parser.set_defaults(func=command_import)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--workspace", required=True)
    list_parser.set_defaults(func=command_list)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--workspace", required=True)
    validate_parser.set_defaults(func=command_validate)

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("--workspace", required=True)
    resolve_parser.add_argument("--asset-id", required=True)
    resolve_parser.set_defaults(func=command_resolve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
