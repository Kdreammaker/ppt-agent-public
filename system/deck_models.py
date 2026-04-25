from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


class StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlexibleBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class SourceMode(str, Enum):
    import_ = "import"
    blank = "blank"


FitStrategy = Literal["preserve_template", "shrink", "manual_wrap"]
AspectRatio = Literal["16:9", "4:3"]
HexColor = Annotated[str, Field(pattern=r"^#?[0-9A-Fa-f]{6}$")]
ThemeAccentSlot = Literal["accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]
ModePolicyName = Literal["auto", "assistant"]
AssetIntentRole = Literal["image_placeholder", "icon", "chart_preset", "palette", "typography", "theme", "logo", "reference"]
AssetClass = Literal["palette", "typography", "icon", "illustration", "image", "chart_preset", "theme", "reference", "slides", "document"]
AssetSourcePolicy = Literal["finalized_catalog", "local_user_asset_policy", "external_registry_reference", "workspace_user_asset"]
AssetMaterialization = Literal["metadata_only", "runtime_materialization_required", "local_config_reference", "local_code_reference", "local_workspace_file"]


class SlideSelector(StrictBase):
    purpose: str
    scope: str | None = None
    preferred_variant: str | None = None
    fallback_variants: list[str] = Field(default_factory=list)
    required_tags: list[str] = Field(default_factory=list)
    tone: list[str] = Field(default_factory=list)
    preferred_density: str | None = None
    preferred_structure: str | None = None
    preferred_visual_weight: str | None = None
    source_library: str | None = None
    min_quality_score: float | None = None
    preferred_design_tier: str | None = None
    usage_policies: list[str] = Field(default_factory=list)
    prefer_high_quality: bool = True
    use_variation_penalty: bool = True


class ImageItem(StrictBase):
    path: str
    left: float
    top: float
    width: float
    height: float


class ShapeItem(StrictBase):
    left: float
    top: float
    width: float
    height: float
    geometry: str | None = None
    fill: HexColor | None = None
    line: HexColor | None = None
    line_width: float | None = Field(default=None, ge=0)
    radius: float | None = None
    rotation: float | None = None


class TextBoxItem(StrictBase):
    text: str
    left: float
    top: float
    width: float
    height: float
    font_size: float | None = None
    font_role: str | None = None
    color: str | None = None
    bold: bool = False
    align: str | None = None
    max_chars_per_line: int | None = Field(default=None, ge=1)


class BarChartItem(StrictBase):
    left: float
    top: float
    width: float
    height: float
    categories: list[str]
    values: list[float]

    @model_validator(mode="after")
    def validate_lengths(self) -> "BarChartItem":
        if len(self.categories) != len(self.values):
            raise ValueError("categories and values must have the same length")
        return self


class ChartSlotData(StrictBase):
    chart_type: Literal["bar"] = "bar"
    categories: list[str] = Field(min_length=1)
    values: list[float] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lengths(self) -> "ChartSlotData":
        if len(self.categories) != len(self.values):
            raise ValueError("categories and values must have the same length")
        return self


CellValue = str | int | float


class TableSlotData(StrictBase):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[CellValue]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rectangular(self) -> "TableSlotData":
        expected_columns = len(self.headers) if self.headers else len(self.rows[0])
        if expected_columns <= 0:
            raise ValueError("table slot requires at least one column")
        for row in self.rows:
            if len(row) != expected_columns:
                raise ValueError("all table rows must have the same column count as headers or first row")
        return self


class CommonSlide(StrictBase):
    layout: str
    plan_slide_id: str | None = None
    plan_decision_refs: list[str] = Field(default_factory=list)
    base_slide_key: str | None = None
    template_key: str | None = None
    base_slide_no: int | None = Field(default=None, ge=1)
    slide_selector: SlideSelector | None = None
    source_mode: SourceMode | None = None
    keep_shape_indices: list[int] = Field(default_factory=list)
    shapes: list[ShapeItem] = Field(default_factory=list)
    text_boxes: list[TextBoxItem] = Field(default_factory=list)
    images: list[ImageItem] = Field(default_factory=list)
    bar_charts: list[BarChartItem] = Field(default_factory=list)
    speaker_notes: list[str] = Field(default_factory=list)
    report_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source(self) -> "CommonSlide":
        if self.source_mode == SourceMode.blank:
            return self
        has_source = any(
            [
                self.base_slide_key,
                self.template_key,
                self.base_slide_no is not None,
                self.slide_selector is not None,
            ]
        )
        if not has_source:
            raise ValueError("slide must define one of base_slide_key, template_key, base_slide_no, or slide_selector")
        return self


class SlotOverride(StrictBase):
    font_role: str | None = None
    font_size: float | None = None
    color: str | None = None
    bold: bool | None = None
    align: str | None = None
    max_chars_per_line: int | None = Field(default=None, ge=1)
    max_lines: int | None = Field(default=None, ge=1)
    fit_strategy: FitStrategy | None = None


class AssetIntent(StrictBase):
    role: AssetIntentRole
    asset_class: AssetClass
    asset_id: str
    slide_number: int | None = Field(default=None, ge=1)
    slot: str | None = None
    purpose: str | None = None
    industry: str | None = None
    tone: list[str] = Field(default_factory=list)
    aspect_ratio: str | None = None
    query: dict[str, Any] = Field(default_factory=dict)
    source_policy: AssetSourcePolicy
    materialization: AssetMaterialization
    source_type: str | None = None
    workspace_relative_path: str | None = None
    private_upload_allowed: bool | None = None
    usage_rationale: str | None = None
    license_action: str
    risk_level: str
    semantic_context: dict[str, Any] = Field(default_factory=dict)
    template_media_policy: dict[str, Any] = Field(default_factory=dict)
    candidate_asset_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class BlueprintOverlaySlide(CommonSlide):
    layout: Literal["blueprint_overlay"]
    text_slots: dict[str, str] = Field(default_factory=dict)
    text_values: list[str] = Field(default_factory=list)
    image_slots: dict[str, str] = Field(default_factory=dict)
    chart_slots: dict[str, ChartSlotData] = Field(default_factory=dict)
    table_slots: dict[str, TableSlotData] = Field(default_factory=dict)
    slot_overrides: dict[str, SlotOverride] = Field(default_factory=dict)
    clear_unfilled_slots: bool = True
    clear_unfilled_image_slots: bool = False
    clear_residual_placeholders: bool = True
    clear_residual_text_patterns: list[str] = Field(default_factory=list)


class TemplateSlide(CommonSlide):
    layout: Literal["template_slide"]
    text_slots: dict[str, str] = Field(default_factory=dict)
    text_values: list[str] = Field(default_factory=list)
    image_slots: dict[str, str] = Field(default_factory=dict)
    chart_slots: dict[str, ChartSlotData] = Field(default_factory=dict)
    table_slots: dict[str, TableSlotData] = Field(default_factory=dict)
    slot_overrides: dict[str, SlotOverride] = Field(default_factory=dict)
    clear_unfilled_slots: bool = True
    clear_unfilled_image_slots: bool = False
    clear_residual_placeholders: bool = True
    clear_residual_text_patterns: list[str] = Field(default_factory=list)


DeckSlide = Annotated[
    BlueprintOverlaySlide | TemplateSlide,
    Field(discriminator="layout"),
]


class DeckSpec(StrictBase):
    schema_: str | None = Field(default=None, alias="$schema")
    name: str
    project_id: str | None = None
    deck_plan_ref: str | None = None
    plan_traceability_report_path: str | None = None
    aspect_ratio: AspectRatio = "16:9"
    catalog_path: str | None = None
    reference_catalog_path: str | None = None
    blueprint_path: str | None = None
    mode_policy: ModePolicyName = "auto"
    theme_path: str
    theme_accent_overrides: dict[ThemeAccentSlot, HexColor] = Field(default_factory=dict)
    source_template: str | None = None
    output_path: str
    design_brief_path: str | None = None
    doc_paths: list[str] = Field(default_factory=list)
    recipe: str | None = None
    asset_intents: list[AssetIntent] = Field(default_factory=list)
    slides: list[DeckSlide] = Field(min_length=1)


def validate_deck_spec(data: dict[str, Any]) -> DeckSpec:
    return DeckSpec.model_validate(data)


def deck_spec_json_schema() -> dict[str, Any]:
    return DeckSpec.model_json_schema()


class DeckSpecRoot(RootModel[DeckSpec]):
    pass


class Bounds(StrictBase):
    slot: str | None = None
    left: float
    top: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class TemplateTextSlot(StrictBase):
    slot: str
    shape_index: int | None = Field(default=None, ge=1)
    shape_name: str | None = None
    fingerprint: str | None = None
    bounds: Bounds | None = None
    font_role: str | None = None
    color_token: str | None = None
    bold: bool = False
    align: str | None = None
    max_lines: int | None = Field(default=None, ge=1)
    allow_shrink: bool = False
    max_chars_per_line: int | None = Field(default=None, ge=1)
    protect_tokens: list[str] = Field(default_factory=list)
    fit_strategy: FitStrategy = "preserve_template"

    @model_validator(mode="after")
    def validate_target(self) -> "TemplateTextSlot":
        if self.shape_index is None and self.bounds is None:
            raise ValueError("text slot requires shape_index or bounds")
        return self


class TemplateImageSlot(StrictBase):
    slot: str
    shape_index: int | None = Field(default=None, ge=1)
    shape_name: str | None = None
    bounds: Bounds | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "TemplateImageSlot":
        if self.shape_index is None and self.bounds is None:
            raise ValueError("image slot requires shape_index or bounds")
        return self


class TemplateChartSlot(StrictBase):
    slot: str
    bounds: Bounds


class TemplateTableSlot(StrictBase):
    slot: str
    bounds: Bounds


class TemplateBlueprint(FlexibleBase):
    slide_id: str
    template_key: str
    library_id: str
    library_path: str
    library_slide_no: int = Field(ge=1)
    purpose: str
    variant: str
    scope: str
    mode: str
    preserve_shapes: list[int] = Field(default_factory=list)
    remove_shapes: list[int] = Field(default_factory=list)
    editable_text_slots: list[TemplateTextSlot] = Field(default_factory=list)
    editable_image_slots: list[TemplateImageSlot] = Field(default_factory=list)
    editable_chart_slots: list[TemplateChartSlot] = Field(default_factory=list)
    editable_table_slots: list[TemplateTableSlot] = Field(default_factory=list)
    overlay_safe_zones: list[Bounds] = Field(default_factory=list)
    header_zone: Bounds
    footer_zone: Bounds
    page_zone: Bounds
    text_rules: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_slots_and_shapes(self) -> "TemplateBlueprint":
        preserve = set(self.preserve_shapes)
        remove = set(self.remove_shapes)
        if preserve & remove:
            raise ValueError("preserve_shapes and remove_shapes overlap")

        slot_groups = {
            "editable_text_slots": [slot.slot for slot in self.editable_text_slots],
            "editable_image_slots": [slot.slot for slot in self.editable_image_slots],
            "editable_chart_slots": [slot.slot for slot in self.editable_chart_slots],
            "editable_table_slots": [slot.slot for slot in self.editable_table_slots],
        }
        for label, names in slot_groups.items():
            if len(names) != len(set(names)):
                raise ValueError(f"duplicate slot names in {label}")
        return self


class TemplateBlueprintCollection(StrictBase):
    version: str | None = None
    slides: dict[str, TemplateBlueprint]


def validate_template_blueprints(data: dict[str, Any]) -> TemplateBlueprintCollection:
    return TemplateBlueprintCollection.model_validate(data)
