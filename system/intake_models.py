from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeLevel(str, Enum):
    general = "general"
    informed = "informed"
    expert = "expert"


class DecisionRole(str, Enum):
    decision_maker = "decision_maker"
    influencer = "influencer"
    reviewer = "reviewer"
    learner = "learner"
    mixed = "mixed"


class DeliveryMode(str, Enum):
    live = "live"
    async_readout = "async_readout"
    leave_behind = "leave_behind"
    workshop = "workshop"
    email_attachment = "email_attachment"


class DeckType(str, Enum):
    report = "report"
    sales = "sales"
    portfolio = "portfolio"
    strategy = "strategy"
    training = "training"
    status_update = "status_update"
    proposal = "proposal"
    analysis = "analysis"
    other = "other"


class Industry(str, Enum):
    business = "business"
    travel = "travel"
    food_and_beverage = "food_and_beverage"
    healthcare = "healthcare"
    entertainment = "entertainment"
    exhibition = "exhibition"
    technology = "technology"
    finance = "finance"
    other = "other"


class Tone(str, Enum):
    executive = "executive"
    analytical = "analytical"
    sales = "sales"
    technical = "technical"
    portfolio = "portfolio"
    conservative = "conservative"
    visual = "visual"
    urgent = "urgent"
    friendly = "friendly"


class ContentDensity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class VariationLevel(str, Enum):
    single_path = "single_path"
    light_variants = "light_variants"
    variant_review = "variant_review"


class ApprovalMode(str, Enum):
    none = "none"
    assistant = "assistant"
    operator_review = "operator_review"
    stakeholder_review = "stakeholder_review"


class SourceKind(str, Enum):
    docx = "docx"
    xlsx = "xlsx"
    json = "json"
    markdown = "markdown"
    notes = "notes"
    other = "other"


class Audience(StrictBase):
    primary: str
    secondary: list[str] = Field(default_factory=list)
    knowledge_level: KnowledgeLevel
    decision_role: DecisionRole


class PresentationContext(StrictBase):
    setting: str
    delivery_mode: DeliveryMode
    duration_minutes: int | None = Field(default=None, ge=1)
    presenter_role: str | None = None
    locale: str | None = None


class SlideCountRange(StrictBase):
    min: int = Field(ge=1)
    max: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_order(self) -> "SlideCountRange":
        if self.max < self.min:
            raise ValueError("slide_count_range.max must be greater than or equal to min")
        return self


class BrandOrTemplateScope(StrictBase):
    preferred_scope: str | None
    preferred_template_keys: list[str] = Field(default_factory=list)
    required_template_library: str | None = None
    theme_path: str | None = None
    notes: str | None = None


class ReviewRequirements(StrictBase):
    needs_variant_review: bool
    requires_rationale_report: bool
    requires_slot_map: bool
    reviewers: list[str] = Field(default_factory=list)
    approval_mode: ApprovalMode


class SourceMaterial(StrictBase):
    path: str
    kind: SourceKind
    description: str | None = None


class OutputPreferences(StrictBase):
    output_spec_path: str | None = None
    output_deck_path: str | None = None
    required_reports: list[str] = Field(default_factory=list)


class DeckIntake(StrictBase):
    schema_: str | None = Field(default=None, alias="$schema")
    intake_version: str = Field(pattern=r"^1\.0$")
    name: str
    audience: Audience
    presentation_context: PresentationContext
    primary_goal: str
    deck_type: DeckType
    industry: Industry = Industry.other
    tone: list[Tone] = Field(min_length=1)
    slide_count_range: SlideCountRange
    brand_or_template_scope: BrandOrTemplateScope
    content_density: ContentDensity
    variation_level: VariationLevel
    review_requirements: ReviewRequirements
    must_include: list[str]
    must_avoid: list[str]
    source_materials: list[SourceMaterial] = Field(default_factory=list)
    output_preferences: OutputPreferences = Field(default_factory=OutputPreferences)
    notes: str | None = None


def validate_deck_intake(data: dict[str, Any]) -> DeckIntake:
    return DeckIntake.model_validate(data)


def deck_intake_json_schema() -> dict[str, Any]:
    return DeckIntake.model_json_schema()
