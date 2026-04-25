from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.deck_models import validate_deck_spec
from system.intake_models import DeckIntake, validate_deck_intake
from system.template_engine import slot_text_budget, text_budget_units, truncate_text_to_budget_units

DEFAULT_THEME_PATH = BASE_DIR / "config" / "pptx_theme.example.json"
DEFAULT_REFERENCE_CATALOG_PATH = BASE_DIR / "config" / "reference_catalog.json"
DEFAULT_BLUEPRINT_PATH = BASE_DIR / "config" / "template_blueprints.json"
DEFAULT_FEEDBACK_MEMORY_PATH = BASE_DIR / "config" / "slide_feedback_memory.json"
DEFAULT_ASSET_CATALOG_PATH = BASE_DIR / "config" / "ppt_asset_catalog.json"
INDUSTRY_STORYLINE_TAXONOMY_PATH = BASE_DIR / "config" / "industry_storyline_taxonomy.json"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
EDITORIAL_TEMPLATE_SEQUENCE = [
    "cover_brand_right_v1",
    "toc_visual_tiles_v1",
    "summary_two_panel_v1",
    "proposal_grid_4up_v1",
    "issue_2x2_v1",
    "proposal_grid_4up_v1",
    "summary_two_panel_v1",
    "goal_grid_v1",
]
BUSINESS_TEMPLATE_KEY_TERMS = ("financial", "funding", "market_", "competition", "tam_sam_som")
CONSUMER_INAPPROPRIATE_TEMPLATE_KEY_TERMS = (
    *BUSINESS_TEMPLATE_KEY_TERMS,
    "project_case",
    "improvement_case",
    "core_technology",
    "roi_",
    "alpha_signal",
    "finance_",
    "problem_story",
    "proof_metrics",
    "poc_process",
)
BUSINESS_RESIDUAL_TEXT_PATTERNS = [
    "Market | Customer Analysis",
    "Financial | Funding History",
    "Customer Analysis",
    "Funding History",
]
ASSET_PROFILE_DEFAULTS = {
    "business": {
        "theme": "theme.neutral_modern_report",
        "palette": "palette.neutral_modern_report",
        "typography": "typography.neutral_modern_report.malgun_gothic",
        "icon_terms": ["presentation_analytics", "bar_chart", "file_line_chart", "dashboard_monitoring"],
    },
    "travel": {
        "theme": "theme.blue_green_report",
        "palette": "palette.blue_green_report",
        "typography": "typography.blue_green_report.malgun_gothic",
        "icon_terms": ["calendar_event", "home", "user", "check"],
    },
    "technology": {
        "theme": "theme.neutral_modern_report",
        "palette": "palette.neutral_modern_report",
        "typography": "typography.neutral_modern_report.malgun_gothic",
        "icon_terms": ["cloud_computing", "database", "code", "network"],
    },
    "finance": {
        "theme": "theme.neutral_modern_report",
        "palette": "palette.neutral_modern_report",
        "typography": "typography.neutral_modern_report.malgun_gothic",
        "icon_terms": ["bar_chart", "file_line_chart", "presentation_analytics"],
    },
    "other": {
        "theme": "theme.blue_green_report",
        "palette": "palette.blue_green_report",
        "typography": "typography.blue_green_report.malgun_gothic",
        "icon_terms": ["check", "settings", "presentation_analytics"],
    },
}
CHART_PRESET_ASSET_ID = "chart_preset.simple_bar_chart"
IMAGE_POLICY_ASSET_ID = "image_policy.user_supplied_or_generated"

PURPOSE_SEQUENCE_BY_TYPE = {
    "sales": ["cover", "toc", "issue", "summary", "process", "chart", "closing"],
    "portfolio": ["cover", "toc", "team", "analysis", "analysis", "summary", "closing"],
    "strategy": ["cover", "toc", "summary", "issue", "strategy", "process", "chart", "closing"],
    "proposal": ["cover", "toc", "issue", "strategy", "process", "summary", "closing"],
    "analysis": ["cover", "toc", "summary", "analysis", "chart", "strategy", "closing"],
    "report": ["cover", "toc", "summary", "market", "analysis", "chart", "closing"],
    "status_update": ["cover", "toc", "summary", "timeline", "issue", "closing"],
    "training": ["cover", "toc", "summary", "process", "analysis", "closing"],
    "other": ["cover", "toc", "summary", "analysis", "strategy", "closing"],
}


def load_industry_taxonomy(path: Path = INDUSTRY_STORYLINE_TAXONOMY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"default_industry": "other", "industries": {"other": {}}}
    return load_json(path)


def industry_profile(intake: DeckIntake, taxonomy: dict[str, Any] | None = None) -> dict[str, Any]:
    taxonomy = taxonomy or load_industry_taxonomy()
    industries = taxonomy.get("industries", {})
    key = getattr(intake.industry, "value", str(intake.industry))
    default_key = taxonomy.get("default_industry", "other")
    profile = industries.get(key) or industries.get(default_key) or {}
    return {"industry": key if key in industries else default_key, **profile}


class IncludeItem:
    def __init__(self, raw: str) -> None:
        self.raw = raw.strip()
        self.title, self.detail = split_include_item(self.raw)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_asset_catalog(path: Path = DEFAULT_ASSET_CATALOG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"assets": []}
    return load_json(path)


def eligible_assets_by_id(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(asset["asset_id"]): asset
        for asset in catalog.get("assets", [])
        if isinstance(asset, dict)
        and isinstance(asset.get("asset_id"), str)
        and asset.get("production_eligible") is True
        and asset.get("allowed_for_ppt") is True
    }


def asset_source_policy(asset: dict[str, Any]) -> str:
    if asset.get("asset_id") == IMAGE_POLICY_ASSET_ID:
        return "local_user_asset_policy"
    if asset.get("source_type") == "external_registry_reference":
        return "external_registry_reference"
    return "finalized_catalog"


def asset_materialization(asset: dict[str, Any]) -> str:
    source_type = asset.get("source_type")
    if asset.get("asset_id") == IMAGE_POLICY_ASSET_ID:
        return "runtime_materialization_required"
    if source_type == "local_config":
        return "local_config_reference"
    if source_type == "local_code":
        return "local_code_reference"
    return "metadata_only"


