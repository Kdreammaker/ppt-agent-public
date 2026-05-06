from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CONTRACT_ID = "ppt-maker.auto-output-intent-policy.v0"
OUTPUT_INTENTS = ("design_visual", "editable_office", "balanced")
CAPABILITY_KEYS = (
    "output_intent_bounded_effects",
    "approved_package_asset_insertion",
    "approved_structured_native_chart_table_rendering",
    "shared_ir_safe_area_native_chart_table_bounds",
    "b54_style_token_guidance",
)
ASSET_INTERPRETATION_KEYS = (
    "b53b_palette_seeds",
    "promotion_ready",
    "b54_style_tokens",
    "font_handoff",
    "insertable_assets",
)
BLOCKER_KEYS = (
    "shared_ir_layout_density_geometry_text_slot_asset_slot_consumption",
    "font_materialization_without_approved_opaque_package_evidence",
    "html_screenshots_inserted_into_pptx",
    "public_exposure_of_package_internals_or_private_ids",
)
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
    re.compile(r"\bslot_id\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bxox(?:[abprs]|c|d)-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:drive|docs)\.google\.com\b", re.IGNORECASE),
)
PACKAGE_INTERNAL_PATTERNS = (
    re.compile(r"\bpackage_manifest_id\b", re.IGNORECASE),
    re.compile(r"\bstructured_data_id\b", re.IGNORECASE),
    re.compile(r"\bpackage[-_: ]manifest[-_: ][A-Za-z0-9_.:-]+\b", re.IGNORECASE),
    re.compile(r"\bstructured[-_: ]data[-_: ][A-Za-z0-9_.:-]+\b", re.IGNORECASE),
    re.compile(r"\bpackage manifest\b", re.IGNORECASE),
    re.compile(r"\binternal package\b", re.IGNORECASE),
    re.compile(r"\braw manifest\b", re.IGNORECASE),
    re.compile(r"\braw package\b", re.IGNORECASE),
    re.compile(r"\braw structured[-_ ]data\b", re.IGNORECASE),
)
SAFE_TEXT = re.compile(r"^[A-Za-z0-9_ .:/,-]{1,160}$")


class PublicAutoCapabilityMetadataError(ValueError):
    """Raised when Auto capability metadata cannot be safely exposed."""


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
    hits = [pattern.pattern for pattern in (*PRIVATE_PATTERNS, *PACKAGE_INTERNAL_PATTERNS) if pattern.search(raw)]
    if hits:
        raise PublicAutoCapabilityMetadataError(f"{source} contains private or sensitive marker patterns: {hits}")


def unavailable_auto_capability_metadata(reason: str = "auto_capability_metadata_not_available") -> dict[str, Any]:
    return {
        "auto_capability_metadata_enabled": False,
        "status": "not_available",
        "reason": reason,
        "metadata_only": True,
        "renderer_behavior": "unchanged",
        "auto_policy_redesign_enabled": False,
        "selected_output_intent": None,
        "two_variant_policy_status": "not_available",
        "two_variant_policy": {
            "variant_count": 0,
            "redesign_enabled": False,
            "variants_receive_same_output_intent": False,
            "selection_policy": "not_available",
        },
        "bounded_renderer_capabilities": {key: "not_available" for key in CAPABILITY_KEYS},
        "native_chart_table_supported_candidate_counts": {},
        "b54_and_font_status": {
            "b54_style_token_guidance": "not_available",
            "font_materialization": "blocked_without_approved_opaque_package_evidence",
        },
        "asset_system_interpretation": {
            "b53b_palette_seeds": "candidate_reference_only",
            "promotion_ready": "proposal_eligible_only",
            "b54_style_tokens": "metadata_recipe_guidance_only",
            "font_handoff": "metadata_only_without_approved_opaque_package",
            "insertable_assets": "approved_package_handoffs_only",
        },
        "public_safe_blocker_categories": [],
        "public_private_hygiene": {
            "tokens_included": False,
            "private_paths_included": False,
            "drive_or_docs_urls_included": False,
            "private_identifiers_included": False,
            "raw_payloads_included": False,
            "package_internals_included": False,
        },
    }


def safe_string(value: Any, *, fallback: str = "not_available") -> str:
    if not isinstance(value, str) or not value:
        return fallback
    if any(pattern.search(value) for pattern in (*PRIVATE_PATTERNS, *PACKAGE_INTERNAL_PATTERNS)):
        return fallback
    if not SAFE_TEXT.fullmatch(value):
        return fallback
    return value


