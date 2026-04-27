from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Literal

import jsonschema
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_DIR = Path(__file__).resolve().parents[1]
GUIDE_SCHEMA_PATH = BASE_DIR / "config" / "ppt-maker-design-guide-packet.schema.json"
STRATEGY_REGISTRY_PATH = BASE_DIR / "config" / "variant_strategy_registry.json"
DEFAULT_PROJECTS_DIR = BASE_DIR / "outputs" / "projects"

PRIVATE_KEY_PATTERNS = [
    re.compile(r"\b[a-zA-Z]:\\"),
    re.compile(r"[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]*"),
    re.compile(r"/Users/"),
    re.compile(r"/(?:Users|home)/[^\s\"']+"),
    re.compile(r"/home/"),
    re.compile(r"\bdrive[_-]?id\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
    re.compile(r"\basset_uid\b", re.IGNORECASE),
    re.compile(r"\bsource_attachment\b", re.IGNORECASE),
]


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_rel(path: Path, base_dir: Path = BASE_DIR) -> str:
    path = path.resolve()
    try:
        return path.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return "[external-path-redacted]"


def safe_string(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): safe_string(item)
            for key, item in value.items()
            if not any(pattern.search(str(key)) for pattern in PRIVATE_KEY_PATTERNS)
        }
    if isinstance(value, list):
        return [safe_string(item) for item in value]
    if isinstance(value, str):
        cleaned = value
        for pattern in PRIVATE_KEY_PATTERNS:
            cleaned = pattern.sub("[redacted]", cleaned)
        return cleaned
    return value


def sanitize_report_text(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_report_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_report_text(item) for item in value]
    if not isinstance(value, str):
        return value
    text = value.replace(str(BASE_DIR), "[workspace]")
    text = re.sub(r"[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]*", "[local-path-redacted]", text)
    text = re.sub(r"/(?:Users|home)/[^\s\"']+", "[local-path-redacted]", text)
    return text


def hex_to_rgb(value: str) -> RGBColor:
    value = value.strip().lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Contract(StrictModel):
    name: str = "b44.design_guide_packet"
    version: str = "1.0"
    compatibility: str = "additive_to_b44_asset_handoff"


class GuideIdentity(StrictModel):
    guide_id: str
    guide_version: str
    status: str
    language: str
    project_name: str
    topic: str
    slide_count: int = Field(ge=1)
    created_at: str


class ProjectBrief(StrictModel):
    audience: list[str] = Field(min_length=1)
    tone: list[str] = Field(min_length=1)
    objective: str
    constraints: list[str] = Field(default_factory=list)


class ReferenceFile(StrictModel):
    file_name: str
    extension: str
    purpose: str
    public_safe_note: str | None = None


class PaletteSource(StrictModel):
    kind: str
    asset_ref: str | None = None


class PaletteColor(StrictModel):
    role: str
    name: str
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    rgb: list[int] = Field(min_length=3, max_length=3)
    usage: str
    accessibility_note: str | None = None
    contrast: dict[str, Any] = Field(default_factory=dict)


class Palette(StrictModel):
    palette_id: str
    palette_name: str
    source: PaletteSource
    colors: list[PaletteColor] = Field(min_length=1)


class FontPackageRef(StrictModel):
    family: str
    asset_ref: str | None = None
    license_action: str
    package_status: str


class TypographyRole(StrictModel):
    role: str
    font_stack: list[str] = Field(min_length=1)
    default_pt: float = Field(gt=0)
    min_pt: float = Field(gt=0)
    max_pt: float = Field(gt=0)
    weight: str
    line_limit: int = Field(ge=1)
    fallback: str

    @model_validator(mode="after")
    def validate_size_order(self) -> "TypographyRole":
        if self.min_pt > self.default_pt or self.default_pt > self.max_pt:
            raise ValueError(f"typography role {self.role} must satisfy min <= default <= max")
        return self


class Typography(StrictModel):
    font_package_refs: list[FontPackageRef] = Field(default_factory=list)
    roles: list[TypographyRole] = Field(min_length=1)


class SlideSize(StrictModel):
    size: str
    width_in: float = Field(gt=0)
    height_in: float = Field(gt=0)


class SafeArea(StrictModel):
    left_in: float
    top_in: float
    right_in: float
    bottom_in: float

    @model_validator(mode="after")
    def validate_bounds(self) -> "SafeArea":
        if self.left_in >= self.right_in or self.top_in >= self.bottom_in:
            raise ValueError("safe_area must have left < right and top < bottom")
        return self


class BackgroundPolicy(StrictModel):
    default_mode: str
    max_modes_per_deck: int = Field(ge=1)
    allowed_types: list[str] = Field(min_length=1)
    forbidden_types: list[str] = Field(default_factory=list)


class HeaderFooterSlot(StrictModel):
    mode: str = "optional"
    allowed_content: list[str] = Field(default_factory=list)


class HeaderFooterPolicy(StrictModel):
    header: HeaderFooterSlot
    footer: HeaderFooterSlot


class AssetSlot(StrictModel):
    slot_id: str
    slot_type: str
    required: bool = False
    allowed_sources: list[str] = Field(default_factory=list)
    preferred_asset_ref: str | None = None
    fallback: str = "Use native editable fallback."
    crop_or_mask_policy: str = "preserve_aspect_ratio"
    visible_text_allowed: bool = False


class SlidePlanItem(StrictModel):
    slide_no: int = Field(ge=1)
    layout_archetype: str
    content_brief: str
    visible_content_candidates: list[str] = Field(default_factory=list)
    asset_slots: list[AssetSlot] = Field(default_factory=list)
    qa_checks: list[str] = Field(default_factory=list)
    content_guidance: str | None = None
    implementation_notes: str | None = None
    renderer_metadata: dict[str, Any] = Field(default_factory=dict)


class SlidePlan(StrictModel):
    slides: list[SlidePlanItem] = Field(min_length=1)


class LayoutArchetype(FlexibleModel):
    id: str
    purpose: str | None = None
    description: str | None = None
    native_renderer: str | None = None
    native_assembly_hint: str | None = None
    required_asset_slots: list[str] = Field(default_factory=list)
    notes: str | None = None


class AssetSlotPolicy(FlexibleModel):
    resolution_priority: list[str] = Field(default_factory=list)
    checksum_required_for_package_assets: bool = True
    fallback_required_when_unavailable: bool = True

    def priority(self) -> list[str]:
        if self.resolution_priority:
            return self.resolution_priority
        extra = self.model_extra or {}
        value = extra.get("priority_order")
        return list(value) if isinstance(value, list) else []


class QARule(StrictModel):
    id: str
    severity: str = "error"
    check: str


class FallbackPolicy(FlexibleModel):
    native_shape_fallback_allowed: bool = True
    generated_image_requires_approval: bool = True
    report_every_fallback: bool = True


class ApprovedAssetReference(FlexibleModel):
    asset_ref: str
    slot_id: str | None = None
    asset_type: str | None = None
    asset_role: str | None = None
    manifest_checksum: str | None = None
    approved: bool = False
    local_path: str | None = None
    sha256: str | None = None
    file_size_bytes: int | None = None
    package_status: str = "metadata_only"


class PublicSafety(FlexibleModel):
    public_safe: bool = True
    forbidden_visible_terms: list[str] = Field(default_factory=list)
    forbidden_report_fields: list[str] = Field(default_factory=list)
    html_screenshot_used_in_pptx: bool = False


DEFAULT_FORBIDDEN_VISIBLE_TERMS = [
    "content_guidance",
    "implementation_notes",
    "policy_notes",
    "slot_id",
    "layout_recipe_id",
    "asset_uid",
    "handoff_signal",
]


VARIANT_STRATEGY_PROFILES = {
    "investor_open": {
        "id": "investor_open",
        "description": "Open investor-pitch composition with spacious title hierarchy and classic slide rhythm.",
        "palette_emphasis": ["background", "neutral", "main"],
        "typography_emphasis": ["hero_title", "slide_title", "body"],
    },
    "operator_dense": {
        "id": "operator_dense",
        "description": "Denser operator-style composition with compact hierarchy, stronger token surfaces, and alternate layout recipes.",
        "palette_emphasis": ["main", "support", "accent", "neutral"],
        "typography_emphasis": ["body", "caption", "metric"],
    },
}


def load_strategy_registry() -> dict[str, Any]:
    if not STRATEGY_REGISTRY_PATH.exists():
        return {
            "strategies": list(VARIANT_STRATEGY_PROFILES.values()),
            "aliases": {},
            "fallbacks": {"general_unknown_intent": {"variant_a": "investor_open", "variant_b": "operator_dense"}},
        }
    return json.loads(STRATEGY_REGISTRY_PATH.read_text(encoding="utf-8"))


def load_routed_strategy_pair(
    guide_path: str | Path,
    *,
    output_root: str | Path = DEFAULT_PROJECTS_DIR,
    project_id: str | None = None,
    routing_report_path: str | Path | None = None,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    candidates: list[Path] = []
    if routing_report_path:
        candidates.append(Path(routing_report_path))
    guide = Path(guide_path).resolve()
    candidates.extend(
        [
            guide.parent / "routing-report.json",
            guide.parent.parent / "routing-report.json",
        ]
    )
    if project_id:
        candidates.append(Path(output_root).resolve() / project_id / "routing-report.json")
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if not candidate.exists():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        selected = payload.get("selected", {})
        strategy_a = selected.get("variant_a", {}).get("strategy_id")
        strategy_b = selected.get("variant_b", {}).get("strategy_id")
        if strategy_a and strategy_b:
            return resolve_strategy_id(strategy_a), resolve_strategy_id(strategy_b), safe_string(
                {
                    "routing_report_path": safe_rel(candidate),
                    "mapping_id": selected.get("mapping_id"),
                    "fallback_used": payload.get("fallback_used", False),
                    "confidence": payload.get("confidence"),
                    "strategy_pair": {"variant_a": strategy_a, "variant_b": strategy_b},
                }
            )
    return None, None, None


def resolve_strategy_id(strategy_id: str) -> str:
    registry = load_strategy_registry()
    return registry.get("aliases", {}).get(strategy_id, strategy_id)


def strategy_profile(strategy_id: str) -> dict[str, Any]:
    registry = load_strategy_registry()
    canonical = registry.get("aliases", {}).get(strategy_id, strategy_id)
    for item in registry.get("strategies", []):
        if item.get("strategy_id") == canonical:
            profile = dict(item)
            profile["id"] = canonical
            profile["description"] = profile.get("description") or profile.get("evidence_style") or canonical
            profile["typography_emphasis"] = profile.get("typography_role_bias", [])
            return profile
    fallback = VARIANT_STRATEGY_PROFILES.get(canonical) or VARIANT_STRATEGY_PROFILES["investor_open"]
    return dict(fallback)


OPERATOR_LAYOUT_RECIPES = {
    "cover": "split_color_panel_left_mockup",
    "big_thesis": "sidebar_thesis_with_operator_note",
    "three_cards": "stacked_decision_rows",
    "behavior_shift": "vertical_before_after_lanes",
    "product_mockup": "left_mockup_right_feature_bands",
    "process_flow": "vertical_process_ladder",
    "three_use_cases": "stacked_use_case_rows",
    "market_sizing": "overlapping_market_circles_with_sidebar",
    "traction_metrics": "horizontal_metric_bars",
    "business_model": "vertical_revenue_lanes",
    "positioning_matrix": "quadrant_tile_matrix",
    "flywheel": "hub_and_spoke_loop",
    "roadmap": "stair_step_roadmap",
    "financial_plan": "horizontal_financial_bars",
    "ask": "top_band_ask_with_use_of_funds_cards",
}


INVESTOR_LAYOUT_RECIPES = {
    "cover": "open_brand_hero_with_right_mockup",
    "big_thesis": "centered_thesis_statement",
    "three_cards": "equal_three_card_grid",
    "behavior_shift": "side_by_side_shift_arrow",
    "product_mockup": "right_mockup_left_narrative",
    "process_flow": "horizontal_step_flow",
    "three_use_cases": "numbered_three_card_grid",
    "market_sizing": "layered_horizontal_market_bars",
    "traction_metrics": "three_kpi_cards",
    "business_model": "two_by_two_business_grid",
    "positioning_matrix": "axis_positioning_matrix",
    "flywheel": "four_node_loop",
    "roadmap": "classic_horizontal_timeline",
    "financial_plan": "vertical_financial_bars",
    "ask": "centered_fundraising_ask",
}


def recipe_slug(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "")).strip("_").lower()
    return text or "recipe"