def asset_intent_record(
    asset: dict[str, Any],
    *,
    role: str,
    industry: str,
    tone: list[str],
    purpose: str | None,
    query: dict[str, Any],
    slide_number: int | None = None,
    slot: str | None = None,
    candidate_asset_ids: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    intent = {
        "role": role,
        "asset_class": asset["asset_class"],
        "asset_id": asset["asset_id"],
        "slide_number": slide_number,
        "slot": slot,
        "purpose": purpose,
        "industry": industry,
        "tone": tone,
        "aspect_ratio": "16:9",
        "query": query,
        "source_policy": asset_source_policy(asset),
        "materialization": asset_materialization(asset),
        "license_action": str(asset.get("license_action") or "none"),
        "risk_level": str(asset.get("risk_level") or "unknown"),
        "candidate_asset_ids": candidate_asset_ids or [],
        "notes": notes,
    }
    semantic_context = asset.get("semantic_context")
    if isinstance(semantic_context, dict) and semantic_context:
        intent["semantic_context"] = semantic_context
    template_media_policy = asset.get("template_media_policy")
    if isinstance(template_media_policy, dict) and template_media_policy:
        intent["template_media_policy"] = template_media_policy
    return intent


def first_asset_by_terms(
    assets: dict[str, dict[str, Any]],
    *,
    asset_class: str,
    terms: list[str],
) -> dict[str, Any] | None:
    class_assets = [
        asset
        for asset in assets.values()
        if asset.get("asset_class") == asset_class
        and asset.get("risk_level") in {"low", "medium"}
        and str(asset.get("license_action") or "none") in {"none", "check-source-policy", "check-license-file"}
    ]
    for term in terms:
        needle = term.lower()
        for asset in class_assets:
            searchable = " ".join(
                [
                    str(asset.get("asset_id", "")),
                    str(asset.get("external_asset_name", "")),
                    " ".join(str(tag) for tag in asset.get("style_tags", [])),
                ]
            ).lower()
            if needle in searchable:
                return asset
    return class_assets[0] if class_assets else None


def asset_intents_for_spec(
    intake: DeckIntake,
    *,
    purposes: list[str],
    slides: list[dict[str, Any]],
    blueprints_by_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    catalog = load_asset_catalog()
    assets = eligible_assets_by_id(catalog)
    profile = industry_profile(intake)
    industry = str(profile.get("industry") or "other")
    asset_profile = ASSET_PROFILE_DEFAULTS.get(industry, ASSET_PROFILE_DEFAULTS["other"])
    tone = [item.value for item in intake.tone]
    intents: list[dict[str, Any]] = []

    for role, asset_id in (
        ("theme", asset_profile["theme"]),
        ("palette", asset_profile["palette"]),
        ("typography", asset_profile["typography"]),
        ("chart_preset", CHART_PRESET_ASSET_ID),
    ):
        asset = assets.get(str(asset_id))
        if asset:
            intents.append(
                asset_intent_record(
                    asset,
                    role=role,
                    industry=industry,
                    tone=tone,
                    purpose=None,
                    query={
                        "industry": industry,
                        "tone": tone,
                        "slot_kind": role,
                        "aspect_ratio": "16:9",
                        "source_policy": "production_eligible_catalog_only",
                    },
                    notes="Composer-level recommendation; no binary asset is copied by this step.",
                )
            )

    image_policy = assets.get(IMAGE_POLICY_ASSET_ID)
    icon_candidates: list[str] = []
    icon_asset = first_asset_by_terms(assets, asset_class="icon", terms=list(asset_profile.get("icon_terms", [])))
    if icon_asset:
        icon_candidates = [
            asset_id
            for asset_id, asset in assets.items()
            if asset.get("asset_class") == "icon"
            and any(term.lower() in asset_id.lower() for term in asset_profile.get("icon_terms", []))
        ][:5]

    for slide_number, slide in enumerate(slides, start=1):
        purpose = purposes[slide_number - 1] if slide_number <= len(purposes) else None
        template_key = slide.get("template_key")
        blueprint = blueprints_by_key.get(str(template_key)) if template_key else None
        image_slots = list((blueprint or {}).get("editable_image_slots", []))
        if image_policy and image_slots and not slide.get("image_slots"):
            slot_name = str(image_slots[0].get("slot") or "image_1")
            intents.append(
                asset_intent_record(
                    image_policy,
                    role="image_placeholder",
                    industry=industry,
                    tone=tone,
                    purpose=purpose,
                    slide_number=slide_number,
                    slot=slot_name,
                    query={
                        "industry": industry,
                        "tone": tone,
                        "purpose": purpose,
                        "slot_kind": "image",
                        "aspect_ratio": "16:9",
                        "license_policy": "user_supplied_or_generated_only",
                        "source_policy": "no_raw_folder_scan",
                    },
                    notes="Image slot intent only; materialization is a later consented step.",
                )
            )
        if icon_asset and slide_number in {2, 3, 4}:
            intents.append(
                asset_intent_record(
                    icon_asset,
                    role="icon",
                    industry=industry,
                    tone=tone,
                    purpose=purpose,
                    slide_number=slide_number,
                    query={
                        "industry": industry,
                        "tone": tone,
                        "purpose": purpose,
                        "slot_kind": "icon",
                        "aspect_ratio": "16:9",
                        "source_policy": "external_registry_metadata_only",
                    },
                    candidate_asset_ids=icon_candidates,
                    notes="Icon recommendation metadata only; B31 does not materialize external registry files.",
                )
            )
    return intents


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "deck"


def resolve_from(base_dir: Path, value: str | None, default: Path | None = None) -> Path:
    if value:
        path = Path(value)
        return path if path.is_absolute() else (base_dir / path).resolve()
    if default is None:
        raise ValueError("Missing required path")
    return default.resolve()


def spec_path_ref(target: Path, spec_dir: Path) -> str:
    return Path(os.path.relpath(target.resolve(), spec_dir.resolve())).as_posix()


def split_include_item(value: str) -> tuple[str, str | None]:
    text = " ".join(value.strip().split())
    for separator in (" — ", " – ", " - ", ": "):
        if separator in text:
            title, detail = text.split(separator, 1)
            title = title.strip()
            detail = detail.strip()
            if title and detail:
                return title, detail
    return text, None


def include_items(intake: DeckIntake) -> list[IncludeItem]:
    return [IncludeItem(item) for item in intake.must_include]


def locale_is_korean(intake: DeckIntake) -> bool:
    locale = (intake.presentation_context.locale or "").lower()
    return locale.startswith("ko")


def is_editorial_consumer_deck(intake: DeckIntake) -> bool:
    tone = {item.value for item in intake.tone}
    setting = intake.presentation_context.setting.lower()
    audience = intake.audience.primary.lower()
    notes = (intake.brand_or_template_scope.notes or "").lower()
    if "allow_business_templates" in notes:
        return False
    if intake.industry.value == "food_and_beverage" and "visual" in tone:
        return True
    if {"friendly", "visual"} & tone and intake.audience.decision_role.value == "learner":
        return True
    return any(token in setting or token in audience for token in ("editorial", "guide", "food", "cook", "consumer"))


def mode_policy_for_intake(intake: DeckIntake) -> str:
    approval_mode = intake.review_requirements.approval_mode.value
    if approval_mode != "none" or intake.variation_level.value != "single_path":
        return "assistant"
    return "auto"


def desired_slide_count(intake: DeckIntake) -> int:
    minimum = intake.slide_count_range.min
    maximum = intake.slide_count_range.max
    preferred_count = len(intake.brand_or_template_scope.preferred_template_keys)
    if preferred_count:
        return min(maximum, max(minimum, preferred_count))
    content_driven = len(intake.must_include) + 2
    return min(maximum, max(minimum, content_driven))


def purpose_sequence(intake: DeckIntake, count: int, profile: dict[str, Any] | None = None) -> list[str]:
    profile_sequence = list((profile or {}).get("purpose_sequence") or [])
    base = profile_sequence or list(PURPOSE_SEQUENCE_BY_TYPE.get(intake.deck_type.value, PURPOSE_SEQUENCE_BY_TYPE["other"]))
    if count <= len(base):
        return base[: count - 1] + ["closing"] if base[count - 1] != "closing" else base[:count]
    while len(base) < count - 1:
        base.insert(-1, "analysis")
    return base[: count - 1] + ["closing"]


def preferred_template_keys(intake: DeckIntake, count: int, profile: dict[str, Any] | None = None) -> list[str]:
    preferred = list(intake.brand_or_template_scope.preferred_template_keys)
    if not preferred:
        preferred = list((profile or {}).get("template_sequence") or [])[:count]
    if not is_editorial_consumer_deck(intake):
        return preferred

    sanitized: list[str] = []
    for index in range(count):
        current = preferred[index] if index < len(preferred) else ""
        lowered = current.lower()
        if current and not any(term in lowered for term in CONSUMER_INAPPROPRIATE_TEMPLATE_KEY_TERMS):
            sanitized.append(current)
            continue
        sanitized.append(EDITORIAL_TEMPLATE_SEQUENCE[index % len(EDITORIAL_TEMPLATE_SEQUENCE)])
    return sanitized


def blueprint_by_template_key(blueprints: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        blueprint.get("template_key"): blueprint
        for blueprint in blueprints.get("slides", {}).values()
        if blueprint.get("template_key")
    }


def compact_for_slot(value: str, slot_def: dict[str, Any]) -> str:
    budget = slot_text_budget(slot_def)
    if budget is None or text_budget_units(value) <= budget:
        return value
    return truncate_text_to_budget_units(value, budget)


def slot_budget_override(slot_def: dict[str, Any], intake: DeckIntake) -> dict[str, Any]:
    return {
        "fit_strategy": "shrink",
        "max_chars_per_line": 200,
        "max_lines": 10,
    }


def slot_overrides_for_template(blueprint: dict[str, Any], intake: DeckIntake) -> dict[str, dict[str, Any]]:
    return {
        str(slot["slot"]): slot_budget_override(slot, intake)
        for slot in blueprint.get("editable_text_slots", [])
        if slot.get("slot")
    }


def compact_for_slot_with_override(value: str, slot_def: dict[str, Any], override: dict[str, Any]) -> str:
    budget = slot_text_budget(slot_def, override)
    if budget is None or text_budget_units(value) <= budget:
        return value
    return truncate_text_to_budget_units(value, budget)


def short_footer(intake: DeckIntake) -> str:
    return f"Draft | {slugify(intake.name)[:36]}"


def numbered_item(slot_name: str, items: list[IncludeItem], offset: int = 0) -> IncludeItem | None:
    match = re.search(r"_(\d+)_", f"_{slot_name}_")
    if not match:
        return None
    index = offset + int(match.group(1)) - 1
    return items[index] if 0 <= index < len(items) else None


def item_title(item: IncludeItem) -> str:
    return item.title


def item_body(item: IncludeItem, intake: DeckIntake) -> str:
    if item.detail:
        return item.detail
    return intake.primary_goal


ROLE_TAG_LABELS = {
    "architecture": "Architecture",
    "audience_case": "Audience",
    "audience_profile": "Audience",
    "before_after": "Before/After",
    "clinical_context": "Clinical",
    "closing": "Next",
    "components": "Components",
    "content_case": "Content",
    "context": "Context",
    "decision": "Decision",
    "decision_case": "Decision",
    "decision_path": "Decision",
    "destination_hook": "Destination",
    "evidence": "Evidence",
    "executive_summary": "Summary",
    "experience_case": "Experience",
    "growth_case": "Growth",
    "hook": "Hook",
    "implementation": "Implementation",
    "ingredient_story": "Ingredient",
    "market_context": "Market",
    "market_story": "Market",
    "menu_hook": "Menu",
    "metrics": "Metrics",
    "next_steps": "Next",
    "outcome_metrics": "Outcomes",
    "pairing_story": "Pairing",
    "patient_or_ops_problem": "Problem",
    "problem": "Problem",
    "proof": "Proof",
    "proof_metric": "Proof",
    "program_case": "Program",
    "roi": "ROI",
    "route_option": "Route",
    "technical_hook": "Tech",
    "traveler_profile": "Traveler",
    "venue_hook": "Venue",
}


def tag_for_slot(slot_name: str, intake: DeckIntake) -> str | None:
    match = re.fullmatch(r"tag_(\d+)", slot_name)
    if not match:
        return None
    roles = list(industry_profile(intake).get("storyline_roles") or [])
    index = int(match.group(1)) - 1
    if not 0 <= index < len(roles):
        return None
    label = ROLE_TAG_LABELS.get(str(roles[index]), str(roles[index]).replace("_", " ").title())
    return f"#{label.replace(' ', '')}"


def sequenced_text(slot_name: str, include_text: str | None, include_detail: str | None, items: list[IncludeItem], item_offset: int, intake: DeckIntake) -> str | None:
    match = re.search(r"_(\d+)$", slot_name)
    if match:
        index = item_offset + int(match.group(1)) - 1
        if 0 <= index < len(items):
            item = items[index]
            return item_body(item, intake) if include_detail else item_title(item)
        return None
    return include_detail or include_text or intake.primary_goal


def text_for_slot(
    slot_def: dict[str, Any],
    *,
    slide_title: str,
    purpose: str,
    intake: DeckIntake,
    include_text: str | None,
    include_detail: str | None,
    items: list[IncludeItem],
    item_offset: int,
) -> str | None:
    slot_name = str(slot_def.get("slot", ""))
    lowered = slot_name.lower()
    tag = tag_for_slot(lowered, intake)
    if tag:
        return tag
    if lowered == "footer_note":
        return short_footer(intake)
    if lowered == "name":
        return slide_title
    if lowered == "eyebrow":
        return "가이드" if locale_is_korean(intake) else purpose.replace("_", " ").upper()
    if lowered == "case_number":
        if is_editorial_consumer_deck(intake):
            return None
        return f"Case {item_offset + 1:02d}"
    if lowered == "period":
        if is_editorial_consumer_deck(intake):
            return None
        return "Current planning cycle"
    if lowered == "role":
        return intake.presentation_context.presenter_role
    if lowered == "outcome_title":
        if is_editorial_consumer_deck(intake):
            return None
        return "Expected outcome"
    if lowered == "capability_title":
        if is_editorial_consumer_deck(intake):
            return None
        return "Focus areas"
    if re.fullmatch(r"(outcome|capability|text)_\d+", lowered):
        return sequenced_text(lowered, include_text, include_detail, items, item_offset, intake)
    if lowered == "left_card_title":
        return include_text or slide_title
    if lowered == "left_card_body":
        return include_detail or intake.primary_goal
    if lowered == "right_card_title":
        next_item = items[item_offset + 1] if item_offset + 1 < len(items) else None
        return item_title(next_item) if next_item else ("추천 포인트" if locale_is_korean(intake) else "Recommendation")
    if re.fullmatch(r"(toc|step|card|message|item)_\d+_number", lowered):
        item = numbered_item(lowered, items, item_offset)
        if item:
            return lowered.split("_")[1].zfill(2)
        return None
    if re.fullmatch(r"(toc|step|card|message|item)_\d+_title", lowered):
        item = numbered_item(lowered, items, item_offset)
        if item:
            return item_title(item)
        return None
    if re.fullmatch(r"(toc|step|card|message|item)_\d+_body", lowered):
        item = numbered_item(lowered, items, item_offset)
        if item:
            return item_body(item, intake)
        return None
    if re.fullmatch(r"body_\d+", lowered):
        item = numbered_item(lowered, items, item_offset)
        if item:
            return item_body(item, intake)
        return None
    if "title" in lowered or lowered in {"headline", "section"}:
        return slide_title
    if "subtitle" in lowered or "summary" in lowered or "description" in lowered:
        return include_detail or include_text or intake.primary_goal
    if lowered in {"conclusion", "goal_statement", "call_to_action"}:
        return intake.primary_goal
    if any(token in lowered for token in ("body", "message", "point", "card", "item", "note")):
        return include_detail or include_text or intake.primary_goal
    return None


def text_slots_for_template(
    template_key: str,
    slide_title: str,
    intake: DeckIntake,
    include_text: str | None,
    include_detail: str | None,
    blueprints_by_key: dict[str, dict[str, Any]],
    items: list[IncludeItem],
    item_offset: int,
) -> dict[str, str]:
    blueprint = blueprints_by_key.get(template_key)
    if not blueprint:
        return {"title": slide_title, "footer_note": short_footer(intake)}
    values: dict[str, str] = {}
    overrides = slot_overrides_for_template(blueprint, intake)
    for slot in blueprint.get("editable_text_slots", []):
        slot_name = slot.get("slot")
        if not slot_name:
            continue
        value = text_for_slot(
            slot,
            slide_title=slide_title,
            purpose=str(blueprint.get("purpose") or ""),
            intake=intake,
            include_text=include_text,
            include_detail=include_detail,
            items=items,
            item_offset=item_offset,
        )
        if value is not None:
            values[slot_name] = compact_for_slot_with_override(value, slot, overrides.get(slot_name, {}))
    return values


def slide_title_for(
    index: int,
    purpose: str,
    intake: DeckIntake,
    items: list[IncludeItem],
    has_toc: bool = True,
) -> tuple[str, str | None, str | None, int]:
    if index == 0:
        cover_title = intake.name.split(" / ")[-1] if locale_is_korean(intake) and " / " in intake.name else intake.name
        return cover_title, intake.primary_goal, intake.primary_goal, 0
    include_index = index - (2 if has_toc else 1) if purpose != "toc" else None
    if include_index is not None and 0 <= include_index < len(items):
        item = items[include_index]
        return item_title(item), item_title(item), item_body(item, intake), include_index
    if purpose == "toc":
        title = "구성" if locale_is_korean(intake) else "Decision agenda"
        return title, " / ".join(item_title(item) for item in items[:4]), None, 0
    if purpose == "closing":
        return ("마무리" if locale_is_korean(intake) else "Next steps"), intake.primary_goal, intake.primary_goal, max(0, len(items) - 1)
    return purpose.replace("_", " ").title(), intake.primary_goal, intake.primary_goal, 0


def project_root_for_material(path: Path) -> Path | None:
    if path.is_dir():
        return path
    if path.parent.name in {"docs", "specs"}:
        return path.parent.parent
    if path.parent.name == "images" and path.parent.parent.name == "assets":
        return path.parent.parent.parent
    return None


def discover_image_assets(intake: DeckIntake) -> list[Path]:
    images: list[Path] = []
    for material in intake.source_materials:
        path = resolve_from(BASE_DIR, material.path)
        candidates: list[Path] = []
        if path.exists() and path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            candidates.append(path)
        root = project_root_for_material(path)
        if root is not None:
            image_dir = root / "assets" / "images"
            if image_dir.exists():
                candidates.extend(
                    item
                    for item in sorted(image_dir.iterdir())
                    if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
                )
        images.extend(candidates)

    unique: dict[str, Path] = {}
    for image in images:
        unique[str(image.resolve())] = image.resolve()
    return sorted(unique.values(), key=lambda value: ("cover" not in value.stem.lower(), value.name.lower()))


def discover_source_project_deck(intake: DeckIntake) -> Path | None:
    for material in intake.source_materials:
        path = resolve_from(BASE_DIR, material.path)
        root = project_root_for_material(path)
        if root is None:
            continue
        deck_dir = root / "deck"
        if deck_dir.exists():
            decks = sorted(deck_dir.glob("*.pptx"))
            if decks:
                return decks[0].resolve()
    fallback = BASE_DIR / "outputs" / "decks" / "korea_q2_seasonal_seafood_guide_v2.pptx"
    return fallback.resolve() if fallback.exists() else None


def load_feedback_memories(path: Path = DEFAULT_FEEDBACK_MEMORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = load_json(path)
    memories = payload.get("memories", [])
    return [memory for memory in memories if isinstance(memory, dict)]


def intake_match_text(intake: DeckIntake) -> dict[str, str]:
    source_paths = " ".join(material.path for material in intake.source_materials)
    source_descriptions = " ".join(material.description or "" for material in intake.source_materials)
    return {
        "name": intake.name.lower(),
        "setting": intake.presentation_context.setting.lower(),
        "audience": " ".join([intake.audience.primary, *intake.audience.secondary]).lower(),
        "notes": " ".join([intake.brand_or_template_scope.notes or "", intake.notes or ""]).lower(),
        "source_path": source_paths.lower(),
        "source_description": source_descriptions.lower(),
        "content": " ".join([intake.primary_goal, *intake.must_include, *intake.must_avoid]).lower(),
    }


def feedback_memory_score(intake: DeckIntake, memory: dict[str, Any]) -> int:
    match = memory.get("match")
    if not isinstance(match, dict) or not match:
        return 0
    text = intake_match_text(intake)
    score = 0
    for rule, raw_needles in match.items():
        if not rule.endswith("_contains") or not isinstance(raw_needles, list):
            continue
        field = rule[: -len("_contains")]
        haystack = text.get(field, "")
        if not haystack:
            continue
        needles = [str(needle).lower() for needle in raw_needles if str(needle).strip()]
        if any(needle in haystack for needle in needles):
            score += 1
    return score


def matching_feedback_memory(intake: DeckIntake) -> dict[str, Any] | None:
    scored = [
        (feedback_memory_score(intake, memory), memory)
        for memory in load_feedback_memories()
    ]
    scored = [(score, memory) for score, memory in scored if score > 0]
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], str(item[1].get("id", ""))), reverse=True)
    return scored[0][1]


