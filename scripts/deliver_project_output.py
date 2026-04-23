from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.reference_pipeline import load_json, utc_now, write_json

DEFAULT_POLICY_PATH = BASE_DIR / "config" / "output_delivery_policy.json"


def resolve_base_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (BASE_DIR / value).resolve()


def path_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def copy_project_bundle(source_root: Path, target_root: Path) -> list[str]:
    copied: list[str] = []
    if not source_root.exists():
        raise FileNotFoundError(source_root)
    for item in sorted(source_root.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(source_root)
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied.append(target.resolve().as_posix())
    return copied


def render_slack_message(template: str, *, deck_name: str, drive_link: str | None, delivery_manifest: str) -> str:
    template = template.replace("\\n", "\n")
    return template.format(
        deck_name=deck_name,
        drive_link=drive_link or "Google Drive Desktop sync; no public link opened",
        delivery_manifest=delivery_manifest,
    )


def delivery_status(
    *,
    drive_enabled: bool,
    drive_link: str | None,
    share_default: dict[str, Any],
    share_permission_confirmed: bool = False,
) -> str:
    if not drive_enabled:
        return "disabled_in_policy"
    if drive_link and share_permission_confirmed:
        return "share_ready"
    if drive_link and share_default.get("requires_google_drive_permission_update"):
        return "drive_link_recorded_permission_pending"
    if drive_link:
        return "drive_link_recorded"
    if share_default.get("requires_google_drive_permission_update"):
        return "pending_google_drive_permission_update"
    return "synced_to_drive_desktop"


def slack_status(
    *,
    slack_policy: dict[str, Any],
    drive_ready: bool,
    slack_destination: str | None,
    slack_sent: bool = False,
) -> str:
    if not slack_policy.get("enabled"):
        return "disabled_in_policy"
    if slack_sent:
        return "sent"
    if not slack_destination:
        return "pending_slack_destination"
    if not drive_ready:
        return "pending_drive_link"
    return "ready_for_connector_send"


def deliver_project_output(
    project_manifest_path: Path,
    *,
    policy_path: Path = DEFAULT_POLICY_PATH,
    drive_link: str | None = None,
    drive_file_id: str | None = None,
    share_permission_confirmed: bool = False,
    slack_destination: str | None = None,
    slack_sent: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    project_manifest = load_json(project_manifest_path)
    project_id = str(project_manifest.get("project_id") or project_manifest_path.parent.name)
    bundle = project_manifest.get("bundle", {})
    if not isinstance(bundle, dict):
        raise ValueError(f"Invalid project manifest bundle: {project_manifest_path}")

    project_root = resolve_base_path(str(bundle.get("project_root", project_manifest_path.parent.as_posix())))
    deck_path = resolve_base_path(str(bundle.get("deck_path", "")))
    if not deck_path.exists():
        raise FileNotFoundError(deck_path)

    drive_policy = policy.get("google_drive_desktop", {})
    slack_policy = policy.get("slack", {})
    reference_policy = policy.get("reference_learning_loop", {})
    if not isinstance(drive_policy, dict) or not isinstance(slack_policy, dict) or not isinstance(reference_policy, dict):
        raise ValueError("Delivery policy sections must be objects")

    drive_enabled = bool(policy.get("enabled") and drive_policy.get("enabled"))
    drive_workspace = Path(str(drive_policy.get("workspace_path", "")))
    project_subdir = str(drive_policy.get("project_subdir") or "projects")
    drive_project_root = drive_workspace / project_subdir / project_id
    drive_deck_path = drive_workspace / "decks" / deck_path.name

    copied_files: list[str] = []
    if drive_enabled:
        if not drive_workspace.exists():
            raise FileNotFoundError(drive_workspace)
        if not dry_run and bool(drive_policy.get("copy_project_bundle", True)):
            copied_files = copy_project_bundle(project_root, drive_project_root)
        if not dry_run and bool(drive_policy.get("copy_final_pptx_to_root_decks", True)):
            drive_deck_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(deck_path, drive_deck_path)

    manifest_path = project_root / "delivery_manifest.json"
    drive_manifest_path = drive_project_root / "delivery_manifest.json"
    slack_message_path = project_root / "slack_message.md"
    slack_destination = slack_destination or slack_policy.get("destination")
    slack_destination_value = str(slack_destination) if slack_destination else None

    slack_message = render_slack_message(
        str(slack_policy.get("message_template", "{drive_link}")),
        deck_name=deck_path.name,
        drive_link=drive_link,
        delivery_manifest=drive_manifest_path.resolve().as_posix(),
    )
    drive_status_value = delivery_status(
        drive_enabled=drive_enabled,
        drive_link=drive_link,
        share_default=drive_policy.get("share_default", {}),
        share_permission_confirmed=share_permission_confirmed,
    )
    drive_ready = drive_status_value in {
        "share_ready",
        "synced_to_drive_desktop",
        "drive_link_recorded",
        "drive_link_recorded_permission_pending",
    }

    manifest = {
        "schema_version": "1.0",
        "created_at": utc_now(),
        "project_id": project_id,
        "project_manifest_path": path_label(project_manifest_path),
        "local": {
            "project_root": path_label(project_root),
            "deck_path": path_label(deck_path),
            "delivery_manifest_path": path_label(manifest_path),
            "slack_message_path": path_label(slack_message_path),
        },
        "google_drive_desktop": {
            "enabled": drive_enabled,
            "workspace_path": drive_workspace.resolve().as_posix() if drive_workspace else None,
            "project_root": drive_project_root.resolve().as_posix(),
            "deck_path": drive_deck_path.resolve().as_posix(),
            "drive_file_id": drive_file_id,
            "drive_link": drive_link,
            "share_default": drive_policy.get("share_default", {}),
            "status": drive_status_value,
            "share_permission_confirmed": share_permission_confirmed,
            "copied_file_count": len(copied_files),
        },
        "slack": {
            "enabled": bool(slack_policy.get("enabled")),
            "destination": slack_destination_value,
            "send_mode": slack_policy.get("send_mode"),
            "status": slack_status(
                slack_policy=slack_policy,
                drive_ready=drive_ready,
                slack_destination=slack_destination_value,
                slack_sent=slack_sent,
            ),
            "sent_confirmed": slack_sent,
            "message_path": path_label(slack_message_path),
        },
        "reference_learning_loop": reference_policy,
        "reference_capture": project_manifest.get("reference_capture"),
        "dry_run": dry_run,
    }

    if not dry_run:
        write_json(manifest_path, manifest)
        slack_message_path.write_text(slack_message + "\n", encoding="utf-8")
        if drive_enabled:
            drive_project_root.mkdir(parents=True, exist_ok=True)
            write_json(drive_manifest_path, manifest)
            (drive_project_root / "slack_message.md").write_text(slack_message + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy a project-scoped PPT bundle into the configured delivery workspace.")
    parser.add_argument("project_manifest")
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH.as_posix())
    parser.add_argument("--drive-link", default=None)
    parser.add_argument("--drive-file-id", default=None)
    parser.add_argument("--share-permission-confirmed", action="store_true")
    parser.add_argument("--slack-destination", default=None)
    parser.add_argument("--slack-sent", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest = deliver_project_output(
        Path(args.project_manifest).resolve(),
        policy_path=Path(args.policy).resolve(),
        drive_link=args.drive_link,
        drive_file_id=args.drive_file_id,
        share_permission_confirmed=args.share_permission_confirmed,
        slack_destination=args.slack_destination,
        slack_sent=args.slack_sent,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