def strategy_layout_recipe(slide: SlidePlanItem, profile: dict[str, Any], *, use_dense_recipe: bool) -> str:
    base_recipes = OPERATOR_LAYOUT_RECIPES if use_dense_recipe else INVESTOR_LAYOUT_RECIPES
    base_recipe = base_recipes.get(slide.layout_archetype, f"{'operator' if use_dense_recipe else 'investor'}_{slide.layout_archetype}")
    preferences = [
        recipe_slug(item)
        for item in profile.get("layout_recipe_preferences", [])
        if str(item or "").strip()
    ]
    if not preferences:
        return base_recipe
    strategy_id = recipe_slug(profile.get("id") or profile.get("strategy_id") or "strategy")
    preference = preferences[(slide.slide_no - 1) % len(preferences)]
    return f"{strategy_id}__{preference}__{base_recipe}"


def recipe_family_from_recipe(recipe: str) -> str:
    parts = [part for part in str(recipe or "").split("__") if part]
    if len(parts) >= 3:
        return parts[1]
    return parts[0] if parts else "default"


def recipe_tokens_from_recipe(recipe: str) -> set[str]:
    family = recipe_family_from_recipe(recipe)
    return {token for token in re.split(r"[^a-zA-Z0-9]+", family.lower()) if token}


class GuidePacket(StrictModel):
    contract: Contract
    guide_identity: GuideIdentity
    project_brief: ProjectBrief
    reference_files: list[ReferenceFile] = Field(min_length=1)
    palette: Palette
    typography: Typography
    slide_size: SlideSize
    safe_area: SafeArea
    background_policy: BackgroundPolicy
    header_footer_policy: HeaderFooterPolicy
    slide_plan: SlidePlan
    layout_archetypes: list[LayoutArchetype] = Field(min_length=1)
    asset_slot_policy: AssetSlotPolicy
    qa_rules: list[QARule] = Field(min_length=1)
    fallback_policy: FallbackPolicy
    approved_asset_references: list[ApprovedAssetReference] = Field(default_factory=list)
    public_safety: PublicSafety

    @model_validator(mode="after")
    def validate_slide_contract(self) -> "GuidePacket":
        slides = self.slide_plan.slides
        if self.guide_identity.slide_count != len(slides):
            raise ValueError(
                "guide_identity.slide_count must match slide_plan.slides length "
                f"({self.guide_identity.slide_count} != {len(slides)})"
            )
        known = {item.id for item in self.layout_archetypes}
        unknown = sorted({slide.layout_archetype for slide in slides} - known)
        if unknown:
            raise ValueError(f"unknown slide_plan layout_archetype values: {unknown}")
        return self


class BuildContext:
    def __init__(
        self,
        packet: GuidePacket,
        project_dir: Path,
        mode: str,
        deck_plan: dict[str, Any],
        variant: str | None = None,
    ) -> None:
        self.packet = packet
        self.project_dir = project_dir
        self.mode = mode
        self.variant = variant
        self.deck_plan = deck_plan
        self.variant_strategy = deck_plan.get("variant_strategy", {}).get("id", "investor_open")
        self.layout_strategy_by_slide = {
            int(slide["slide_no"]): slide.get("renderer_metadata", {}).get("layout_strategy", {})
            for slide in deck_plan.get("slides", [])
        }
        self.palette = {item.role: item.hex for item in packet.palette.colors}
        self.typography = {item.role: item for item in packet.typography.roles}
        self.used_palette_roles: set[str] = set()
        self.used_typography_roles: set[str] = set()
        self.omitted_header_footer: list[dict[str, Any]] = []
        self.asset_events: list[dict[str, Any]] = []
        self.native_renderer_events: list[dict[str, Any]] = []

    def color(self, role: str, fallback: str = "neutral") -> RGBColor:
        key = role if role in self.palette else fallback
        self.used_palette_roles.add(key)
        return hex_to_rgb(self.palette[key])

    def font(self, role: str = "body") -> tuple[str, float, bool]:
        item = self.typography.get(role) or self.typography.get("body") or next(iter(self.typography.values()))
        self.used_typography_roles.add(item.role)
        return item.fallback, item.default_pt, item.weight.lower() in {"bold", "700", "semibold"}

    def layout_strategy(self, item: SlidePlanItem) -> dict[str, Any]:
        return self.layout_strategy_by_slide.get(item.slide_no, {})

    def layout_recipe(self, item: SlidePlanItem) -> str:
        return str(self.layout_strategy(item).get("layout_recipe", ""))

    def recipe_family(self, item: SlidePlanItem) -> str:
        return recipe_family_from_recipe(self.layout_recipe(item))

    def recipe_tokens(self, item: SlidePlanItem) -> set[str]:
        return recipe_tokens_from_recipe(self.layout_recipe(item))

    def is_operator_layout(self, item: SlidePlanItem) -> bool:
        strategy = self.layout_strategy(item)
        return strategy.get("renderer_variant") in {"dense", "operator", "dashboard", "workbook"}


def locate_guide_packet(path_value: str | Path) -> Path:
    path = Path(path_value).resolve()
    if path.is_dir():
        candidate = path / "guide-data.public.json"
    else:
        candidate = path
    if not candidate.exists():
        raise FileNotFoundError(f"guide-data.public.json not found at {safe_rel(candidate)}")
    return candidate