def feedback_source_slide_numbers(memory: dict[str, Any] | None) -> set[int]:
    if memory is None:
        return set()
    source_policy = memory.get("source_deck_policy", {})
    numbers = {
        int(slide_no)
        for slide_no in source_policy.get("reuse_source_slides", [])
        if isinstance(slide_no, int) and slide_no > 0
    }
    for preference in memory.get("slide_preferences", []):
        if isinstance(preference, dict) and preference.get("winner") == "source":
            slide_no = preference.get("slide")
            if isinstance(slide_no, int) and slide_no > 0:
                numbers.add(slide_no)
    return numbers


def feedback_composer_slide_numbers(memory: dict[str, Any] | None) -> set[int]:
    if memory is None:
        return set()
    composer_policy = memory.get("composer_policy", {})
    numbers = {
        int(slide_no)
        for slide_no in composer_policy.get("regenerate_slides", [])
        if isinstance(slide_no, int) and slide_no > 0
    }
    for preference in memory.get("slide_preferences", []):
        if isinstance(preference, dict) and preference.get("winner") == "composer":
            slide_no = preference.get("slide")
            if isinstance(slide_no, int) and slide_no > 0:
                numbers.add(slide_no)
    return numbers


def should_reuse_source_slide(slide_no: int, source_deck: Path | None, memory: dict[str, Any] | None) -> bool:
    return source_deck is not None and slide_no in feedback_source_slide_numbers(memory)


