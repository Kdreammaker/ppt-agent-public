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

from scripts.reference_pipeline import load_json, utc_now, write_json

DEFAULT_POLICY_PATH = BASE_DIR / "config" / "output_delivery_policy.json"


def resolve_base_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (BASE_DIR / value).resolve()


def bridge_script_from_policy(policy: dict[str, Any], override: str | None = None) -> Path:
    if override:
        return Path(override).resolve()
    slack = policy.get("slack", {})
    if not isinstance(slack, dict):
        raise ValueError("Delivery policy slack section must be an object")
    script = slack.get("bridge_script")
    if not isinstance(script, str) or not script:
        raise ValueError("Delivery policy slack.bridge_script is required for host_main_bridge sends")
    return Path(script).resolve()


def parse_bridge_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        raise ValueError("Slack bridge returned no JSON output")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.rfind("{")
        if start < 0:
            raise
        return json.loads(text[start:])


def update_manifest_slack_state(manifest_path: Path, bridge_result: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    slack = manifest.get("slack")
    if not isinstance(slack, dict):
        raise ValueError(f"delivery manifest slack section must be an object: {manifest_path}")
    ok = bool(bridge_result.get("ok"))
    slack["status"] = "sent" if ok else "ready_for_connector_send"
    slack["sent_confirmed"] = ok
    slack["message_ts"] = str(bridge_result.get("slackTs") or "") or None
    slack["permalink"] = bridge_result.get("permalink")
    slack["sent_at"] = utc_now() if ok else None
    slack["send_evidence_path"] = bridge_result.get("evidencePath")
    slack["send_error"] = str(bridge_result.get("error") or "") or None
    write_json(manifest_path, manifest)
    return manifest


def mirrored_manifest_path(manifest: dict[str, Any]) -> Path | None:
    drive = manifest.get("google_drive_desktop")
    if not isinstance(drive, dict) or not drive.get("enabled"):
        return None
    project_root = drive.get("project_root")
    if not isinstance(project_root, str) or not project_root:
        return None
    path = Path(project_root) / "delivery_manifest.json"
    return path if path.exists() else None


def send_delivery_slack_message(
    manifest_path: Path,
    *,
    policy_path: Path = DEFAULT_POLICY_PATH,
    bridge_script: str | None = None,
    request_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    policy = load_json(policy_path)
    slack = manifest.get("slack", {})
    if not isinstance(slack, dict):
        raise ValueError("delivery manifest slack section must be an object")
    if not slack.get("enabled"):
        raise ValueError("Slack delivery is disabled in the manifest")
    message_path = resolve_base_path(str(slack.get("message_path", "")))
    if not message_path.exists():
        raise FileNotFoundError(message_path)
    destination = slack.get("destination")
    if not isinstance(destination, str) or not destination:
        raise ValueError("Slack destination is required before sending")

    script = bridge_script_from_policy(policy, bridge_script)
    if not script.exists():
        raise FileNotFoundError(script)
    request_id_value = request_id or f"{manifest.get('project_id', 'project')}-delivery-slack"
    command = [
        "node",
        script.as_posix(),
        "--workspace",
        BASE_DIR.as_posix(),
        "--channel",
        destination,
        "--text-file",
        message_path.as_posix(),
        "--request-id",
        request_id_value,
    ]
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "operation": "send_delivery_slack_message",
            "command": command,
            "manifest_path": manifest_path.as_posix(),
            "message_path": message_path.as_posix(),
        }

    completed = subprocess.run(
        command,
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    bridge_result = parse_bridge_stdout(completed.stdout)
    if completed.returncode != 0 or not bridge_result.get("ok"):
        update_manifest_slack_state(manifest_path, bridge_result)
        raise RuntimeError(f"Slack bridge send failed: {bridge_result.get('error') or completed.stderr}")

    updated_manifest = update_manifest_slack_state(manifest_path, bridge_result)
    mirror_path = mirrored_manifest_path(updated_manifest)
    if mirror_path is not None and mirror_path.resolve() != manifest_path.resolve():
        update_manifest_slack_state(mirror_path, bridge_result)

    return {
        "ok": True,
        "operation": "send_delivery_slack_message",
        "manifest_path": manifest_path.as_posix(),
        "message_path": message_path.as_posix(),
        "slack_ts": bridge_result.get("slackTs"),
        "evidence_path": bridge_result.get("evidencePath"),
        "mirrored_manifest_path": mirror_path.as_posix() if mirror_path else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a delivery manifest's Slack message through the host-main bridge.")
    parser.add_argument("delivery_manifest")
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH.as_posix())
    parser.add_argument("--bridge-script", default=None)
    parser.add_argument("--request-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    result = send_delivery_slack_message(
        Path(args.delivery_manifest).resolve(),
        policy_path=Path(args.policy).resolve(),
        bridge_script=args.bridge_script,
        request_id=args.request_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