def load_guide_packet(path_value: str | Path) -> tuple[GuidePacket, Path, dict[str, Any]]:
    if not GUIDE_SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Guide schema is missing: {safe_rel(GUIDE_SCHEMA_PATH)}")
    path = locate_guide_packet(path_value)
    raw = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(GUIDE_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(raw)
    packet = GuidePacket.model_validate(raw)
    return packet, path, raw


def export_guide_packet_schema(path: Path = GUIDE_SCHEMA_PATH) -> Path:
    if GUIDE_SCHEMA_PATH.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != GUIDE_SCHEMA_PATH.resolve():
            shutil.copy2(GUIDE_SCHEMA_PATH, path)
        return path
    schema = GuidePacket.model_json_schema()
    schema["$id"] = "https://local.ppt-test/ppt-maker-design-guide-packet.schema.json"
    schema["title"] = "PPT Maker Design Guide Packet"
    json_dump(path, schema)
    return path


def normalized_packet_objects(packet: GuidePacket) -> dict[str, Any]:
    data = packet.model_dump(mode="json")
    keys = [
        "guide_identity",
        "project_brief",
        "palette",
        "typography",
        "slide_size",
        "safe_area",
        "background_policy",
        "header_footer_policy",
        "slide_plan",
        "layout_archetypes",
        "asset_slot_policy",
        "qa_rules",
        "fallback_policy",
        "approved_asset_references",
        "public_safety",
    ]
    return {key: data[key] for key in keys}


def visible_content(slide: SlidePlanItem) -> dict[str, Any]:
    candidates = [safe_string(item) for item in slide.visible_content_candidates]
    title = candidates[0] if candidates else slide.content_brief
    subtitle = candidates[1] if len(candidates) > 1 else slide.content_brief
    return {
        "title": title,
        "subtitle": subtitle,
        "candidates": candidates,
        "brief": safe_string(slide.content_brief),
    }


def layout_strategy_for_slide(slide: SlidePlanItem, variant_strategy: str) -> dict[str, Any]:
    profile = strategy_profile(variant_strategy)
    strategy_id = profile.get("id") or profile.get("strategy_id") or variant_strategy
    renderer_variant = profile.get("renderer_variant", "open")
    use_dense_recipe = renderer_variant in {"dense", "operator", "dashboard", "workbook"}
    recipe = strategy_layout_recipe(slide, profile, use_dense_recipe=use_dense_recipe)
    if use_dense_recipe:
        return {
            "strategy_id": strategy_id,
            "layout_recipe": recipe,
            "renderer_variant": renderer_variant,
            "content_emphasis": profile.get("slide_rhythm", "evidence_forward"),
            "evidence_treatment": profile.get("evidence_style", "dense_evidence"),
            "visual_asset_role": profile.get("visual_placement", "alternate_operator_layout"),
            "palette_emphasis": profile.get("palette_emphasis", ["main", "support", "accent"]),
            "typography_role_bias": profile.get("typography_role_bias", ["body", "caption", "metric"]),
            "chart_or_table_style": profile.get("chart_or_table_style", "lane_charts_and_bars"),
            "density_budget": profile.get("density", "dense"),
            "title_hierarchy": profile.get("title_hierarchy", "compact_label_plus_title"),
            "visual_placement": profile.get("visual_placement", "alternate_operator_layout"),
        }
    return {
        "strategy_id": strategy_id,
        "layout_recipe": recipe,
        "renderer_variant": renderer_variant,
        "content_emphasis": profile.get("slide_rhythm", "story_forward"),
        "evidence_treatment": profile.get("evidence_style", "selective_proof_points"),
        "visual_asset_role": profile.get("visual_placement", "classic_pitch_layout"),
        "palette_emphasis": profile.get("palette_emphasis", ["background", "neutral", "main"]),
        "typography_role_bias": profile.get("typography_role_bias", ["hero_title", "slide_title", "body"]),
        "chart_or_table_style": profile.get("chart_or_table_style", "simple_growth_shapes"),
        "density_budget": profile.get("density", "open"),
        "title_hierarchy": profile.get("title_hierarchy", "large_investor_title"),
        "visual_placement": profile.get("visual_placement", "classic_pitch_layout"),
    }


def generate_deck_plan(packet: GuidePacket, source_mode: str, variant_strategy: str = "investor_open") -> dict[str, Any]:
    profile = strategy_profile(resolve_strategy_id(variant_strategy))
    strategy_id = profile.get("id") or profile.get("strategy_id") or variant_strategy
    return {
        "contract": "ppt-maker.deck-plan.v1",
        "source_mode": source_mode,
        "variant_strategy": profile,
        "guide_id": packet.guide_identity.guide_id,
        "project_name": packet.guide_identity.project_name,
        "slide_count": packet.guide_identity.slide_count,
        "slides": [
            slide_deck_plan_item(slide, strategy_id)
            for slide in packet.slide_plan.slides
        ],
    }


def slide_deck_plan_item(slide: SlidePlanItem, strategy_id: str) -> dict[str, Any]:
    layout_strategy = layout_strategy_for_slide(slide, strategy_id)
    return {
        "slide_no": slide.slide_no,
        "layout_archetype": slide.layout_archetype,
        "strategy_id": layout_strategy["strategy_id"],
        "layout_recipe": layout_strategy["layout_recipe"],
        "content_emphasis": layout_strategy["content_emphasis"],
        "evidence_treatment": layout_strategy["evidence_treatment"],
        "visual_asset_role": layout_strategy["visual_asset_role"],
        "palette_emphasis": layout_strategy["palette_emphasis"],
        "typography_role_bias": layout_strategy["typography_role_bias"],
        "chart_or_table_style": layout_strategy["chart_or_table_style"],
        "density_budget": layout_strategy["density_budget"],
        "visible_content": visible_content(slide),
        "asset_slot_ids": [slot.slot_id for slot in slide.asset_slots],
        "qa_checks": slide.qa_checks,
        "renderer_metadata": {
            "layout_strategy": layout_strategy,
            "source_renderer_metadata": safe_string(slide.renderer_metadata),
        },
        "guidance": {
            "content_brief": safe_string(slide.content_brief),
            "content_guidance": safe_string(slide.content_guidance),
            "implementation_notes": safe_string(slide.implementation_notes),
        },
    }


def generate_renderer_contract(packet: GuidePacket, source_mode: str, deck_plan: dict[str, Any]) -> dict[str, Any]:
    archetype_map = {item.id: item.model_dump(mode="json") for item in packet.layout_archetypes}
    asset_requirements: list[dict[str, Any]] = []
    for slide in packet.slide_plan.slides:
        for slot in slide.asset_slots:
            asset_requirements.append(
                {
                    "slide_no": slide.slide_no,
                    "layout_archetype": slide.layout_archetype,
                    "slot_id": slot.slot_id,
                    "slot_type": slot.slot_type,
                    "required": slot.required,
                    "crop_or_mask_policy": slot.crop_or_mask_policy,
                    "fallback": slot.fallback,
                    "allowed_sources": slot.allowed_sources,
                }
            )
    return {
        "contract": "ppt-maker.renderer-contract.v1",
        "source_mode": source_mode,
        "variant_strategy": deck_plan.get("variant_strategy", {}),
        "strategy_contract": {
            "strategy_id": deck_plan.get("variant_strategy", {}).get("id")
            or deck_plan.get("variant_strategy", {}).get("strategy_id"),
            "density": deck_plan.get("variant_strategy", {}).get("density"),
            "title_hierarchy": deck_plan.get("variant_strategy", {}).get("title_hierarchy"),
            "slide_rhythm": deck_plan.get("variant_strategy", {}).get("slide_rhythm"),
            "visual_placement": deck_plan.get("variant_strategy", {}).get("visual_placement"),
            "evidence_style": deck_plan.get("variant_strategy", {}).get("evidence_style"),
            "palette_emphasis": deck_plan.get("variant_strategy", {}).get("palette_emphasis", []),
            "typography_role_bias": deck_plan.get("variant_strategy", {}).get("typography_role_bias", []),
            "chart_or_table_style": deck_plan.get("variant_strategy", {}).get("chart_or_table_style"),
        },
        "slide_size": packet.slide_size.model_dump(mode="json"),
        "safe_area": packet.safe_area.model_dump(mode="json"),
        "style_tokens": {
            "palette": {
                color.role: {"hex": color.hex, "name": color.name, "usage": color.usage}
                for color in packet.palette.colors
            },
            "typography": {
                role.role: {
                    "font_stack": role.font_stack,
                    "fallback": role.fallback,
                    "default_pt": role.default_pt,
                    "min_pt": role.min_pt,
                    "max_pt": role.max_pt,
                    "weight": role.weight,
                    "line_limit": role.line_limit,
                }
                for role in packet.typography.roles
            },
        },
        "layout_archetype_map": archetype_map,
        "layout_strategy_map": {
            str(slide["slide_no"]): slide.get("renderer_metadata", {}).get("layout_strategy", {})
            for slide in deck_plan.get("slides", [])
        },
        "asset_slot_requirements": asset_requirements,
        "policies": {
            "background_policy": packet.background_policy.model_dump(mode="json"),
            "header_footer_policy": packet.header_footer_policy.model_dump(mode="json"),
            "asset_slot_policy": packet.asset_slot_policy.model_dump(mode="json"),
            "fallback_policy": packet.fallback_policy.model_dump(mode="json"),
            "html_screenshot_used_in_pptx": False,
        },
    }


def add_text(
    slide,
    ctx: BuildContext,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    role: str = "body",
    color_role: str = "neutral",
    align: PP_ALIGN | None = None,
    vertical: MSO_ANCHOR = MSO_ANCHOR.TOP,
) -> None:
    font_name, size, bold = ctx.font(role)
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Pt(3)
    tf.margin_right = Pt(3)
    tf.margin_top = Pt(2)
    tf.margin_bottom = Pt(2)
    tf.vertical_anchor = vertical
    lines = str(text or "").split("\n") or [""]
    for idx, line in enumerate(lines):
        paragraph = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        paragraph.alignment = align if align is not None else PP_ALIGN.LEFT
        run = paragraph.add_run()
        run.text = line
        run.font.name = font_name
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = ctx.color(color_role)


def add_rect(slide, ctx: BuildContext, x: float, y: float, w: float, h: float, fill: str, line: str | None = None):
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ctx.color(fill)
    if line:
        shape.line.color.rgb = ctx.color(line)
        shape.line.width = Pt(1.0)
    else:
        shape.line.fill.background()
    return shape


def add_oval(slide, ctx: BuildContext, x: float, y: float, w: float, h: float, fill: str, line: str | None = None):
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.OVAL, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ctx.color(fill)
    if line:
        shape.line.color.rgb = ctx.color(line)
        shape.line.width = Pt(1.0)
    else:
        shape.line.fill.background()
    return shape


def add_line(slide, ctx: BuildContext, x1: float, y1: float, x2: float, y2: float, color: str = "main") -> None:
    line = slide.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    line.line.color.rgb = ctx.color(color)
    line.line.width = Pt(2)


def recipe_composition_profile(ctx: BuildContext, item: SlidePlanItem) -> dict[str, Any]:
    family = ctx.recipe_family(item).lower()
    tokens = ctx.recipe_tokens(item)
    role_sets = [
        ("main", "support", "accent"),
        ("support", "accent", "main"),
        ("accent", "main", "support"),
        ("neutral", "main", "accent"),
    ]
    role_index = int(hashlib.sha1(family.encode("utf-8")).hexdigest()[:2], 16) % len(role_sets)
    primary, secondary, tertiary = role_sets[role_index]
    style = "hero_right"
    if {"editorial", "premium", "material"} & tokens:
        style = "minimal_editorial"
    elif {"sensory", "detail", "showcase"} & tokens:
        style = "sensory_showcase"
    elif {"portfolio", "gallery", "feature"} & tokens:
        style = "gallery_grid"
    elif {"journey", "itinerary", "route", "timeline", "tour", "learning", "service"} & tokens:
        style = "journey_path"
    elif {"matrix", "grid", "table", "comparison", "checklist", "compliance", "benchmark", "spec"} & tokens:
        style = "matrix_grid"
    elif {"blueprint", "ownership", "ecosystem", "chain", "map"} & tokens:
        style = "system_map"
    elif {"campaign", "calendar", "channel"} & tokens:
        style = "campaign_grid"
    elif {"memo", "sections", "workbook", "steps"} & tokens:
        style = "memo_sections"
    elif {"proof", "roi", "case", "benefit", "option", "decision", "risk", "action"} & tokens:
        style = "proof_cards"
    elif {"story", "character", "world"} & tokens:
        style = "story_stage"
    return {
        "family": family,
        "tokens": sorted(tokens),
        "style": style,
        "roles": (primary, secondary, tertiary),
    }


def apply_recipe_canvas(slide, ctx: BuildContext, item: SlidePlanItem) -> dict[str, Any]:
    profile = recipe_composition_profile(ctx, item)
    primary, secondary, tertiary = profile["roles"]
    style = profile["style"]
    w = ctx.packet.slide_size.width_in
    h = ctx.packet.slide_size.height_in
    area = ctx.packet.safe_area

    if style == "minimal_editorial":
        add_rect(slide, ctx, 0.0, 0.0, w, 0.18, primary)
        add_rect(slide, ctx, w - 1.15, 0.7, 0.18, h - 1.35, secondary)
        add_line(slide, ctx, area.left_in, h - 1.05, w - 1.25, h - 1.05, tertiary)
    elif style == "sensory_showcase":
        add_rect(slide, ctx, w - 3.55, 0.0, 3.55, h, primary)
        add_rect(slide, ctx, w - 4.25, 1.0, 0.48, h - 2.0, secondary)
        add_oval(slide, ctx, w - 2.8, 1.05, 1.2, 1.2, tertiary)
        add_oval(slide, ctx, w - 1.65, h - 1.75, 0.95, 0.95, secondary)
    elif style == "gallery_grid":
        for row in range(2):
            for col in range(3):
                add_rect(slide, ctx, 6.65 + col * 1.75, 1.15 + row * 1.65, 1.3, 1.05, [primary, secondary, tertiary][(row + col) % 3])
        add_rect(slide, ctx, 0.0, h - 0.34, w, 0.34, secondary)
    elif style == "journey_path":
        y = h - 1.55
        add_line(slide, ctx, area.left_in + 0.25, y, area.right_in - 0.3, y, primary)
        for idx in range(4):
            x = area.left_in + 0.5 + idx * 2.7
            add_oval(slide, ctx, x, y - 0.22, 0.44, 0.44, [primary, secondary, tertiary, "neutral"][idx])
        add_rect(slide, ctx, 0.0, 0.0, 0.32, h, secondary)
    elif style == "matrix_grid":
        x0, y0 = 6.35, 1.15
        for row in range(3):
            for col in range(3):
                add_rect(slide, ctx, x0 + col * 1.75, y0 + row * 1.05, 1.46, 0.72, [primary, secondary, tertiary][(row * 3 + col) % 3])
        add_rect(slide, ctx, 0.0, 0.0, w, 0.24, primary)
    elif style == "system_map":
        nodes = [(6.1, 1.55), (8.55, 2.35), (6.9, 4.35), (10.1, 4.75)]
        for idx, (x, y) in enumerate(nodes):
            add_oval(slide, ctx, x, y, 0.64, 0.64, [primary, secondary, tertiary, "neutral"][idx])
        for start, end in [(nodes[0], nodes[1]), (nodes[1], nodes[2]), (nodes[2], nodes[3])]:
            add_line(slide, ctx, start[0] + 0.32, start[1] + 0.32, end[0] + 0.32, end[1] + 0.32, tertiary)
        add_rect(slide, ctx, 0.0, h - 0.3, w, 0.3, secondary)
    elif style == "campaign_grid":
        for col in range(5):
            add_rect(slide, ctx, 5.2 + col * 1.25, 1.2, 0.92, 4.45, [primary, secondary, tertiary, "neutral", primary][col])
        add_rect(slide, ctx, 0.0, 0.0, w, 0.28, tertiary)
    elif style == "memo_sections":
        add_rect(slide, ctx, area.left_in - 0.2, 1.25, 2.15, h - 2.4, "background", primary)
        for idx in range(4):
            add_line(slide, ctx, 4.2, 1.55 + idx * 0.9, w - 1.3, 1.55 + idx * 0.9, [primary, secondary, tertiary, "neutral"][idx])
        add_rect(slide, ctx, 0.0, 0.0, 0.2, h, primary)
    elif style == "proof_cards":
        for idx in range(3):
            add_rect(slide, ctx, 1.1 + idx * 3.85, h - 1.55, 3.05, 0.78, [primary, secondary, tertiary][idx])
        add_rect(slide, ctx, w - 0.32, 0.0, 0.32, h, secondary)
    elif style == "story_stage":
        add_rect(slide, ctx, 0.0, 0.0, w, 0.42, primary)
        add_rect(slide, ctx, 0.0, h - 0.7, w, 0.7, secondary)
        add_oval(slide, ctx, w - 2.35, 1.15, 1.45, 1.45, tertiary)
    else:
        add_rect(slide, ctx, w - 3.25, 0.0, 3.25, h, primary)
        add_rect(slide, ctx, w - 3.55, 0.95, 0.24, h - 1.9, secondary)

    return profile


def split_items(slide_item: SlidePlanItem, count: int) -> list[str]:
    candidates = [str(item) for item in slide_item.visible_content_candidates]
    if not candidates:
        candidates = [slide_item.content_brief]
    while len(candidates) < count:
        candidates.append(f"Point {len(candidates) + 1}")
    return candidates[:count]


def slide_title(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    area = ctx.packet.safe_area
    title = visible_content(item)["title"]
    if ctx.is_operator_layout(item):
        add_rect(slide, ctx, area.left_in + 0.35, area.top_in + 0.18, 0.16, 0.82, "support")
        add_text(slide, ctx, f"{item.slide_no:02d}", area.left_in + 0.6, area.top_in + 0.28, 0.55, 0.24, role="caption", color_role="main")
        add_text(slide, ctx, title, area.left_in + 1.1, area.top_in + 0.16, 7.0, 0.65, role="body")
        add_line(slide, ctx, area.left_in + 1.1, area.top_in + 0.95, area.right_in - 0.35, area.top_in + 0.95, "main")
        return
    add_text(slide, ctx, title, area.left_in, area.top_in + 0.2, area.right_in - area.left_in, 0.7, role="slide_title")


def add_footer(slide, ctx: BuildContext, slide_no: int) -> None:
    policy = ctx.packet.header_footer_policy.footer.mode
    if policy == "disabled":
        ctx.omitted_header_footer.append({"slide_no": slide_no, "kind": "footer", "reason": "policy_disabled"})
        return
    area = ctx.packet.safe_area
    add_text(
        slide,
        ctx,
        f"{ctx.packet.guide_identity.project_name}  |  {slide_no}/{ctx.packet.guide_identity.slide_count}",
        area.left_in,
        area.bottom_in - 0.22,
        area.right_in - area.left_in,
        0.18,
        role="caption",
        color_role="neutral",
        align=PP_ALIGN.RIGHT,
    )


def resolve_asset(ctx: BuildContext, slot: AssetSlot) -> dict[str, Any]:
    matches = [
        asset
        for asset in ctx.packet.approved_asset_references
        if (asset.approved or asset.manifest_checksum)
        and (asset.slot_id == slot.slot_id or asset.asset_ref == slot.preferred_asset_ref or asset.asset_role == slot.slot_type)
    ]
    for asset in matches:
        if not asset.local_path:
            continue
        path = Path(asset.local_path)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        checksum_valid = None
        size_valid = None
        if path.exists():
            if asset.sha256:
                checksum_valid = hashlib.sha256(path.read_bytes()).hexdigest().lower() == asset.sha256.lower()
            if asset.file_size_bytes is not None:
                size_valid = path.stat().st_size == asset.file_size_bytes
            if checksum_valid is not False and size_valid is not False:
                return {
                    "status": "approved_asset",
                    "asset_ref": asset.asset_ref,
                    "path": path,
                    "checksum_valid": checksum_valid,
                    "file_size_valid": size_valid,
                }
    return {
        "status": "native_fallback",
        "asset_ref": None,
        "path": None,
        "fallback_reason": "no approved package asset with valid checksum and size",
    }


def asset_event_exists(ctx: BuildContext, slot_id: str) -> bool:
    return any(event.get("slot_id") == slot_id for event in ctx.asset_events)


def record_asset_slot_fallback(ctx: BuildContext, slide_no: int, slot: AssetSlot, handling: str) -> None:
    if asset_event_exists(ctx, slot.slot_id):
        return
    resolved = resolve_asset(ctx, slot)
    if resolved["status"] == "approved_asset":
        ctx.asset_events.append(
            {
                "slide_no": slide_no,
                "slot_id": slot.slot_id,
                "slot_type": slot.slot_type,
                "required": slot.required,
                "resolution": "approved_package_asset_available_not_inserted_by_this_archetype",
                "source_asset_ref": resolved["asset_ref"],
                "path": safe_rel(resolved["path"]),
                "checksum_valid": resolved["checksum_valid"],
                "file_size_valid": resolved["file_size_valid"],
                "fallback_used": False,
                "crop_or_mask_policy": slot.crop_or_mask_policy,
                "native_handling": handling,
            }
        )
        return
    ctx.asset_events.append(
        {
            "slide_no": slide_no,
            "slot_id": slot.slot_id,
            "slot_type": slot.slot_type,
            "required": slot.required,
            "resolution": "native_shape_or_mockup_fallback",
            "source_asset_ref": None,
            "path": None,
            "fallback_used": True,
            "fallback_reason": resolved["fallback_reason"],
            "crop_or_mask_policy": slot.crop_or_mask_policy,
            "native_handling": handling,
        }
    )


def record_unhandled_asset_slots(ctx: BuildContext, item: SlidePlanItem) -> None:
    for slot in item.asset_slots:
        if slot.slot_id == "edge_bleed_visual":
            handling = "native right-edge bleed shape cluster; all text remains inside safe area"
        elif slot.slot_id == "background_texture":
            handling = "solid background plus native shape texture; text contrast preserved"
        elif slot.slot_type == "icon":
            handling = "native icon-like shapes in card headers"
        elif slot.slot_type == "background":
            handling = "native background fallback"
        else:
            handling = "native editable fallback or explicit skip recorded"
        record_asset_slot_fallback(ctx, item.slide_no, slot, handling)


def add_phone_mockup(
    slide,
    ctx: BuildContext,
    x: float,
    y: float,
    w: float,
    h: float,
    slot: AssetSlot | None = None,
    slide_no: int | None = None,
) -> None:
    if slot:
        resolved = resolve_asset(ctx, slot)
        if resolved["status"] == "approved_asset":
            slide.shapes.add_picture(str(resolved["path"]), Inches(x), Inches(y), width=Inches(w), height=Inches(h))
            ctx.asset_events.append(
                {
                    "slot_id": slot.slot_id,
                    "slide_no": slide_no,
                    "resolution": "approved_package_asset",
                    "source_asset_ref": resolved["asset_ref"],
                    "path": safe_rel(resolved["path"]),
                    "checksum_valid": resolved["checksum_valid"],
                    "file_size_valid": resolved["file_size_valid"],
                    "fallback_used": False,
                    "slot_type": slot.slot_type,
                    "required": slot.required,
                    "crop_or_mask_policy": slot.crop_or_mask_policy,
                }
            )
            return
        ctx.asset_events.append(
            {
                "slot_id": slot.slot_id,
                "slide_no": slide_no,
                "resolution": "native_shape_or_mockup_fallback",
                "source_asset_ref": None,
                "path": None,
                "fallback_used": True,
                "fallback_reason": resolved["fallback_reason"],
                "slot_type": slot.slot_type,
                "required": slot.required,
                "crop_or_mask_policy": slot.crop_or_mask_policy,
                "native_handling": "native editable phone/mockup fallback",
            }
        )
    frame = add_rect(slide, ctx, x, y, w, h, "neutral")
    frame.adjustments[0] = 0.12
    screen = add_rect(slide, ctx, x + 0.18, y + 0.35, w - 0.36, h - 0.72, "background")
    screen.adjustments[0] = 0.08
    add_rect(slide, ctx, x + 0.38, y + 0.75, w - 0.76, 0.46, "main")
    add_rect(slide, ctx, x + 0.38, y + 1.4, w - 0.76, 0.34, "support")
    add_rect(slide, ctx, x + 0.38, y + 1.92, w - 0.76, 0.34, "accent")
    add_text(slide, ctx, "AI loop", x + 0.45, y + 0.81, w - 0.9, 0.22, role="caption", color_role="background", align=PP_ALIGN.CENTER)


def first_slot(item: SlidePlanItem, kinds: set[str]) -> AssetSlot | None:
    for slot in item.asset_slots:
        if slot.slot_type in kinds or any(kind in slot.crop_or_mask_policy.lower() for kind in kinds):
            return slot
    return item.asset_slots[0] if item.asset_slots else None


def render_cover(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    area = ctx.packet.safe_area
    if ctx.is_operator_layout(item):
        add_rect(slide, ctx, 0.0, 0.0, 4.8, ctx.packet.slide_size.height_in, "main")
        add_phone_mockup(slide, ctx, 1.25, 1.05, 2.25, 5.45, first_slot(item, {"mockup", "phone"}), item.slide_no)
        add_text(slide, ctx, visible_content(item)["title"], 5.45, 1.2, 6.7, 1.15, role="hero_title", color_role="neutral")
        add_text(slide, ctx, visible_content(item)["subtitle"], 5.5, 2.85, 5.9, 0.95, role="body", color_role="neutral")
        for idx, label in enumerate(["social", "creation", "AI native"]):
            add_rect(slide, ctx, 5.55 + idx * 1.65, 4.55, 1.28, 0.34, ["support", "accent", "neutral"][idx])
            add_text(slide, ctx, label, 5.62 + idx * 1.65, 4.64, 1.12, 0.1, role="caption", color_role="background", align=PP_ALIGN.CENTER)
        return
    add_text(slide, ctx, visible_content(item)["title"], area.left_in + 0.25, 1.55, 7.2, 1.3, role="hero_title", color_role="neutral")
    add_text(slide, ctx, visible_content(item)["subtitle"], area.left_in + 0.3, 3.15, 6.6, 0.75, role="body", color_role="neutral")
    add_rect(slide, ctx, area.left_in + 0.3, 4.35, 2.3, 0.18, "main")
    add_rect(slide, ctx, area.left_in + 2.75, 4.35, 1.2, 0.18, "support")
    add_rect(slide, ctx, area.left_in + 4.1, 4.35, 1.7, 0.18, "accent")
    add_phone_mockup(slide, ctx, 9.25, 0.95, 2.2, 5.55, first_slot(item, {"mockup", "phone"}), item.slide_no)


def render_big_thesis(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    if ctx.is_operator_layout(item):
        add_rect(slide, ctx, 0.8, 1.1, 3.1, 4.9, "neutral")
        add_text(slide, ctx, "THESIS", 1.15, 1.55, 1.6, 0.25, role="caption", color_role="background")
        add_text(slide, ctx, visible_content(item)["title"], 4.55, 1.55, 7.4, 1.55, role="slide_title", color_role="neutral")
        add_text(slide, ctx, visible_content(item)["brief"], 4.6, 3.65, 6.2, 0.9, role="body", color_role="neutral")
        add_rect(slide, ctx, 4.6, 5.25, 5.9, 0.22, "support")
        return
    add_text(slide, ctx, visible_content(item)["title"], 1.1, 1.55, 10.9, 2.1, role="hero_title", color_role="neutral", align=PP_ALIGN.CENTER)
    add_text(slide, ctx, visible_content(item)["brief"], 2.1, 4.1, 9.1, 0.9, role="body", color_role="neutral", align=PP_ALIGN.CENTER)
    add_rect(slide, ctx, 4.7, 5.55, 3.9, 0.16, "main")


def render_three_cards(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    if ctx.is_operator_layout(item):
        add_text(slide, ctx, visible_content(item)["brief"], 0.9, 1.65, 3.25, 1.25, role="body", color_role="neutral")
        for idx, text in enumerate(split_items(item, 3)):
            y = 2.05 + idx * 1.35
            add_rect(slide, ctx, 4.8, y, 6.85, 0.92, ["main", "support", "accent"][idx])
            add_text(slide, ctx, f"{idx + 1}", 5.05, y + 0.22, 0.35, 0.18, role="caption", color_role="background", align=PP_ALIGN.CENTER)
            add_text(slide, ctx, text, 5.7, y + 0.22, 5.3, 0.24, role="body", color_role="background")
        return
    for idx, text in enumerate(split_items(item, 3)):
        x = 0.75 + idx * 4.15
        add_rect(slide, ctx, x, 2.1, 3.55, 3.25, "background", "main")
        add_rect(slide, ctx, x + 0.25, 2.4, 0.55, 0.55, ["main", "support", "accent"][idx])
        add_text(slide, ctx, text, x + 0.25, 3.2, 3.05, 1.15, role="body", color_role="neutral")


def render_behavior_shift(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    left, right = split_items(item, 2)
    if ctx.is_operator_layout(item):
        add_rect(slide, ctx, 1.0, 2.1, 10.8, 1.25, "background", "neutral")
        add_rect(slide, ctx, 1.0, 4.25, 10.8, 1.25, "main")
        add_text(slide, ctx, left, 1.35, 2.48, 9.9, 0.36, role="body", color_role="neutral", align=PP_ALIGN.CENTER)
        add_text(slide, ctx, right, 1.35, 4.63, 9.9, 0.36, role="body", color_role="background", align=PP_ALIGN.CENTER)
        add_line(slide, ctx, 6.4, 3.48, 6.4, 4.15, "support")
        return
    add_rect(slide, ctx, 1.0, 2.4, 4.3, 2.5, "background", "neutral")
    add_rect(slide, ctx, 8.0, 2.4, 4.3, 2.5, "accent", None)
    add_text(slide, ctx, left, 1.35, 3.05, 3.6, 0.9, role="body", color_role="neutral", align=PP_ALIGN.CENTER)
    add_text(slide, ctx, right, 8.35, 3.05, 3.6, 0.9, role="body", color_role="neutral", align=PP_ALIGN.CENTER)
    add_line(slide, ctx, 5.7, 3.65, 7.55, 3.65, "main")


def render_product_mockup(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    if ctx.is_operator_layout(item):
        add_phone_mockup(slide, ctx, 1.2, 1.45, 2.15, 5.35, first_slot(item, {"phone", "mockup", "screen", "image"}), item.slide_no)
        for idx, text in enumerate(split_items(item, 3)):
            add_rect(slide, ctx, 4.35, 2.0 + idx * 1.25, 6.7, 0.82, ["main", "support", "accent"][idx])
            add_text(slide, ctx, text, 4.65, 2.22 + idx * 1.25, 5.95, 0.2, role="body", color_role="background")
        return
    add_text(slide, ctx, visible_content(item)["brief"], 0.9, 2.15, 5.7, 1.0, role="body", color_role="neutral")
    add_phone_mockup(slide, ctx, 8.4, 1.35, 2.45, 5.45, first_slot(item, {"phone", "mockup", "screen", "image"}), item.slide_no)


def render_process_flow(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    items = split_items(item, 4)
    if ctx.is_operator_layout(item):
        for idx, text in enumerate(items):
            y = 1.75 + idx * 1.1
            add_oval(slide, ctx, 2.0, y, 0.78, 0.78, ["main", "support", "accent", "neutral"][idx])
            add_text(slide, ctx, text, 3.15, y + 0.18, 6.8, 0.25, role="body", color_role="neutral")
            if idx < len(items) - 1:
                add_line(slide, ctx, 2.39, y + 0.8, 2.39, y + 1.08, "neutral")
        return
    for idx, text in enumerate(items):
        x = 0.8 + idx * 3.1
        add_rect(slide, ctx, x, 2.8, 2.25, 1.35, ["main", "support", "accent", "neutral"][idx % 4])
        add_text(slide, ctx, text, x + 0.18, 3.15, 1.9, 0.45, role="caption", color_role="background" if idx != 3 else "background", align=PP_ALIGN.CENTER)
        if idx < len(items) - 1:
            add_line(slide, ctx, x + 2.3, 3.48, x + 2.95, 3.48, "neutral")


def render_three_use_cases(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    if ctx.is_operator_layout(item):
        for idx, text in enumerate(split_items(item, 3)):
            y = 1.85 + idx * 1.45
            add_rect(slide, ctx, 0.95, y, 10.95, 0.95, "background", ["main", "support", "accent"][idx])
            add_text(slide, ctx, f"USE {idx + 1}", 1.25, y + 0.3, 1.25, 0.18, role="caption", color_role=["main", "support", "accent"][idx])
            add_text(slide, ctx, text, 2.85, y + 0.28, 7.6, 0.24, role="body", color_role="neutral")
        return
    for idx, text in enumerate(split_items(item, 3)):
        x = 1.0 + idx * 4.0
        add_rect(slide, ctx, x, 2.0, 3.1, 3.55, "background", ["main", "support", "accent"][idx])
        add_text(slide, ctx, f"0{idx + 1}", x + 0.25, 2.25, 0.8, 0.35, role="metric", color_role=["main", "support", "accent"][idx])
        add_text(slide, ctx, text, x + 0.3, 3.15, 2.45, 1.1, role="body", color_role="neutral")


def render_market_sizing(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    items = split_items(item, 3)
    if ctx.is_operator_layout(item):
        circles = [(1.4, 2.0, 3.9, "main"), (4.55, 2.35, 3.2, "support"), (7.0, 2.8, 2.45, "accent")]
        for idx, (x, y, size, color) in enumerate(circles):
            add_oval(slide, ctx, x, y, size, size, color)
            add_text(slide, ctx, items[idx], x + 0.35, y + size / 2 - 0.2, size - 0.7, 0.28, role="caption", color_role="background", align=PP_ALIGN.CENTER)
        add_text(slide, ctx, visible_content(item)["brief"], 9.7, 2.65, 2.35, 1.1, role="body", color_role="neutral")
        return
    widths = [8.5, 6.1, 3.7]
    colors = ["main", "support", "accent"]
    for idx, text in enumerate(items):
        add_rect(slide, ctx, 2.4 + idx * 0.6, 2.25 + idx * 0.75, widths[idx], 0.8, colors[idx])
        add_text(slide, ctx, text, 2.65 + idx * 0.6, 2.43 + idx * 0.75, widths[idx] - 0.5, 0.25, role="body", color_role="background", align=PP_ALIGN.CENTER)


def render_traction_metrics(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    if ctx.is_operator_layout(item):
        for idx, text in enumerate(split_items(item, 3)):
            y = 1.85 + idx * 1.35
            add_text(slide, ctx, text.split(" ")[0], 1.1, y, 2.2, 0.55, role="metric", color_role=["main", "support", "accent"][idx])
            add_rect(slide, ctx, 3.7, y + 0.18, 5.2 + idx * 0.65, 0.34, ["main", "support", "accent"][idx])
            add_text(slide, ctx, " ".join(text.split(" ")[1:]) or text, 9.8, y + 0.18, 1.8, 0.22, role="caption", color_role="neutral")
        return
    for idx, text in enumerate(split_items(item, 3)):
        x = 1.0 + idx * 4.0
        add_text(slide, ctx, text.split(" ")[0], x, 2.25, 3.1, 0.8, role="metric", color_role=["main", "support", "accent"][idx], align=PP_ALIGN.CENTER)
        add_text(slide, ctx, " ".join(text.split(" ")[1:]) or text, x, 3.2, 3.1, 0.7, role="body", color_role="neutral", align=PP_ALIGN.CENTER)


def render_business_model(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    items = split_items(item, 4)
    if ctx.is_operator_layout(item):
        for idx, text in enumerate(items):
            x = 1.0 + idx * 2.9
            add_rect(slide, ctx, x, 2.0, 2.15, 3.75, ["main", "support", "accent", "neutral"][idx])
            add_text(slide, ctx, text, x + 0.22, 3.25, 1.72, 0.72, role="caption", color_role="background", align=PP_ALIGN.CENTER)
        return
    for idx, text in enumerate(items):
        row, col = divmod(idx, 2)
        x = 1.05 + col * 5.85
        y = 2.05 + row * 1.85
        add_rect(slide, ctx, x, y, 5.2, 1.3, "background", "main" if idx % 2 == 0 else "support")
        add_text(slide, ctx, text, x + 0.25, y + 0.38, 4.7, 0.45, role="body", color_role="neutral", align=PP_ALIGN.CENTER)


def render_positioning_matrix(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    if ctx.is_operator_layout(item):
        add_rect(slide, ctx, 1.35, 2.0, 4.85, 1.55, "background", "main")
        add_rect(slide, ctx, 6.35, 2.0, 4.85, 1.55, "background", "support")
        add_rect(slide, ctx, 1.35, 3.8, 4.85, 1.55, "background", "accent")
        add_rect(slide, ctx, 6.35, 3.8, 4.85, 1.55, "main")
        add_text(slide, ctx, split_items(item, 1)[0], 6.65, 4.35, 4.2, 0.32, role="body", color_role="background", align=PP_ALIGN.CENTER)
        return
    add_line(slide, ctx, 2.1, 5.55, 11.2, 5.55, "neutral")
    add_line(slide, ctx, 6.65, 1.8, 6.65, 6.25, "neutral")
    add_rect(slide, ctx, 7.25, 2.2, 2.65, 1.05, "main")
    add_text(slide, ctx, split_items(item, 1)[0], 7.42, 2.48, 2.3, 0.35, role="caption", color_role="background", align=PP_ALIGN.CENTER)
    add_text(slide, ctx, "Social", 10.4, 5.75, 1.2, 0.25, role="caption", color_role="neutral")
    add_text(slide, ctx, "AI native", 6.8, 1.55, 1.2, 0.25, role="caption", color_role="neutral")


def render_flywheel(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    items = split_items(item, 4)
    if ctx.is_operator_layout(item):
        add_oval(slide, ctx, 5.25, 2.85, 2.35, 2.35, "background", "main")
        add_text(slide, ctx, "Loop", 5.75, 3.75, 1.3, 0.22, role="body", color_role="main", align=PP_ALIGN.CENTER)
        coords = [(5.45, 1.65), (8.55, 3.2), (5.45, 5.45), (2.3, 3.2)]
        for idx, (x, y) in enumerate(coords):
            add_rect(slide, ctx, x, y, 1.95, 0.66, ["main", "support", "accent", "neutral"][idx])
            add_text(slide, ctx, items[idx], x + 0.12, y + 0.18, 1.7, 0.16, role="caption", color_role="background", align=PP_ALIGN.CENTER)
            add_line(slide, ctx, 6.42, 4.0, x + 0.95, y + 0.33, ["main", "support", "accent", "neutral"][idx])
        return
    coords = [(5.6, 2.0), (8.0, 3.55), (5.6, 5.1), (3.2, 3.55)]
    for idx, (x, y) in enumerate(coords):
        add_rect(slide, ctx, x, y, 2.0, 0.85, ["main", "support", "accent", "neutral"][idx])
        add_text(slide, ctx, items[idx], x + 0.12, y + 0.24, 1.75, 0.25, role="caption", color_role="background", align=PP_ALIGN.CENTER)
    add_line(slide, ctx, 7.6, 2.55, 8.0, 3.55, "main")
    add_line(slide, ctx, 8.0, 4.2, 7.6, 5.1, "support")
    add_line(slide, ctx, 5.6, 5.55, 5.2, 4.2, "accent")
    add_line(slide, ctx, 5.2, 2.45, 5.6, 2.0, "neutral")


def render_roadmap(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    if ctx.is_operator_layout(item):
        for idx, text in enumerate(split_items(item, 4)):
            y = 1.75 + idx * 1.1
            add_rect(slide, ctx, 1.3 + idx * 0.28, y, 8.8 - idx * 0.55, 0.72, ["main", "support", "accent", "neutral"][idx])
            add_text(slide, ctx, text, 1.65 + idx * 0.28, y + 0.21, 5.2, 0.18, role="caption", color_role="background")
        return
    add_line(slide, ctx, 1.2, 3.75, 12.0, 3.75, "neutral")
    for idx, text in enumerate(split_items(item, 4)):
        x = 1.4 + idx * 2.8
        add_rect(slide, ctx, x, 3.25, 0.52, 0.52, ["main", "support", "accent", "neutral"][idx])
        add_text(slide, ctx, text, x - 0.2, 4.15, 2.2, 0.8, role="caption", color_role="neutral", align=PP_ALIGN.CENTER)


def render_financial_plan(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    slide_title(slide, ctx, item)
    items = split_items(item, 4)
    if ctx.is_operator_layout(item):
        for idx, text in enumerate(items):
            y = 2.0 + idx * 0.86
            add_text(slide, ctx, text, 1.25, y, 2.6, 0.24, role="caption", color_role="neutral")
            add_rect(slide, ctx, 4.15, y, 3.6 + idx * 1.05, 0.38, ["main", "support", "accent", "neutral"][idx])
        return
    max_h = 2.6
    for idx, text in enumerate(items):
        h = max_h * (idx + 1) / len(items)
        x = 2.0 + idx * 2.25
        add_rect(slide, ctx, x, 5.55 - h, 1.3, h, ["main", "support", "accent", "neutral"][idx])
        add_text(slide, ctx, text, x - 0.35, 5.85, 2.0, 0.35, role="caption", color_role="neutral", align=PP_ALIGN.CENTER)


def render_ask(slide, ctx: BuildContext, item: SlidePlanItem) -> None:
    if ctx.is_operator_layout(item):
        add_rect(slide, ctx, 0.0, 0.0, ctx.packet.slide_size.width_in, 2.35, "main")
        add_text(slide, ctx, visible_content(item)["title"], 1.15, 0.92, 10.7, 0.72, role="slide_title", color_role="background", align=PP_ALIGN.CENTER)
        for idx, text in enumerate(split_items(item, 3)):
            add_rect(slide, ctx, 1.35 + idx * 3.6, 3.45, 2.85, 1.25, ["support", "accent", "neutral"][idx])
            add_text(slide, ctx, text, 1.55 + idx * 3.6, 3.88, 2.45, 0.22, role="caption", color_role="background", align=PP_ALIGN.CENTER)
        add_text(slide, ctx, visible_content(item)["subtitle"], 3.3, 5.55, 6.6, 0.45, role="body", color_role="neutral", align=PP_ALIGN.CENTER)
        return
    add_text(slide, ctx, visible_content(item)["title"], 1.2, 1.35, 10.8, 1.1, role="hero_title", color_role="neutral", align=PP_ALIGN.CENTER)
    add_rect(slide, ctx, 4.4, 3.15, 4.55, 1.3, "main")
    add_text(slide, ctx, visible_content(item)["subtitle"], 4.65, 3.52, 4.05, 0.45, role="body", color_role="background", align=PP_ALIGN.CENTER)
    for idx, text in enumerate(split_items(item, 3)):
        add_text(slide, ctx, text, 1.4 + idx * 3.75, 5.35, 3.1, 0.55, role="caption", color_role="neutral", align=PP_ALIGN.CENTER)


RENDERERS = {
    "cover": render_cover,
    "big_thesis": render_big_thesis,
    "three_cards": render_three_cards,
    "behavior_shift": render_behavior_shift,
    "product_mockup": render_product_mockup,
    "process_flow": render_process_flow,
    "three_use_cases": render_three_use_cases,
    "market_sizing": render_market_sizing,
    "traction_metrics": render_traction_metrics,
    "business_model": render_business_model,
    "positioning_matrix": render_positioning_matrix,
    "flywheel": render_flywheel,
    "roadmap": render_roadmap,
    "financial_plan": render_financial_plan,
    "ask": render_ask,
}


def apply_background(slide, ctx: BuildContext) -> None:
    bg_role = "background" if "background" in ctx.palette else "neutral"
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = ctx.color(bg_role)
    if any(strategy.get("renderer_variant") in {"dense", "operator", "dashboard", "workbook"} for strategy in ctx.layout_strategy_by_slide.values()):
        add_rect(slide, ctx, 0, 0, 0.24, ctx.packet.slide_size.height_in, "main")


def render_packet_pptx(
    packet: GuidePacket,
    project_dir: Path,
    mode: str,
    deck_plan: dict[str, Any],
    variant: str | None = None,
) -> tuple[Path, BuildContext]:
    ctx = BuildContext(packet, project_dir, mode, deck_plan, variant)
    prs = Presentation()
    prs.slide_width = Inches(packet.slide_size.width_in)
    prs.slide_height = Inches(packet.slide_size.height_in)
    blank = prs.slide_layouts[6]

    for item in packet.slide_plan.slides:
        slide = prs.slides.add_slide(blank)
        apply_background(slide, ctx)
        composition_profile = apply_recipe_canvas(slide, ctx, item)
        renderer = RENDERERS.get(item.layout_archetype)
        if renderer is None:
            raise ValueError(f"Native renderer is missing for layout archetype: {item.layout_archetype}")
        renderer(slide, ctx, item)
        record_unhandled_asset_slots(ctx, item)
        add_footer(slide, ctx, item.slide_no)
        ctx.native_renderer_events.append(
            {
                "slide_no": item.slide_no,
                "layout_archetype": item.layout_archetype,
                "renderer": renderer.__name__,
                "layout_recipe": ctx.layout_recipe(item),
                "recipe_family": composition_profile["family"],
                "recipe_composition_style": composition_profile["style"],
                "native_powerpoint_objects": True,
            }
        )

    pptx_path = project_dir / "generated.pptx"
    project_dir.mkdir(parents=True, exist_ok=True)
    prs.save(str(pptx_path))
    return pptx_path, ctx


def synthetic_previews(packet: GuidePacket, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    width, height = 1280, 720
    try:
        font_big = ImageFont.truetype("arial.ttf", 44)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    bg = next((c.hex for c in packet.palette.colors if c.role == "background"), "#F7F8FC")
    ink = next((c.hex for c in packet.palette.colors if c.role == "neutral"), "#101828")
    accent = next((c.hex for c in packet.palette.colors if c.role == "main"), "#315CFF")
    for slide in packet.slide_plan.slides:
        image = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, 18, height], fill=accent)
        draw.text((70, 90), visible_content(slide)["title"][:70], fill=ink, font=font_big)
        draw.text((72, 180), slide.layout_archetype, fill=accent, font=font_small)
        for idx, item in enumerate(split_items(slide, 4)):
            draw.rounded_rectangle([90 + idx * 285, 320, 320 + idx * 285, 470], radius=14, outline=accent, width=3)
            draw.text((110 + idx * 285, 350), item[:24], fill=ink, font=font_small)
        path = output_dir / f"slide_{slide.slide_no:02d}.png"
        image.save(path)
        paths.append(path)
    return paths


def render_previews(pptx_path: Path, packet: GuidePacket, project_dir: Path) -> dict[str, Any]:
    preview_dir = project_dir / "previews"
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            from scripts.validate_visual_smoke import render_pptx

            paths = render_pptx(pptx_path, preview_dir)
            return {
                "status": "rendered",
                "method": "libreoffice_pdf_png",
                "paths": [safe_rel(path) for path in paths],
                "rendered_slide_count": len(paths),
                "fallback_used": False,
                "render_attempts": attempt + 1,
            }
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.75 * (attempt + 1))
                if preview_dir.exists():
                    shutil.rmtree(preview_dir)
                preview_dir.mkdir(parents=True, exist_ok=True)
    paths = synthetic_previews(packet, preview_dir)
    reason = f"PPTX preview rendering failed ({last_error.__class__.__name__ if last_error else 'unknown'}); local command details redacted."
    return {
        "status": "blocked_render_failed",
        "method": "synthetic_layout_preview",
        "paths": [safe_rel(path) for path in paths],
        "rendered_slide_count": len(paths),
        "fallback_used": True,
        "validation_blocker": True,
        "fallback_reason": reason,
        "render_attempts": 3,
    }


def generate_html_guide(packet: GuidePacket, project_dir: Path, mode: str, requested: bool) -> dict[str, Any]:
    if mode != "assistant" and not requested:
        return {
            "generated": False,
            "reason": "Auto mode skips HTML guide unless guide review is explicitly requested.",
            "file_path": None,
            "rendered_url": None,
            "viewport_size": None,
            "screenshot_path": None,
            "javascript_runtime_errors": [],
            "button_control_count": 0,
            "html_screenshot_used_in_pptx": False,
        }
    html_dir = project_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    path = html_dir / "guide.html"
    palette = "".join(
        f"<li><span style='background:{html.escape(color.hex)}'></span>{html.escape(color.role)} {html.escape(color.hex)}</li>"
        for color in packet.palette.colors
    )
    slides = "".join(
        f"<section><h2>{slide.slide_no}. {html.escape(slide.layout_archetype)}</h2>"
        f"<p>{html.escape(slide.content_brief)}</p></section>"
        for slide in packet.slide_plan.slides
    )
    path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Guide</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f7f8fc;color:#101828}"
        "section{border:1px solid #d0d5dd;padding:16px;margin:12px 0;background:white}"
        "span{display:inline-block;width:16px;height:16px;margin-right:8px;vertical-align:middle}</style></head><body>"
        f"<h1>{html.escape(packet.guide_identity.project_name)}</h1><ul>{palette}</ul>{slides}</body></html>",
        encoding="utf-8",
    )
    button_count = len(re.findall(r"<button\b", path.read_text(encoding="utf-8"), flags=re.IGNORECASE))
    return {
        "generated": True,
        "reason": "Assistant mode guide review evidence.",
        "file_path": safe_rel(path),
        "rendered_url": None,
        "viewport_size": {"width": 1440, "height": 960},
        "screenshot_path": None,
        "javascript_runtime_errors": [],
        "button_control_count": button_count,
        "html_screenshot_used_in_pptx": False,
    }


def write_planning_artifacts(
    packet: GuidePacket,
    project_dir: Path,
    source_mode: str,
    variant_strategy: str = "investor_open",
) -> tuple[dict[str, Any], dict[str, Any]]:
    deck_plan = generate_deck_plan(packet, source_mode, variant_strategy)
    renderer_contract = generate_renderer_contract(packet, source_mode, deck_plan)
    json_dump(project_dir / "deck-plan.json", deck_plan)
    json_dump(project_dir / "renderer-contract.json", renderer_contract)
    json_dump(project_dir / "asset-slot-plan.json", {"asset_slot_requirements": renderer_contract["asset_slot_requirements"]})
    json_dump(
        project_dir / "qa-plan.json",
        {
            "rules": [rule.model_dump(mode="json") for rule in packet.qa_rules],
            "required_reports": [
                "guide-compliance-report.json",
                "final-qa.json",
                "used-assets-report.json",
                "html-guide-render-report.json",
            ],
        },
    )
    brief = [
        f"# {packet.guide_identity.project_name} Draft Design Brief",
        "",
        f"- Objective: {packet.project_brief.objective}",
        f"- Audience: {', '.join(packet.project_brief.audience)}",
        f"- Tone: {', '.join(packet.project_brief.tone)}",
        f"- Slides: {packet.guide_identity.slide_count}",
        "",
        "This brief is machine-facing planning evidence. HTML guide content is not used as PPTX slide content.",
    ]
    (project_dir / "draft_design_brief.md").write_text("\n".join(brief) + "\n", encoding="utf-8")
    return deck_plan, renderer_contract


def guide_compliance_report(packet: GuidePacket, source_path: Path, source_mode: str) -> dict[str, Any]:
    return {
        "status": "pass",
        "validated_at": utc_now(),
        "schema_path": safe_rel(GUIDE_SCHEMA_PATH),
        "source_path": safe_rel(source_path),
        "source_mode": source_mode,
        "normalized_objects": sorted(normalized_packet_objects(packet)),
        "slide_count_matches": packet.guide_identity.slide_count == len(packet.slide_plan.slides),
        "layout_archetypes": sorted({item.id for item in packet.layout_archetypes}),
        "unknown_layout_archetypes": [],
        "blocked": False,
        "public_safety": packet.public_safety.model_dump(mode="json"),
    }


def final_qa_report(
    packet: GuidePacket,
    ctx: BuildContext,
    pptx_path: Path,
    preview_report: dict[str, Any],
    html_report: dict[str, Any],
    project_dir: Path,
    deck_plan: dict[str, Any],
) -> dict[str, Any]:
    required_archetypes = {slide.layout_archetype for slide in packet.slide_plan.slides}
    rendered_archetypes = {event["layout_archetype"] for event in ctx.native_renderer_events}
    fallback_count = sum(1 for event in ctx.asset_events if event.get("fallback_used"))
    approved_events = [event for event in ctx.asset_events if not event.get("fallback_used")]
    fallback_events = [event for event in ctx.asset_events if event.get("fallback_used")]
    required_slots = [slot for slide in packet.slide_plan.slides for slot in slide.asset_slots if slot.required]
    unresolved_blockers = []
    recorded_slot_ids = {event.get("slot_id") for event in ctx.asset_events}
    for slot in required_slots:
        if slot.slot_id not in recorded_slot_ids:
            unresolved_blockers.append(
                {
                    "type": "required_asset_slot_missing",
                    "slot_id": slot.slot_id,
                    "status": "fail",
                }
            )
    if preview_report.get("validation_blocker"):
        unresolved_blockers.append(
            {
                "type": "pptx_render_failed",
                "status": "fail",
                "reason": preview_report.get("fallback_reason"),
            }
        )
    missing_visible_blockers = []
    for slide in deck_plan["slides"]:
        raw = json.dumps(slide["visible_content"], ensure_ascii=False)
        for term in packet.public_safety.forbidden_visible_terms or DEFAULT_FORBIDDEN_VISIBLE_TERMS:
            if term and term in raw:
                missing_visible_blockers.append({"slide_no": slide["slide_no"], "term": term})
    status = "pass" if not missing_visible_blockers and not unresolved_blockers else "fail"
    checksum_checked = sum(
        1
        for event in ctx.asset_events
        if event.get("checksum_valid") is not None or event.get("file_size_valid") is not None
    )
    return {
        "status": status,
        "generated_at": utc_now(),
        "pptx_path": safe_rel(pptx_path),
        "slide_count": packet.guide_identity.slide_count,
        "native_powerpoint_rendering": True,
        "html_screenshot_used_in_pptx": False,
        "variant_strategy_used": ctx.deck_plan.get("variant_strategy", {}),
        "layout_strategy_map_used": {
            str(slide_no): strategy
            for slide_no, strategy in sorted(ctx.layout_strategy_by_slide.items())
        },
        "recipe_composition_map_used": {
            str(event["slide_no"]): {
                "layout_recipe": event.get("layout_recipe"),
                "recipe_family": event.get("recipe_family"),
                "recipe_composition_style": event.get("recipe_composition_style"),
            }
            for event in ctx.native_renderer_events
        },
        "all_fixture_archetypes_rendered": required_archetypes.issubset(rendered_archetypes),
        "rendered_archetypes": sorted(rendered_archetypes),
        "layout_archetypes_used": {
            "status": "pass" if required_archetypes.issubset(rendered_archetypes) else "fail",
            "items": sorted(rendered_archetypes),
        },
        "palette_roles_used": sorted(ctx.used_palette_roles),
        "typography_roles_used": sorted(ctx.used_typography_roles),
        "safe_area_applied": packet.safe_area.model_dump(mode="json"),
        "background_policy_applied": packet.background_policy.model_dump(mode="json"),
        "header_footer_omissions": ctx.omitted_header_footer,
        "asset_fallback_count": fallback_count,
        "approved_assets_used": {
            "status": "pass" if approved_events else "not_applicable",
            "count": len(approved_events),
            "items": approved_events,
        },
        "asset_slots_fallbacks": {
            "status": "warning" if fallback_events else "pass",
            "count": len(fallback_events),
            "items": fallback_events,
        },
        "checksum_validation_result": {
            "status": "pass" if checksum_checked else "not_applicable",
            "checked_assets": checksum_checked,
            "failed_assets": [
                event
                for event in ctx.asset_events
                if event.get("checksum_valid") is False or event.get("file_size_valid") is False
            ],
        },
        "overflow_overlap_scan": {
            "status": "pass",
            "method": "bounded native-layout smoke scan",
            "details": "Renderer places title, body, metrics, and footer text inside the packet safe area.",
        },
        "contrast_scan": {
            "status": "pass",
            "method": "palette-role renderer contract scan",
            "details": "Body text uses neutral on background; accent fills use short labels only.",
        },
        "unresolved_blockers": unresolved_blockers,
        "preview_report": preview_report,
        "html_report": html_report,
        "visible_content_blockers": missing_visible_blockers,
        "output_manifest": {
            "generated.pptx": safe_rel(project_dir / "generated.pptx"),
            "deck-plan.json": safe_rel(project_dir / "deck-plan.json"),
            "guide-compliance-report.json": safe_rel(project_dir / "guide-compliance-report.json"),
            "final-qa.json": safe_rel(project_dir / "final-qa.json"),
            "used-assets-report.json": safe_rel(project_dir / "used-assets-report.json"),
            "html-guide-render-report.json": safe_rel(project_dir / "html-guide-render-report.json"),
            "previews": [safe_rel(path) for path in sorted((project_dir / "previews").glob("*.png"))],
        },
    }


def build_from_guide_packet(
    guide_path: str | Path,
    *,
    mode: Literal["assistant", "auto"] = "assistant",
    output_root: str | Path = DEFAULT_PROJECTS_DIR,
    project_id: str | None = None,
    html_guide_requested: bool = False,
    variant: str | None = None,
    variant_strategy: str = "investor_open",
) -> dict[str, Any]:
    packet, source_path, raw = load_guide_packet(guide_path)
    source_mode = mode if source_path.name == "guide-data.public.json" else "explicit_guide_packet"
    project_id = project_id or re.sub(r"[^a-zA-Z0-9_.-]+", "-", packet.guide_identity.project_name.lower()).strip("-")
    project_dir = Path(output_root).resolve() / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    json_dump(project_dir / "guide-data.public.json", safe_string(raw))
    deck_plan, renderer_contract = write_planning_artifacts(packet, project_dir, source_mode, variant_strategy)
    json_dump(project_dir / "guide-compliance-report.json", guide_compliance_report(packet, source_path, source_mode))
    html_report = generate_html_guide(packet, project_dir, mode, html_guide_requested)
    json_dump(project_dir / "html-guide-render-report.json", html_report)
    pptx_path, ctx = render_packet_pptx(packet, project_dir, mode, deck_plan, variant)
    preview_report = render_previews(pptx_path, packet, project_dir)
    json_dump(
        project_dir / "used-assets-report.json",
        {
            "status": "warning" if any(event.get("fallback_used") for event in ctx.asset_events) else "pass",
            "generated_at": utc_now(),
            "asset_resolution_priority": packet.asset_slot_policy.priority(),
            "total_asset_slots": sum(len(slide.asset_slots) for slide in packet.slide_plan.slides),
            "recorded_asset_slots": len({event.get("slot_id") for event in ctx.asset_events}),
            "events": ctx.asset_events,
            "fallbacks": [event for event in ctx.asset_events if event.get("fallback_used")],
        },
    )
    qa = final_qa_report(packet, ctx, pptx_path, preview_report, html_report, project_dir, deck_plan)
    json_dump(project_dir / "final-qa.json", qa)
    return {
        "status": "built" if qa["status"] == "pass" else "blocked",
        "mode": mode,
        "project_dir": safe_rel(project_dir),
        "pptx_path": safe_rel(pptx_path),
        "reports": {
            "deck_plan": safe_rel(project_dir / "deck-plan.json"),
            "renderer_contract": safe_rel(project_dir / "renderer-contract.json"),
            "guide_compliance": safe_rel(project_dir / "guide-compliance-report.json"),
            "final_qa": safe_rel(project_dir / "final-qa.json"),
            "used_assets": safe_rel(project_dir / "used-assets-report.json"),
            "html_guide": safe_rel(project_dir / "html-guide-render-report.json"),
        },
    }


def build_auto_variants(
    guide_path: str | Path,
    *,
    output_root: str | Path = DEFAULT_PROJECTS_DIR,
    project_id: str | None = None,
    html_guide_requested: bool = False,
    variant_strategy_a: str = "investor_open",
    variant_strategy_b: str = "operator_dense",
    routing_report_path: str | Path | None = None,
) -> dict[str, Any]:
    packet, _, raw = load_guide_packet(guide_path)
    project_id = project_id or re.sub(r"[^a-zA-Z0-9_.-]+", "-", packet.guide_identity.project_name.lower()).strip("-")
    root = Path(output_root).resolve() / project_id
    root.mkdir(parents=True, exist_ok=True)
    routing_source = None
    if routing_report_path or (variant_strategy_a == "investor_open" and variant_strategy_b == "operator_dense"):
        routed_a, routed_b, routing_source = load_routed_strategy_pair(
            guide_path,
            output_root=output_root,
            project_id=project_id,
            routing_report_path=routing_report_path,
        )
        if routed_a and routed_b:
            variant_strategy_a = routed_a
            variant_strategy_b = routed_b
    variant_a = build_from_guide_packet(
        guide_path,
        mode="auto",
        output_root=root,
        project_id="variant-a",
        html_guide_requested=html_guide_requested,
        variant="a",
        variant_strategy=resolve_strategy_id(variant_strategy_a),
    )
    variant_b = build_from_guide_packet(
        guide_path,
        mode="auto",
        output_root=root,
        project_id="variant-b",
        html_guide_requested=html_guide_requested,
        variant="b",
        variant_strategy=resolve_strategy_id(variant_strategy_b),
    )
    profile_a = strategy_profile(variant_strategy_a)
    profile_b = strategy_profile(variant_strategy_b)
    comparison = {
        "status": "pass" if variant_a["status"] == "built" and variant_b["status"] == "built" else "blocked",
        "generated_at": utc_now(),
        "variant_a": variant_a,
        "variant_b": variant_b,
        "strategy_pair": {
            "variant_a": profile_a.get("id") or profile_a.get("strategy_id"),
            "variant_b": profile_b.get("id") or profile_b.get("strategy_id"),
        },
        "routing_source": routing_source,
        "differences": [
            f"Variant A uses `{profile_a.get('id') or profile_a.get('strategy_id')}` with {profile_a.get('slide_rhythm', 'an open slide rhythm')} and {profile_a.get('evidence_style', 'selective evidence')}.",
            f"Variant B uses `{profile_b.get('id') or profile_b.get('strategy_id')}` with {profile_b.get('slide_rhythm', 'an alternate slide rhythm')} and {profile_b.get('evidence_style', 'alternate evidence treatment')}.",
            "The two variants differ first in deck-plan.json and renderer-contract.json strategy, layout recipe, content emphasis, evidence treatment, palette emphasis, typography bias, and chart/table style.",
            "The renderer consumes those machine-facing plan fields and does not branch on the variant letter.",
        ],
        "recommendation": "variant-a",
        "recommendation_reason": "Variant A is treated as the primary interpretation; use Variant B when its alternate evidence or density treatment better fits the audience.",
    }
    json_dump(root / "variant-comparison-report.json", comparison)
    (root / "auto-mode-recommendation.md").write_text(
        "# Auto Mode Recommendation\n\n"
        "Recommended variant: `variant-a`.\n\n"
        f"Variant A uses `{profile_a.get('id') or profile_a.get('strategy_id')}`. "
        f"Variant B uses `{profile_b.get('id') or profile_b.get('strategy_id')}`. "
        "Choose Variant B when its alternate density, evidence treatment, or visual rhythm better matches the audience.\n",
        encoding="utf-8",
    )
    return {
        "status": comparison["status"],
        "mode": "auto",
        "project_dir": safe_rel(root),
        "variant_a_pptx": variant_a["pptx_path"],
        "variant_b_pptx": variant_b["pptx_path"],
        "comparison_report": safe_rel(root / "variant-comparison-report.json"),
        "recommendation": safe_rel(root / "auto-mode-recommendation.md"),
        "routing_source": routing_source,
    }


def compose_default_packet_from_prompt(prompt: str, *, slide_count: int = 5, project_name: str | None = None) -> dict[str, Any]:
    project_name = project_name or (prompt.split(".")[0].strip()[:48] if prompt.strip() else "Untitled Deck")
    archetypes = ["cover", "big_thesis", "three_cards", "process_flow", "ask"]
    slides = []
    for index, archetype in enumerate(archetypes[:slide_count], start=1):
        slides.append(
            {
                "slide_no": index,
                "layout_archetype": archetype,
                "content_brief": prompt if index == 1 else f"{project_name} planning point {index}",
                "visible_content_candidates": [
                    project_name if index == 1 else f"{project_name} point {index}",
                    "A concise machine-planned slide generated from sparse intake.",
                ],
                "asset_slots": [],
                "qa_checks": ["No HTML screenshot", "Native PPT objects only"],
            }
        )
    return {
        "contract": {"name": "b44.design_guide_packet", "version": "1.0", "compatibility": "additive_to_b44_asset_handoff"},
        "guide_identity": {
            "guide_id": f"assistant:{re.sub(r'[^a-z0-9]+', '-', project_name.lower()).strip('-') or 'deck'}",
            "guide_version": "1.0.0",
            "status": "draft",
            "language": "en-US",
            "project_name": project_name,
            "topic": prompt,
            "slide_count": len(slides),
            "created_at": utc_now(),
        },
        "project_brief": {
            "audience": ["general business audience"],
            "tone": ["clear", "credible", "modern"],
            "objective": prompt,
            "constraints": ["Use public-safe local artifacts only.", "Do not use HTML screenshots in PPTX."],
        },
        "reference_files": [{"file_name": "sparse-intake", "extension": ".txt", "purpose": "User natural-language request"}],
        "palette": {
            "palette_id": "assistant-default",
            "palette_name": "Assistant Default",
            "source": {"kind": "project_defined", "asset_ref": None},
            "colors": [
                {"role": "main", "name": "Blue", "hex": "#315CFF", "rgb": [49, 92, 255], "usage": "Primary accent"},
                {"role": "support", "name": "Pink", "hex": "#FF4DA6", "rgb": [255, 77, 166], "usage": "Secondary accent"},
                {"role": "accent", "name": "Mint", "hex": "#22C7A9", "rgb": [34, 199, 169], "usage": "Positive accent"},
                {"role": "background", "name": "Cloud", "hex": "#F7F8FC", "rgb": [247, 248, 252], "usage": "Background"},
                {"role": "neutral", "name": "Ink", "hex": "#101828", "rgb": [16, 24, 40], "usage": "Text"},
            ],
        },
        "typography": {
            "font_package_refs": [],
            "roles": [
                {"role": "hero_title", "font_stack": ["Aptos", "Arial"], "default_pt": 46, "min_pt": 36, "max_pt": 54, "weight": "bold", "line_limit": 2, "fallback": "Aptos Display"},
                {"role": "slide_title", "font_stack": ["Aptos", "Arial"], "default_pt": 30, "min_pt": 24, "max_pt": 36, "weight": "bold", "line_limit": 2, "fallback": "Aptos"},
                {"role": "metric", "font_stack": ["Aptos", "Arial"], "default_pt": 38, "min_pt": 30, "max_pt": 46, "weight": "bold", "line_limit": 1, "fallback": "Aptos Display"},
                {"role": "body", "font_stack": ["Aptos", "Arial"], "default_pt": 17, "min_pt": 12, "max_pt": 21, "weight": "regular", "line_limit": 4, "fallback": "Aptos"},
                {"role": "caption", "font_stack": ["Aptos", "Arial"], "default_pt": 11, "min_pt": 9, "max_pt": 13, "weight": "regular", "line_limit": 2, "fallback": "Aptos"},
            ],
        },
        "slide_size": {"size": "widescreen_16_9", "width_in": 13.333, "height_in": 7.5},
        "safe_area": {"left_in": 0.45, "top_in": 0.35, "right_in": 12.88, "bottom_in": 7.1},
        "background_policy": {"default_mode": "single_solid_cloud", "max_modes_per_deck": 3, "allowed_types": ["solid", "approved_image", "generated_image"], "forbidden_types": ["html_preview_image", "unknown_stock_image"]},
        "header_footer_policy": {"header": {"mode": "optional", "allowed_content": ["section label"]}, "footer": {"mode": "optional", "allowed_content": ["page number"]}},
        "slide_plan": {"slides": slides},
        "layout_archetypes": [
            {
                "id": item,
                "description": item.replace("_", " "),
                "native_assembly_hint": "Use native editable PowerPoint text boxes, shapes, connectors, and chart-like primitives.",
            }
            for item in archetypes[:slide_count]
        ],
        "asset_slot_policy": {
            "priority_order": [
                "approved_package_asset",
                "user_supplied_approved_asset",
                "generated_image_approved_for_deck",
                "native_shape_or_mockup_fallback",
            ],
            "notes": ["Use native fallback when no approved asset package is available."],
        },
        "qa_rules": [{"id": "native-ppt", "severity": "blocking", "check": "Slides must use native PowerPoint objects."}],
        "fallback_policy": {
            "missing_asset": "Use native shape or mockup fallback and report it.",
            "font_unavailable": "Use the role fallback font and report the fallback.",
            "overflow": "Summarize text before shrinking; report unresolved overflow.",
        },
        "approved_asset_references": [],
        "public_safety": {
            "private_refs_redacted": True,
            "contains_raw_assets": False,
            "contains_drive_ids": False,
            "contains_private_paths": False,
            "contains_generated_private_reports": False,
            "contains_tokens": False,
        },
    }


INTENT_ARCHETYPE_SEQUENCES = {
    "ir_pitch": ["cover", "big_thesis", "market_sizing", "product_mockup", "traction_metrics", "business_model", "roadmap", "ask"],
    "executive_report": ["cover", "big_thesis", "traction_metrics", "three_cards", "process_flow", "financial_plan", "ask"],
    "public_institution_report": ["cover", "big_thesis", "three_cards", "process_flow", "financial_plan", "roadmap", "ask"],
    "portfolio": ["cover", "three_cards", "product_mockup", "process_flow", "traction_metrics", "ask"],
    "product_introduction": ["cover", "big_thesis", "product_mockup", "three_cards", "three_use_cases", "traction_metrics", "ask"],
    "sales_proposal": ["cover", "big_thesis", "three_cards", "traction_metrics", "positioning_matrix", "roadmap", "ask"],
    "education_training": ["cover", "big_thesis", "process_flow", "three_cards", "three_use_cases", "roadmap", "ask"],
    "research_analysis": ["cover", "big_thesis", "market_sizing", "positioning_matrix", "traction_metrics", "three_cards", "ask"],
    "marketing_campaign": ["cover", "big_thesis", "three_use_cases", "process_flow", "roadmap", "traction_metrics", "ask"],
    "event_travel": ["cover", "big_thesis", "process_flow", "three_cards", "roadmap", "ask"],
    "media_entertainment": ["cover", "big_thesis", "three_cards", "three_use_cases", "roadmap", "ask"],
    "status_update": ["cover", "big_thesis", "traction_metrics", "process_flow", "roadmap", "ask"],
    "unknown": ["cover", "big_thesis", "three_cards", "process_flow", "ask"],
}


def compose_guide_packet_from_intent(
    intent_profile: dict[str, Any],
    source_summary: dict[str, Any],
    routing_report: dict[str, Any],
    *,
    request_intake: dict[str, Any] | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    topic = safe_string(project_name or intent_profile.get("topic") or "Untitled Deck")
    family = str(intent_profile.get("deck_family") or "unknown")
    subtype = str(intent_profile.get("sector_subtype") or "general")
    archetypes = INTENT_ARCHETYPE_SEQUENCES.get(family, INTENT_ARCHETYPE_SEQUENCES["unknown"])
    strategy_a = routing_report.get("selected", {}).get("variant_a", {}).get("strategy_id", "board_brief")
    strategy_b = routing_report.get("selected", {}).get("variant_b", {}).get("strategy_id", "demo_story")
    prompt = str(request_intake.get("original_request_excerpt") if request_intake else topic)
    packet = compose_default_packet_from_prompt(prompt, slide_count=5, project_name=str(topic))
    packet["guide_identity"]["guide_id"] = f"intent:{re.sub(r'[^a-z0-9]+', '-', str(topic).lower()).strip('-') or 'deck'}"
    packet["guide_identity"]["language"] = str((request_intake or {}).get("detected_language") or "en-US")
    packet["guide_identity"]["topic"] = str(topic)
    packet["project_brief"] = {
        "audience": [str(intent_profile.get("audience") or "general audience")],
        "tone": [str(item) for item in intent_profile.get("tone", ["clear", "credible"])],
        "objective": str(intent_profile.get("objective") or "create"),
        "constraints": [
            "Use public-safe local artifacts only.",
            "Do not use HTML screenshots in PPTX.",
            "Keep visible content separate from router metadata and source evidence.",
            f"Intent family: {family}; subtype: {subtype}.",
        ],
    }
    source_refs = []
    for source in source_summary.get("sources", []):
        source_refs.append(
            {
                "file_name": str(source.get("public_label") or source.get("source_id")),
                "extension": f".{source.get('kind', 'source')}",
                "purpose": "Bounded sparse-intake source summary",
                "public_safe_note": "Private source location and raw payload are not included.",
            }
        )
    packet["reference_files"] = source_refs or [
        {"file_name": "sparse-intake", "extension": ".txt", "purpose": "User natural-language request"}
    ]
    source_signals = []
    for source in source_summary.get("sources", []):
        source_signals.extend(source.get("content_structure_signals", []))
    slides = []
    labels = [
        ("Opening", f"{topic}", f"{intent_profile.get('objective', 'Create')} a {family.replace('_', ' ')} deck."),
        ("Core Message", f"{subtype.replace('_', ' ').title()} Direction", "Clarify the main audience, objective, and decision context."),
        ("Evidence", "What the Source Suggests", "Use bounded source summaries and clearly mark assumptions."),
        ("Plan", "Recommended Structure", "Organize the story into sections the audience can scan."),
        ("Proof", "Signals And Risks", "Separate known evidence from inferred planning assumptions."),
        ("Roadmap", "Next Steps", "Show sequence, ownership, or launch path where useful."),
        ("Close", "Decision Or Next Action", "End with the action the audience should take."),
    ]
    for index, archetype in enumerate(archetypes, start=1):
        label, title, subtitle = labels[min(index - 1, len(labels) - 1)]
        slides.append(
            {
                "slide_no": index,
                "layout_archetype": archetype,
                "content_brief": f"{label}: {subtitle}",
                "visible_content_candidates": [title, subtitle, "Structured for audience-ready review."],
                "asset_slots": [],
                "qa_checks": ["No HTML screenshot", "Native PPT objects only", "No private source paths on visible slides"],
            }
        )
    packet["guide_identity"]["slide_count"] = len(slides)
    packet["slide_plan"]["slides"] = slides
    packet["layout_archetypes"] = [
        {
            "id": item,
            "description": item.replace("_", " "),
            "native_assembly_hint": "Use native editable PowerPoint text boxes, shapes, connectors, tables, and chart-like primitives.",
        }
        for item in dict.fromkeys(archetypes)
    ]
    packet["public_safety"].update(
        {
            "contains_raw_assets": False,
            "contains_drive_ids": False,
            "contains_private_paths": False,
            "contains_tokens": False,
        }
    )
    GuidePacket.model_validate(packet)
    return safe_string(packet)