def image_slots_for_template(
    template_key: str,
    slide_index: int,
    spec_dir: Path,
    images: list[Path],
    blueprints_by_key: dict[str, dict[str, Any]],
) -> dict[str, str]:
    blueprint = blueprints_by_key.get(template_key)
    if not blueprint or not images:
        return {}
    slots = [slot for slot in blueprint.get("editable_image_slots", []) if slot.get("slot")]
    if not slots:
        return {}

    values: dict[str, str] = {}
    for slot_offset, slot in enumerate(slots):
        if slide_index == 0:
            image = next((item for item in images if "cover" in item.stem.lower()), images[0])
        else:
            image = images[(slide_index + slot_offset) % len(images)]
        values[str(slot["slot"])] = spec_path_ref(image, spec_dir)
    return values


def residual_text_patterns_for(intake: DeckIntake) -> list[str]:
    profile = industry_profile(intake)
    patterns = list(profile.get("residual_text_patterns") or [])
    if is_editorial_consumer_deck(intake):
        patterns.extend(BUSINESS_RESIDUAL_TEXT_PATTERNS)
    return patterns


def selector_guardrails_for_intake(intake: DeckIntake) -> dict[str, Any]:
    profile = industry_profile(intake)
    selector_defaults = profile.get("selector_defaults", {}) if isinstance(profile.get("selector_defaults"), dict) else {}
    return {
        "tone": [item.value for item in intake.tone],
        "use_variation_penalty": True,
        **selector_defaults,
    }


EDITORIAL_COLORS = {
    "cream": "#F7F1E3",
    "navy": "#123047",
    "sea": "#0F6F78",
    "aqua": "#8DD8D2",
    "coral": "#E86F51",
    "gold": "#D8A23A",
    "white": "#FFFFFF",
    "ink": "#1B2630",
    "muted": "#59656F",
}


def shape(
    left: float,
    top: float,
    width: float,
    height: float,
    fill: str | None,
    line: str | None = None,
    radius: float | None = None,
    *,
    geometry: str | None = None,
    rotation: float | None = None,
    line_width: float | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "fill": fill,
        "line": line,
        "radius": radius,
    }
    if geometry:
        item["geometry"] = geometry
    if rotation is not None:
        item["rotation"] = rotation
    if line_width is not None:
        item["line_width"] = line_width
    return item


def text_box(
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    font_size: float,
    color: str = "#123047",
    bold: bool = False,
    align: str | None = None,
    max_chars_per_line: int | None = None,
) -> dict[str, Any]:
    return {
        "text": text,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "font_size": font_size,
        "color": color,
        "bold": bold,
        "align": align,
        "max_chars_per_line": max_chars_per_line,
    }


def image_item(path: Path, spec_dir: Path, left: float, top: float, width: float, height: float) -> dict[str, Any]:
    return {"path": spec_path_ref(path, spec_dir), "left": left, "top": top, "width": width, "height": height}


def image_by_name(images: list[Path], *needles: str) -> Path | None:
    lowered_needles = [needle.lower() for needle in needles]
    for image in images:
        stem = image.stem.lower()
        if any(needle in stem for needle in lowered_needles):
            return image
    return images[0] if images else None


def footer_box() -> dict[str, Any]:
    return text_box("Food Guide · 2026-04-19 · Composer Fixed", 0.7, 7.02, 5.8, 0.2, font_size=7.5, color="#59656F")


def base_blank_slide(title: str, subtitle: str | None = None, *, bg: str = "#F7F1E3") -> dict[str, Any]:
    boxes = [text_box(title, 0.7, 0.48, 7.6, 0.45, font_size=24, color=EDITORIAL_COLORS["navy"], bold=True)]
    if subtitle:
        boxes.append(text_box(subtitle, 0.72, 0.98, 8.7, 0.32, font_size=10.5, color=EDITORIAL_COLORS["muted"]))
    boxes.append(footer_box())
    return {
        "layout": "template_slide",
        "source_mode": "blank",
        "clear_unfilled_slots": True,
        "shapes": [shape(0, 0, 13.33, 7.5, bg)],
        "images": [],
        "text_boxes": boxes,
    }