def safe_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def safe_count(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def policy_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    policy = payload.get("auto_output_intent_policy")
    if isinstance(policy, dict):
        return policy
    return payload


def safe_capabilities(policy: dict[str, Any]) -> dict[str, str]:
    raw = policy.get("renderer_capabilities") if isinstance(policy.get("renderer_capabilities"), dict) else {}
    exposed: dict[str, str] = {}
    for key in CAPABILITY_KEYS:
        exposed[key] = safe_string(raw.get(key), fallback="not_available")
    return exposed


def safe_native_counts(policy: dict[str, Any]) -> dict[str, dict[str, int]]:
    raw = policy.get("variant_native_chart_table_counts")
    if not isinstance(raw, dict):
        return {}
    exposed: dict[str, dict[str, int]] = {}
    for variant in ("variant_a", "variant_b"):
        counts = raw.get(variant)
        if isinstance(counts, dict):
            exposed[variant] = {
                "supported_candidate_count": safe_count(counts.get("supported_candidate_count")),
                "blocked_candidate_count": safe_count(counts.get("blocked_candidate_count")),
            }
    return exposed


def safe_b54_status(policy: dict[str, Any]) -> dict[str, Any]:
    raw = policy.get("variant_b54_status")
    variants: dict[str, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for variant in ("variant_a", "variant_b"):
            status = raw.get(variant)
            if isinstance(status, dict):
                variants[variant] = {
                    "status": safe_string(status.get("status")),
                    "font_materialization_enabled": safe_bool(status.get("font_materialization_enabled")),
                }
    return {
        "b54_style_token_guidance": "metadata_recipe_guidance_only",
        "font_materialization": "blocked_without_approved_opaque_package_evidence",
        "variant_status": variants,
    }


def safe_asset_interpretation(policy: dict[str, Any]) -> dict[str, str]:
    raw = policy.get("asset_system_interpretation")
    defaults = unavailable_auto_capability_metadata()["asset_system_interpretation"]
    if not isinstance(raw, dict):
        return defaults
    return {key: safe_string(raw.get(key), fallback=defaults[key]) for key in ASSET_INTERPRETATION_KEYS}


def safe_blocker_categories(policy: dict[str, Any]) -> list[str]:
    raw = policy.get("blocked_behavior")
    if not isinstance(raw, dict):
        return []
    categories = [key for key in BLOCKER_KEYS if raw.get(key) is True]
    if any(
        key not in BLOCKER_KEYS
        and any(pattern.search(str(key)) for pattern in (*PRIVATE_PATTERNS, *PACKAGE_INTERNAL_PATTERNS))
        for key in raw
    ):
        categories.append("sensitive_blocker_category_redacted")
    return categories


def expose_auto_capability_metadata(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return unavailable_auto_capability_metadata()
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise PublicAutoCapabilityMetadataError(f"{path} must contain a JSON object")
    policy = policy_from_payload(payload)
    if policy.get("contract") != CONTRACT_ID:
        raise PublicAutoCapabilityMetadataError(f"{path} Auto capability contract mismatch")
    if policy.get("status") != "ready_for_public_beta_metadata":
        raise PublicAutoCapabilityMetadataError(f"{path} Auto capability status is not ready")
    selected = policy.get("selected_output_intent")
    if selected not in OUTPUT_INTENTS:
        raise PublicAutoCapabilityMetadataError(f"{path} selected output intent is invalid")
    two_variant = policy.get("two_variant_policy") if isinstance(policy.get("two_variant_policy"), dict) else {}
    variant_count = safe_count(two_variant.get("variant_count"))
    redesign_enabled = safe_bool(two_variant.get("redesign_enabled"))
    same_intent = safe_bool(two_variant.get("variants_receive_same_output_intent"))
    exposed = {
        "auto_capability_metadata_enabled": True,
        "status": "available",
        "metadata_only": True,
        "renderer_behavior": "unchanged",
        "auto_policy_redesign_enabled": False,
        "selected_output_intent": selected,
        "two_variant_policy_status": "current_two_variant_policy"
        if variant_count == 2 and not redesign_enabled and same_intent
        else "blocked_or_unknown",
        "two_variant_policy": {
            "variant_count": variant_count,
            "redesign_enabled": False,
            "variants_receive_same_output_intent": same_intent,
            "selection_policy": safe_string(two_variant.get("selection_policy")),
        },
        "bounded_renderer_capabilities": safe_capabilities(policy),
        "native_chart_table_supported_candidate_counts": safe_native_counts(policy),
        "b54_and_font_status": safe_b54_status(policy),
        "asset_system_interpretation": safe_asset_interpretation(policy),
        "public_safe_blocker_categories": safe_blocker_categories(policy),
        "public_private_hygiene": unavailable_auto_capability_metadata()["public_private_hygiene"],
    }
    public_safe(exposed, source=path.as_posix())
    return exposed
