from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CONTRACT_ID = "ppt-maker.b49-asset-request-summary.v0"
ASSET_STATES = ("approved", "requested", "unknown")
ALLOWED_ITEM_FIELDS = (
    "request_id",
    "slide_no",
    "state",
    "asset_type",
    "required",
    "user_action",
    "user_message",
    "public_safe_reason",
)
EXPECTED_ACTIONS_BY_STATE = {
    "approved": {"no_user_action_needed"},
    "requested": {"upload_or_select_required_asset", "upload_or_select_recommended_asset"},
    "unknown": {"clarify_asset_need"},
}
PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/Users/"),
    re.compile(r"/home/"),
    re.compile(r"\bdrive[_-]?id\b", re.IGNORECASE),
    re.compile(r"\bsource_attachment\b", re.IGNORECASE),
    re.compile(r"\braw_payload\b", re.IGNORECASE),
    re.compile(r"\bprivate_prompt\b", re.IGNORECASE),
    re.compile(r"\baccess_token\b", re.IGNORECASE),
    re.compile(r"\brefresh_token\b", re.IGNORECASE),
    re.compile(r"\bapproved_asset_ref\b", re.IGNORECASE),
    re.compile(r"\bpreferred_asset_ref\b", re.IGNORECASE),
    re.compile(r"\bunapproved_asset_records\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bxox(?:[abprs]|c|d)-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:drive|docs)\.google\.com\b", re.IGNORECASE),
)


class PublicB49AssetRequestError(ValueError):
    """Raised when a B49 summary cannot be safely exposed in public reports."""


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()


def first_existing_path(*candidates: Path | None) -> Path | None:
    for path in candidates:
        if path and path.exists():
            return path.resolve()
    return None


def public_safe(payload: dict[str, Any], *, source: str) -> None:
    raw = json.dumps(payload, ensure_ascii=False)
    hits = [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(raw)]
    if hits:
        raise PublicB49AssetRequestError(f"{source} contains private or sensitive marker patterns: {hits}")


def unavailable_asset_request_summary(reason: str = "b49_asset_request_summary_not_available") -> dict[str, Any]:
    return {
        "b49_asset_request_ux_enabled": False,
        "status": "not_available",
        "reason": reason,
        "summary": {"approved": 0, "requested": 0, "unknown": 0, "total_request_items": 0},
        "asset_request_actions": {},
        "asset_request_items": [],
        "metadata_only": True,
        "renderer_behavior": "unchanged",
        "asset_insertion_behavior": "unchanged",
        "public_private_hygiene": {
            "raw_asset_refs_included": False,
            "slot_ids_included": False,
            "private_paths_included": False,
            "drive_or_docs_urls_included": False,
            "tokens_included": False,
            "private_prompts_included": False,
            "raw_payloads_included": False,
            "source_attachment_paths_included": False,
            "unapproved_asset_records_included": False,
        },
    }


def safe_item(raw_item: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(raw_item, dict):
        raise PublicB49AssetRequestError(f"B49 request item {index} must be an object")
    item = {field: raw_item.get(field) for field in ALLOWED_ITEM_FIELDS if field in raw_item}
    state = item.get("state")
    if state not in ASSET_STATES:
        raise PublicB49AssetRequestError(f"B49 request item {index} has invalid state {state!r}")
    action = item.get("user_action")
    if action not in EXPECTED_ACTIONS_BY_STATE[state]:
        raise PublicB49AssetRequestError(f"B49 request item {index} has invalid action {action!r} for state {state!r}")
    if not isinstance(item.get("request_id"), str) or not item["request_id"]:
        raise PublicB49AssetRequestError(f"B49 request item {index} is missing request_id")
    if "slide_no" in item and item["slide_no"] is not None and not isinstance(item["slide_no"], int):
        raise PublicB49AssetRequestError(f"B49 request item {index} slide_no must be an integer or null")
    if "required" in item and not isinstance(item["required"], bool):
        item["required"] = bool(item["required"])
    for field in ("asset_type", "user_message", "public_safe_reason"):
        if not isinstance(item.get(field), str) or not item[field]:
            raise PublicB49AssetRequestError(f"B49 request item {index} is missing {field}")
    public_safe(item, source=f"B49 request item {index}")
    return item


def expose_b49_asset_request_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return unavailable_asset_request_summary()
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise PublicB49AssetRequestError(f"{path} must contain a JSON object")
    if payload.get("contract") != CONTRACT_ID:
        raise PublicB49AssetRequestError(f"{path} contract mismatch")
    items = [safe_item(item, index=index) for index, item in enumerate(payload.get("request_items", []), start=1)]
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    counts = {
        state: summary.get(state) if isinstance(summary.get(state), int) and summary.get(state) >= 0 else 0
        for state in ASSET_STATES
    }
    if sum(counts.values()) != len(items):
        counts = {state: sum(1 for item in items if item["state"] == state) for state in ASSET_STATES}
    action_counts: dict[str, int] = {}
    for item in items:
        action = str(item["user_action"])
        action_counts[action] = action_counts.get(action, 0) + 1
    exposed = {
        "b49_asset_request_ux_enabled": True,
        "status": "available",
        "summary": {**counts, "total_request_items": len(items)},
        "asset_request_actions": action_counts,
        "asset_request_items": items,
        "metadata_only": True,
        "renderer_behavior": "unchanged",
        "asset_insertion_behavior": "unchanged",
        "public_private_hygiene": unavailable_asset_request_summary()["public_private_hygiene"],
    }
    public_safe(exposed, source=path.as_posix())
    return exposed