def add_card(slide: dict[str, Any], left: float, top: float, width: float, height: float, title: str, body: str, *, accent: str) -> None:
    slide["shapes"].append(shape(left, top, width, height, EDITORIAL_COLORS["white"], "#E5DDCD", 0.08))
    slide["shapes"].append(shape(left, top, 0.12, height, accent))
    slide["text_boxes"].append(text_box(title, left + 0.24, top + 0.18, width - 0.44, 0.28, font_size=14, color=EDITORIAL_COLORS["navy"], bold=True))
    slide["text_boxes"].append(text_box(body, left + 0.24, top + 0.58, width - 0.44, height - 0.72, font_size=10.3, color=EDITORIAL_COLORS["ink"], max_chars_per_line=32))


def add_wave_lines(slide: dict[str, Any], left: float, top: float, width: float, *, color: str) -> None:
    for offset in (0.0, 0.22):
        slide["shapes"].append(
            shape(left, top + offset, width, 0.14, None, color, geometry="wave", line_width=0.01)
        )


def add_editable_seafood_icon(slide: dict[str, Any], left: float, top: float, width: float, height: float, kind: str, *, accent: str) -> None:
    slide["shapes"].append(shape(left, top, width, height, "#F8F3E8", "#E1D6C4", radius=0.08))
    add_wave_lines(slide, left + 0.25, top + 0.28, width - 0.5, color=accent)
    cx = left + width / 2
    cy = top + height / 2 + 0.15

    if kind == "flatfish":
        slide["shapes"].append(shape(cx - 0.52, cy - 0.18, 0.86, 0.36, "#D9EEE7", accent, geometry="ellipse", line_width=0.01))
        slide["shapes"].append(shape(cx + 0.28, cy - 0.16, 0.34, 0.32, "#D9EEE7", accent, geometry="triangle", rotation=90, line_width=0.01))
        slide["shapes"].append(shape(cx - 0.28, cy - 0.05, 0.06, 0.06, EDITORIAL_COLORS["navy"], geometry="ellipse"))
        slide["shapes"].append(shape(cx - 0.58, cy - 0.32, 0.5, 0.18, "#D9EEE7", accent, geometry="arc", line_width=0.01))
    elif kind == "pomfret":
        slide["shapes"].append(shape(cx - 0.42, cy - 0.3, 0.84, 0.6, "#F0E6C8", accent, geometry="ellipse", line_width=0.01))
        slide["shapes"].append(shape(cx + 0.31, cy - 0.17, 0.3, 0.34, "#F0E6C8", accent, geometry="triangle", rotation=90, line_width=0.01))
        slide["shapes"].append(shape(cx - 0.18, cy - 0.05, 0.06, 0.06, EDITORIAL_COLORS["navy"], geometry="ellipse"))
    elif kind == "fish":
        slide["shapes"].append(shape(cx - 0.52, cy - 0.18, 0.86, 0.36, "#D9EEE7", accent, geometry="ellipse", line_width=0.01))
        slide["shapes"].append(shape(cx + 0.28, cy - 0.16, 0.34, 0.32, "#D9EEE7", accent, geometry="triangle", rotation=90, line_width=0.01))
        slide["shapes"].append(shape(cx - 0.28, cy - 0.05, 0.06, 0.06, EDITORIAL_COLORS["navy"], geometry="ellipse"))
    elif kind in {"eel"}:
        slide["shapes"].append(shape(cx - 0.76, cy - 0.07, 1.38, 0.15, "#E86F51", "#E86F51", geometry="arc", line_width=0.02))
        slide["shapes"].append(shape(cx + 0.43, cy - 0.03, 0.08, 0.08, EDITORIAL_COLORS["navy"], geometry="ellipse"))
    elif kind == "clam":
        for idx in range(5):
            slide["shapes"].append(shape(cx - 0.56 + idx * 0.24, cy - 0.08, 0.2, 0.34, "#F4D78A", accent, geometry="arc", line_width=0.012))
        slide["shapes"].append(shape(cx - 0.58, cy + 0.17, 1.12, 0.04, accent))
    elif kind == "pen_shell":
        for idx in range(3):
            slide["shapes"].append(shape(cx - 0.42 + idx * 0.32, cy - 0.52, 0.16, 0.92, "#F4D78A", accent, geometry="round_rect", line_width=0.01))
        slide["shapes"].append(shape(cx - 0.58, cy + 0.28, 1.12, 0.04, accent))
    elif kind in {"shell"}:
        for idx in range(4):
            slide["shapes"].append(shape(cx - 0.54 + idx * 0.28, cy - 0.12, 0.22, 0.42, "#F4D78A", accent, geometry="arc", line_width=0.012))
        slide["shapes"].append(shape(cx - 0.62, cy + 0.18, 1.14, 0.04, accent))
    elif kind == "webfoot":
        slide["shapes"].append(shape(cx - 0.28, cy - 0.38, 0.58, 0.62, accent, geometry="ellipse"))
        for idx in range(4):
            slide["shapes"].append(shape(cx - 0.37 + idx * 0.23, cy + 0.12, 0.08, 0.45, accent, geometry="arc", line_width=0.016))
        slide["shapes"].append(shape(cx - 0.06, cy - 0.12, 0.06, 0.06, EDITORIAL_COLORS["white"], geometry="ellipse"))
        slide["shapes"].append(shape(cx + 0.08, cy - 0.12, 0.06, 0.06, EDITORIAL_COLORS["white"], geometry="ellipse"))
    elif kind == "cuttlefish":
        slide["shapes"].append(shape(cx - 0.34, cy - 0.18, 0.68, 0.36, accent, geometry="ellipse"))
        slide["shapes"].append(shape(cx + 0.24, cy - 0.15, 0.34, 0.3, accent, geometry="triangle", rotation=90))
        for idx in range(3):
            slide["shapes"].append(shape(cx - 0.44 + idx * 0.18, cy + 0.1, 0.08, 0.38, accent, geometry="arc", line_width=0.014))
    elif kind == "sea_squirt":
        slide["shapes"].append(shape(cx - 0.28, cy - 0.28, 0.56, 0.56, accent, geometry="ellipse"))
        for angle in (0, 45, 90, 135):
            slide["shapes"].append(shape(cx - 0.02, cy - 0.52, 0.04, 0.42, accent, geometry="rect", rotation=angle))
    elif kind == "squid":
        slide["shapes"].append(shape(cx - 0.28, cy - 0.38, 0.58, 0.62, accent, geometry="ellipse"))
        for idx in range(4):
            slide["shapes"].append(shape(cx - 0.37 + idx * 0.23, cy + 0.12, 0.08, 0.45, accent, geometry="arc", line_width=0.016))
    elif kind in {"kelp"}:
        for idx in range(4):
            slide["shapes"].append(shape(cx - 0.36 + idx * 0.25, cy - 0.48, 0.12, 0.9, accent, geometry="wave", rotation=90, line_width=0.02))
    else:
        slide["shapes"].append(shape(cx - 0.38, cy - 0.28, 0.76, 0.56, "#D9EEE7", accent, geometry="ellipse", line_width=0.01))


def seafood_kind(name: str) -> str:
    if name == "주꾸미":
        return "webfoot"
    if name == "갑오징어":
        return "cuttlefish"
    if name == "멍게":
        return "sea_squirt"
    if name == "도다리":
        return "flatfish"
    if name == "병어":
        return "pomfret"
    if name == "바지락":
        return "clam"
    if name == "키조개":
        return "pen_shell"
    if name == "장어":
        return "eel"
    if name == "다시마":
        return "kelp"
    return "fish"


