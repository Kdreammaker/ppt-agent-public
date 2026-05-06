from __future__ import annotations

import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
LOCAL_PATH_REDACTION = "[local-path-redacted]"

PRIVATE_MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    "windows_absolute_path": re.compile(r"[A-Za-z]:[\\/][^\s\"'`|<>]*"),
    "mac_home_path": re.compile(r"/Users/[^\s\"'`|<>]*"),
    "linux_home_path": re.compile(r"/home/[^\s\"'`|<>]*"),
    "drive_docs_url": re.compile(r"\b(?:drive|docs)\.google\.com\b", re.IGNORECASE),
    "drive_id_marker": re.compile(r"\bdrive[_-]?id\b", re.IGNORECASE),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    "slack_token": re.compile(r"\bxox(?:[abprs]|c|d)-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
    "google_api_key": re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    "raw_payload_marker": re.compile(r"\braw_payload\b", re.IGNORECASE),
    "private_prompt_marker": re.compile(r"\bprivate_prompt\b", re.IGNORECASE),
    "source_attachment_marker": re.compile(r"\bsource_attachment\b", re.IGNORECASE),
    "slot_id_marker": re.compile(r"\bslot_id\b", re.IGNORECASE),
    "slot_name_marker": re.compile(r"\bslot_name\b", re.IGNORECASE),
    "package_manifest_id_marker": re.compile(r"\bpackage_manifest_id\b", re.IGNORECASE),
    "structured_data_id_marker": re.compile(r"\bstructured_data_id\b", re.IGNORECASE),
    "package_internal_marker": re.compile(
        r"\bpackage[-_: ]manifest[-_: ][A-Za-z0-9_.:-]+\b|"
        r"\bstructured[-_: ]data[-_: ][A-Za-z0-9_.:-]+\b|"
        r"\bpackage manifest\b|"
        r"\binternal package\b|"
        r"\braw manifest\b|"
        r"\braw package\b|"
        r"\braw structured[-_ ]data\b",
        re.IGNORECASE,
    ),
}


def artifact_ref(path: Path | None, *, workspace: Path | None = None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    if workspace is not None:
        try:
            return resolved.relative_to(workspace.resolve()).as_posix()
        except ValueError:
            pass
    try:
        return f"repo:{resolved.relative_to(BASE_DIR.resolve()).as_posix()}"
    except ValueError:
        return f"local-artifact:{resolved.name}"


def _replace_absolute_path(match: re.Match[str], workspace: Path | None) -> str:
    raw = match.group(0)
    try:
        return artifact_ref(Path(raw), workspace=workspace) or LOCAL_PATH_REDACTION
    except (OSError, ValueError):
        return LOCAL_PATH_REDACTION


def sanitize_public_string(value: str, *, workspace: Path | None = None) -> str:
    text = value
    for pattern_name in ("windows_absolute_path", "mac_home_path", "linux_home_path"):
        text = PRIVATE_MARKER_PATTERNS[pattern_name].sub(
            lambda match: _replace_absolute_path(match, workspace),
            text,
        )
    text = re.sub(r"\bhttps?://(?:drive|docs)\.google\.com/[^\s\"'`|<>]+", "[google-drive-url-redacted]", text, flags=re.IGNORECASE)
    text = PRIVATE_MARKER_PATTERNS["openai_key"].sub("[token-redacted]", text)
    text = PRIVATE_MARKER_PATTERNS["slack_token"].sub("[token-redacted]", text)
    text = PRIVATE_MARKER_PATTERNS["google_api_key"].sub("[token-redacted]", text)
    for pattern_name in (
        "raw_payload_marker",
        "private_prompt_marker",
        "source_attachment_marker",
        "package_manifest_id_marker",
        "structured_data_id_marker",
        "package_internal_marker",
    ):
        text = PRIVATE_MARKER_PATTERNS[pattern_name].sub("[private-marker-redacted]", text)
    text = PRIVATE_MARKER_PATTERNS["slot_id_marker"].sub("slot_ref", text)
    text = PRIVATE_MARKER_PATTERNS["slot_name_marker"].sub("slot_ref", text)
    return text


def sanitize_public_report(value: Any, *, workspace: Path | None = None) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize_public_report(item, workspace=workspace)
            for key, item in value.items()
            if key
            not in {
                "absolute_paths",
                "raw_payload",
                "private_prompt",
                "source_attachment",
                "slot_id",
                "slot_name",
                "package_manifest_id",
                "structured_data_id",
            }
        }
    if isinstance(value, list):
        return [sanitize_public_report(item, workspace=workspace) for item in value]
    if isinstance(value, Path):
        return artifact_ref(value, workspace=workspace)
    if isinstance(value, str):
        return sanitize_public_string(value, workspace=workspace)
    return value


def public_report_issues(text: str) -> list[str]:
    return [name for name, pattern in PRIVATE_MARKER_PATTERNS.items() if pattern.search(text)]