def add_q2_cover_panel(slide: dict[str, Any]) -> None:
    panel_left, panel_top, panel_w, panel_h = 7.05, 0.72, 5.25, 6.05
    slide["shapes"].append(shape(panel_left, panel_top, panel_w, panel_h, "#F7F1E3", "#8DD8D2", radius=0.08))
    slide["text_boxes"].append(text_box("Q2 제철 캘린더", panel_left + 0.35, panel_top + 0.32, 2.6, 0.34, font_size=14, color=EDITORIAL_COLORS["navy"], bold=True))
    slide["text_boxes"].append(text_box("4월-6월 대표 해산물", panel_left + 0.36, panel_top + 0.72, 2.7, 0.24, font_size=9.5, color=EDITORIAL_COLORS["muted"]))
    months = [
        ("4월", "주꾸미 · 도다리", "webfoot", EDITORIAL_COLORS["coral"]),
        ("5월", "갑오징어 · 멍게", "cuttlefish", EDITORIAL_COLORS["sea"]),
        ("6월", "병어 · 장어", "pomfret", EDITORIAL_COLORS["gold"]),
    ]
    for idx, (month, label, kind, accent) in enumerate(months):
        top = panel_top + 1.25 + idx * 1.42
        slide["shapes"].append(shape(panel_left + 0.38, top, 4.5, 1.06, EDITORIAL_COLORS["white"], "#E1D6C4", radius=0.08))
        slide["shapes"].append(shape(panel_left + 0.38, top, 0.16, 1.06, accent))
        slide["text_boxes"].append(text_box(month, panel_left + 0.72, top + 0.2, 0.75, 0.25, font_size=13, color=EDITORIAL_COLORS["navy"], bold=True))
        slide["text_boxes"].append(text_box(label, panel_left + 0.72, top + 0.55, 1.95, 0.24, font_size=9.5, color=EDITORIAL_COLORS["ink"]))
        add_editable_seafood_icon(slide, panel_left + 3.35, top + 0.18, 1.08, 0.68, kind, accent=accent)
    add_wave_lines(slide, panel_left + 0.48, panel_top + 5.55, 4.2, color=EDITORIAL_COLORS["aqua"])


def add_image_card(
    slide: dict[str, Any],
    spec_dir: Path,
    image: Path | None,
    left: float,
    top: float,
    title: str,
    dish: str,
    note: str,
) -> None:
    slide["shapes"].append(shape(left, top, 3.75, 4.35, EDITORIAL_COLORS["white"], "#E5DDCD", 0.08))
    add_editable_seafood_icon(slide, left + 0.16, top + 0.16, 3.43, 2.05, seafood_kind(title), accent=EDITORIAL_COLORS["coral" if title in {"주꾸미", "갑오징어", "장어"} else "sea" if title in {"도다리", "다시마"} else "gold"])
    slide["text_boxes"].append(text_box(title, left + 0.24, top + 2.42, 3.2, 0.32, font_size=17, color=EDITORIAL_COLORS["navy"], bold=True))
    slide["text_boxes"].append(text_box(dish, left + 0.24, top + 2.84, 3.2, 0.26, font_size=11.5, color=EDITORIAL_COLORS["coral"], bold=True))
    slide["text_boxes"].append(text_box(note, left + 0.24, top + 3.24, 3.18, 0.72, font_size=9.7, color=EDITORIAL_COLORS["ink"], max_chars_per_line=25))


def imported_source_slide(slide_no: int) -> dict[str, Any]:
    return {
        "layout": "template_slide",
        "base_slide_no": slide_no,
        "clear_unfilled_slots": False,
    }


def compose_editorial_blank_slides(
    intake: DeckIntake,
    spec_dir: Path,
    images: list[Path],
    source_deck: Path | None = None,
    feedback_memory: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cover_image = image_by_name(images, "cover")
    slides: list[dict[str, Any]] = []

    cover = {
        "layout": "template_slide",
        "source_mode": "blank",
        "clear_unfilled_slots": True,
        "shapes": [shape(0, 0, 13.33, 7.5, EDITORIAL_COLORS["navy"])],
        "images": [],
        "text_boxes": [
            text_box("한국 2분기\n제철 해산물 가이드", 0.82, 1.55, 5.1, 1.45, font_size=29, color=EDITORIAL_COLORS["white"], bold=True, max_chars_per_line=14),
            text_box("4-6월 재료와 어울리는 요리를 한눈에 정리", 0.86, 3.28, 5.3, 0.34, font_size=13, color=EDITORIAL_COLORS["aqua"]),
            text_box("APR-JUN · Food Guide", 0.88, 4.0, 2.35, 0.3, font_size=10.5, color=EDITORIAL_COLORS["gold"], bold=True),
        ],
    }
    add_q2_cover_panel(cover)
    slides.append(cover)

    if should_reuse_source_slide(2, source_deck, feedback_memory):
        slides.append(imported_source_slide(2))
    else:
        design = base_blank_slide("디자인 브리프", "재사용 가능한 색상, 서체, 배경 규칙을 먼저 고정")
        swatches = [
            ("메인 네이비", "#123047"),
            ("해조 그린", "#0F6F78"),
            ("요리 포인트", "#E86F51"),
            ("제철 강조", "#D8A23A"),
        ]
        for idx, (label, color) in enumerate(swatches):
            left = 0.82 + idx * 3.05
            design["shapes"].append(shape(left, 2.0, 2.42, 2.55, color, radius=0.08))
            design["text_boxes"].append(text_box(label, left + 0.18, 2.22, 2.0, 0.3, font_size=13, color=EDITORIAL_COLORS["white"], bold=True))
            design["text_boxes"].append(text_box(color, left + 0.18, 3.75, 2.0, 0.26, font_size=10.5, color=EDITORIAL_COLORS["white"]))
        design["text_boxes"].append(
            text_box(
                "크림 배경 위에 네이비 제목, sea green/coral/gold 강조색을 반복해 식재료 카드와 표를 같은 톤으로 묶습니다.",
                0.9,
                5.25,
                10.8,
                0.55,
                font_size=12,
                color=EDITORIAL_COLORS["ink"],
                max_chars_per_line=58,
            )
        )
        slides.append(design)

    if should_reuse_source_slide(3, source_deck, feedback_memory):
        slides.append(imported_source_slide(3))
    else:
        agenda = base_blank_slide("2분기 제철 맵", "월별로 기억하기 쉽도록 3개 식재료씩 묶은 구성")
        for idx, (month, items_text, body, accent) in enumerate(
            [
                ("4월", "주꾸미 · 도다리 · 바지락", "봄철 담백함과 맑은 국물 메뉴", EDITORIAL_COLORS["sea"]),
                ("5월", "갑오징어 · 멍게 · 다시마", "산뜻한 식감과 향 중심 구성", EDITORIAL_COLORS["coral"]),
                ("6월", "병어 · 장어 · 키조개", "초여름 보양과 메인 요리 흐름", EDITORIAL_COLORS["gold"]),
            ]
        ):
            left = 0.78 + idx * 4.08
            add_card(agenda, left, 1.85, 3.45, 3.85, month, f"{items_text}\n{body}", accent=accent)
        slides.append(agenda)

    for title, subtitle, cards in [
        (
            "4월 추천 해산물과 요리",
            "봄철 담백함과 맑은 국물 중심",
            [
                ("주꾸미", "주꾸미 샤브샤브", "산란기 전후의 단맛과 탱글한 식감", image_by_name(images, "webfoot")),
                ("도다리", "도다리 쑥국", "맑은 국물과 봄나물 향의 조합", image_by_name(images, "flatfish")),
                ("바지락", "바지락 칼국수", "시원한 국물과 면 요리에 적합", image_by_name(images, "clam")),
            ],
        ),
        (
            "5월 추천 해산물과 요리",
            "산뜻한 향과 식감을 살리는 구성",
            [
                ("갑오징어", "갑오징어 숙회", "부드러운 식감과 산뜻한 초장", image_by_name(images, "cuttlefish")),
                ("멍게", "멍게 비빔밥", "향이 강해 참기름과 채소가 균형", image_by_name(images, "sea_squirt")),
                ("다시마", "다시마쌈", "가벼운 쌈과 반찬으로 활용", image_by_name(images, "kelp")),
            ],
        ),
        (
            "6월 추천 해산물과 요리",
            "초여름 메인 요리와 보양 흐름",
            [
                ("병어", "병어 조림", "담백한 살과 매콤한 양념의 대비", image_by_name(images, "pomfret")),
                ("장어", "장어구이", "초여름 보양 메뉴로 직관적", image_by_name(images, "eel")),
                ("키조개", "키조개 구이", "버터구이와 관자 요리에 적합", image_by_name(images, "pen_shell")),
            ],
        ),
    ]:
        slide = base_blank_slide(title, subtitle)
        for idx, (name, dish, note, image) in enumerate(cards):
            add_image_card(slide, spec_dir, image, 0.78 + idx * 4.1, 1.65, name, dish, note)
        slides.append(slide)

    if all(should_reuse_source_slide(slide_no, source_deck, feedback_memory) for slide_no in (7, 8, 9)):
        slides.extend([imported_source_slide(7), imported_source_slide(8), imported_source_slide(9)])
        return slides

    pairing = base_blank_slide("요리 페어링 매트릭스", "조리 방식별로 어울리는 재료를 빠르게 비교")
    headers = ["상황", "맑은 국물", "숙회/비빔", "구이", "조림"]
    rows = [
        ["가벼운 봄맛", "도다리 쑥국", "주꾸미 샤브", "키조개 구이", "병어 조림"],
        ["향을 살릴 때", "바지락 국물", "멍게 비빔밥", "장어구이", "매콤 조림"],
        ["한 끼 코스", "국물", "전채", "메인", "마무리"],
    ]
    x0, y0, cw, ch = 0.76, 1.78, 2.38, 0.72
    for c, header in enumerate(headers):
        pairing["shapes"].append(shape(x0 + c * cw, y0, cw - 0.04, ch, EDITORIAL_COLORS["sea"] if c else EDITORIAL_COLORS["navy"]))
        pairing["text_boxes"].append(text_box(header, x0 + c * cw + 0.1, y0 + 0.22, cw - 0.24, 0.25, font_size=10.5, color=EDITORIAL_COLORS["white"], bold=True, align="center"))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            pairing["shapes"].append(shape(x0 + c * cw, y0 + (r + 1) * ch, cw - 0.04, ch, EDITORIAL_COLORS["white"], "#E5DDCD"))
            pairing["text_boxes"].append(text_box(value, x0 + c * cw + 0.1, y0 + (r + 1) * ch + 0.2, cw - 0.24, 0.28, font_size=10.2, color=EDITORIAL_COLORS["ink"], align="center"))
    slides.append(pairing)

    course = base_blank_slide("샘플 코스 구성", "제철 식재료를 한 끼 메뉴 흐름으로 연결")
    steps = [
        ("시작", "다시마쌈\n멍게 비빔 한입", EDITORIAL_COLORS["sea"]),
        ("가벼운 국물", "도다리 쑥국\n바지락 칼국수", EDITORIAL_COLORS["aqua"]),
        ("메인", "장어구이\n병어 조림", EDITORIAL_COLORS["coral"]),
        ("마무리", "시장 상황에 맞춰\n대체 재료 선택", EDITORIAL_COLORS["gold"]),
    ]
    for idx, (label, body, accent) in enumerate(steps):
        left = 0.72 + idx * 3.12
        add_card(course, left, 2.08, 2.58, 2.75, label, body, accent=accent)
        if idx < len(steps) - 1:
            course["text_boxes"].append(text_box("→", left + 2.68, 3.22, 0.35, 0.35, font_size=20, color=EDITORIAL_COLORS["navy"], bold=True, align="center"))
    slides.append(course)

    qa = {
        "layout": "template_slide",
        "source_mode": "blank",
        "clear_unfilled_slots": True,
        "shapes": [
            shape(0, 0, 13.33, 7.5, EDITORIAL_COLORS["cream"]),
            shape(0, 0, 13.33, 1.28, EDITORIAL_COLORS["navy"]),
        ],
        "images": [],
        "text_boxes": [
            text_box("APPENDIX", 0.72, 0.26, 1.35, 0.22, font_size=9, color=EDITORIAL_COLORS["gold"], bold=True),
            text_box("작성 가정과 검증 포인트", 0.72, 0.58, 5.6, 0.42, font_size=23, color=EDITORIAL_COLORS["white"], bold=True),
            text_box("본문 가이드와 구분되는 운영/검증 메모", 7.6, 0.62, 4.4, 0.25, font_size=10.5, color=EDITORIAL_COLORS["aqua"], align="right"),
            footer_box(),
        ],
    }
    for idx, (title, body, accent) in enumerate(
        [
            ("콘텐츠 범위", "한국 2분기인 4-6월에 자주 소개되는 제철 해산물과 대표 요리를 큐레이션했습니다.", EDITORIAL_COLORS["sea"]),
            ("이미지 정책", "외부 사진 라이선스 리스크를 피하기 위해 생성형/도식형 일러스트를 사용했습니다.", EDITORIAL_COLORS["coral"]),
            ("템플릿화 방향", "색상, 폰트, 배경, 카드 슬롯, QA 리포트를 프로젝트 단위 폴더로 함께 관리합니다.", EDITORIAL_COLORS["gold"]),
            ("주의", "지역, 해황, 유통 상황에 따라 실제 제철 체감은 달라질 수 있습니다.", EDITORIAL_COLORS["navy"]),
        ]
    ):
        add_card(qa, 0.8 + (idx % 2) * 5.95, 1.75 + (idx // 2) * 2.15, 5.35, 1.6, title, body, accent=accent)
    slides.append(qa)

    return slides


def compose_spec(intake: DeckIntake, intake_path: Path, output_path: Path) -> dict[str, Any]:
    spec_dir = output_path.parent.resolve()
    intake_dir = intake_path.parent.resolve()
    blueprints = load_json(DEFAULT_BLUEPRINT_PATH)
    blueprints_by_key = blueprint_by_template_key(blueprints)
    profile = industry_profile(intake)
    project_id = slugify(intake.name)
    theme_path = resolve_from(intake_dir, intake.brand_or_template_scope.theme_path, DEFAULT_THEME_PATH)
    deck_path = resolve_from(
        BASE_DIR,
        intake.output_preferences.output_deck_path,
        BASE_DIR / "outputs" / "decks" / f"{project_id}.pptx",
    )
    scope = intake.brand_or_template_scope.preferred_scope or profile.get("preferred_scope") or intake.deck_type.value
    required_library = intake.brand_or_template_scope.required_template_library
    count = desired_slide_count(intake)
    preferred_keys = preferred_template_keys(intake, count, profile)
    purposes = purpose_sequence(intake, count, profile)
    items = include_items(intake)
    images = discover_image_assets(intake)
    feedback_memory = matching_feedback_memory(intake)
    source_deck = discover_source_project_deck(intake)
    residual_patterns = residual_text_patterns_for(intake)
    clear_unfilled_image_slots = bool(profile.get("clear_unfilled_image_slots_without_assets")) and not images
    slides: list[dict[str, Any]] = []
    mode_policy = mode_policy_for_intake(intake)

    if is_editorial_consumer_deck(intake) and images:
        slides = compose_editorial_blank_slides(intake, spec_dir, images, source_deck, feedback_memory)
        uses_source_slides = any("base_slide_no" in slide for slide in slides)
        doc_paths = [
            spec_path_ref(resolve_from(BASE_DIR, material.path), spec_dir)
            for material in intake.source_materials
            if material.kind.value in {"docx", "markdown", "notes"}
        ]
        spec = {
            "$schema": spec_path_ref(BASE_DIR / "config" / "deck_spec.schema.json", spec_dir),
            "name": intake.name,
            "project_id": project_id,
            "theme_path": spec_path_ref(theme_path, spec_dir),
            "mode_policy": mode_policy,
            "recipe": f"industry:{profile.get('industry', 'other')}",
            "reference_catalog_path": spec_path_ref(DEFAULT_REFERENCE_CATALOG_PATH, spec_dir),
            "blueprint_path": spec_path_ref(DEFAULT_BLUEPRINT_PATH, spec_dir),
            "source_template": spec_path_ref(source_deck, spec_dir) if source_deck is not None and uses_source_slides else None,
            "output_path": spec_path_ref(deck_path, spec_dir),
            "doc_paths": doc_paths,
            "asset_intents": asset_intents_for_spec(
                intake,
                purposes=[slide.get("purpose", "content") for slide in slides],
                slides=slides,
                blueprints_by_key=blueprints_by_key,
            ),
            "slides": slides,
            "theme_accent_overrides": {
                "accent1": EDITORIAL_COLORS["sea"],
                "accent2": EDITORIAL_COLORS["coral"],
                "accent3": EDITORIAL_COLORS["aqua"],
                "accent4": EDITORIAL_COLORS["gold"],
            },
        }
        validate_deck_spec(spec)
        return spec

    has_toc = "toc" in purposes[:2]
    for index, purpose in enumerate(purposes):
        title, include_text, include_detail, item_offset = slide_title_for(index, purpose, intake, items, has_toc=has_toc)
        slide: dict[str, Any] = {
            "layout": "template_slide",
            "clear_unfilled_slots": True,
            "clear_unfilled_image_slots": clear_unfilled_image_slots,
            "text_slots": {
                "title": title,
                "footer_note": short_footer(intake),
            },
        }
        if residual_patterns:
            slide["clear_residual_text_patterns"] = residual_patterns
        if index < len(preferred_keys):
            template_key = preferred_keys[index]
            slide["template_key"] = template_key
            slide["text_slots"] = text_slots_for_template(
                template_key,
                title,
                intake,
                include_text,
                include_detail,
                blueprints_by_key,
                items,
                item_offset,
            )
            blueprint = blueprints_by_key.get(template_key)
            if blueprint:
                slide["slot_overrides"] = slot_overrides_for_template(blueprint, intake)
            image_slots = image_slots_for_template(template_key, index, spec_dir, images, blueprints_by_key)
            if image_slots:
                slide["image_slots"] = image_slots
        else:
            selector: dict[str, Any] = {
                "purpose": purpose,
                "scope": scope,
                "prefer_high_quality": True,
                **selector_guardrails_for_intake(intake),
            }
            if required_library:
                selector["source_library"] = required_library
            slide["slide_selector"] = selector
        slides.append(slide)

    doc_paths = [
        spec_path_ref(resolve_from(BASE_DIR, material.path), spec_dir)
        for material in intake.source_materials
        if material.kind.value in {"docx", "markdown", "notes"}
    ]
    spec = {
        "$schema": spec_path_ref(BASE_DIR / "config" / "deck_spec.schema.json", spec_dir),
        "name": intake.name,
        "project_id": project_id,
        "theme_path": spec_path_ref(theme_path, spec_dir),
        "mode_policy": mode_policy,
        "recipe": f"industry:{profile.get('industry', 'other')}",
        "reference_catalog_path": spec_path_ref(DEFAULT_REFERENCE_CATALOG_PATH, spec_dir),
        "blueprint_path": spec_path_ref(DEFAULT_BLUEPRINT_PATH, spec_dir),
        "output_path": spec_path_ref(deck_path, spec_dir),
        "doc_paths": doc_paths,
        "asset_intents": asset_intents_for_spec(
            intake,
            purposes=purposes,
            slides=slides,
            blueprints_by_key=blueprints_by_key,
        ),
        "slides": slides,
    }
    validate_deck_spec(spec)
    return spec


def feedback_application_payload(intake: DeckIntake, spec: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    source_slides = feedback_source_slide_numbers(memory)
    composer_slides = feedback_composer_slide_numbers(memory)
    slides = []
    for index, slide in enumerate(spec.get("slides", []), start=1):
        base_slide_no = slide.get("base_slide_no") if isinstance(slide, dict) else None
        slides.append(
            {
                "slide": index,
                "applied_mode": "source" if base_slide_no else "composer",
                "base_slide_no": base_slide_no,
                "expected_by_feedback": (
                    "source" if index in source_slides else "composer" if index in composer_slides else "unspecified"
                ),
            }
        )
    return {
        "intake_name": intake.name,
        "memory_id": memory.get("id"),
        "memory_description": memory.get("description"),
        "source_reuse_slides": sorted(source_slides),
        "composer_regenerate_slides": sorted(composer_slides),
        "slides": slides,
        "composer_policy": memory.get("composer_policy", {}),
        "source_deck_policy": memory.get("source_deck_policy", {}),
    }


def write_feedback_application_report(intake: DeckIntake, spec: dict[str, Any], output_path: Path) -> None:
    memory = matching_feedback_memory(intake)
    if memory is None:
        return
    reports_dir = BASE_DIR / "outputs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = feedback_application_payload(intake, spec, memory)
    json_path = reports_dir / f"{output_path.stem}_feedback_application.json"
    md_path = reports_dir / f"{output_path.stem}_feedback_application.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        f"# Feedback Application: {payload['memory_id']}",
        "",
        f"- Intake: {payload['intake_name']}",
        f"- Source reuse slides: {', '.join(str(item) for item in payload['source_reuse_slides']) or 'none'}",
        f"- Composer regenerate slides: {', '.join(str(item) for item in payload['composer_regenerate_slides']) or 'none'}",
        "",
        "| Slide | Applied mode | Base slide | Expected by feedback |",
        "| --- | --- | --- | --- |",
    ]
    for slide in payload["slides"]:
        lines.append(
            f"| {slide['slide']} | {slide['applied_mode']} | {slide['base_slide_no'] or ''} | {slide['expected_by_feedback']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_workspace_manifest(workspace: Path) -> dict[str, Any]:
    path = workspace / ".ppt-agent" / "asset_manifest.json"
    if not path.exists():
        return {"assets": []}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {"assets": []}


def workspace_asset_by_id(workspace: Path, asset_id: str) -> dict[str, Any] | None:
    manifest = load_workspace_manifest(workspace)
    for asset in manifest.get("assets", []):
        if isinstance(asset, dict) and asset.get("asset_id") == asset_id:
            return asset
    return None


def append_workspace_asset_intents(
    spec: dict[str, Any],
    *,
    workspace: Path | None,
    preferred_asset_ids: list[str],
    operating_mode: str,
) -> None:
    if not workspace or not preferred_asset_ids:
        return
    intents = spec.setdefault("asset_intents", [])
    first_image_slide = 1
    first_image_slot = "image_1"
    for asset_id in preferred_asset_ids:
        asset = workspace_asset_by_id(workspace, asset_id)
        if not asset:
            raise ValueError(f"workspace asset_id not found: {asset_id}")
        asset_class = asset.get("asset_class")
        asset_type = asset.get("asset_type")
        role = "image_placeholder" if asset_class == "image" else "typography" if asset_class == "typography" else "reference"
        intent = {
            "role": role,
            "asset_class": asset_class,
            "asset_id": asset_id,
            "slide_number": first_image_slide if asset_class == "image" else None,
            "slot": first_image_slot if asset_class == "image" else None,
            "purpose": "user_requested_asset",
            "industry": None,
            "tone": [],
            "aspect_ratio": "16:9",
            "query": {
                "source_type": "user_upload",
                "asset_type": asset_type,
                "selection": "explicit_user_asset_id",
                "operating_mode": operating_mode,
            },
            "source_policy": "workspace_user_asset",
            "materialization": "local_workspace_file",
            "source_type": "user_upload",
            "workspace_relative_path": asset.get("workspace_relative_path"),
            "private_upload_allowed": False,
            "license_action": "user_responsibility",
            "risk_level": "user_responsibility",
            "semantic_context": {
                "intent": "Explicit user-uploaded workspace asset",
                "domain": "user_supplied",
                "audience": "deck_viewer",
                "medium": "presentation",
                "output_surface": "pptx",
            },
            "template_media_policy": {
                "embedded_media_reusable": False,
                "jpg_preview_reusable": False,
                "allowed_use": "workspace_relative_user_asset_only",
            },
            "candidate_asset_ids": [asset_id],
            "usage_rationale": (
                "Explicit user-requested workspace asset; Auto Mode may use it directly and record rationale."
                if operating_mode == "auto"
                else "Assistant Mode candidate selected by stable workspace asset ID."
            ),
            "notes": "Workspace-relative asset reference; source attachment path is intentionally omitted.",
        }
        intents.append(intent)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose a deterministic draft deck spec from deck intake JSON.")
    parser.add_argument("intake_path")
    parser.add_argument("--output", default=None, help="Override output spec path. Defaults to intake output_preferences.")
    parser.add_argument("--workspace", default=None, help="Optional installed PPT workspace for user asset lookup.")
    parser.add_argument("--preferred-user-asset", action="append", default=[], help="Workspace asset_id to include in asset_intents.")
    args = parser.parse_args(argv)

    intake_path = Path(args.intake_path)
    if not intake_path.is_absolute():
        intake_path = BASE_DIR / intake_path
    intake_data = load_json(intake_path)
    intake = validate_deck_intake(intake_data)
    default_output = intake.output_preferences.output_spec_path or f"data/specs/{slugify(intake.name)}_spec.json"
    output_path = Path(args.output or default_output)
    if not output_path.is_absolute():
        output_path = (BASE_DIR / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    spec = compose_spec(intake, intake_path, output_path)
    workspace = Path(args.workspace).resolve() if args.workspace else None
    append_workspace_asset_intents(
        spec,
        workspace=workspace,
        preferred_asset_ids=list(args.preferred_user_asset),
        operating_mode=spec.get("mode_policy", "auto"),
    )
    validate_deck_spec(spec)
    output_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_feedback_application_report(intake, spec, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
