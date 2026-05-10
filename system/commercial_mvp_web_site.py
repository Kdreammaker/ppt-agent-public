from __future__ import annotations

from copy import deepcopy


PUBLIC_SITE_SCHEMA_VERSION = "commercial_mvp_public_site.v1"

FORBIDDEN_PUBLIC_SITE_MARKERS = (
    "postgresql://",
    "postgres://",
    "supabase.co",
    "corp-db.local",
    "company-postgres.local",
    "C:\\",
    "/Users/",
    "package_manifest",
    "raw_evidence_root",
    "private_prompt",
    "Authorization" + ":",
    "Bearer" + " ",
    "api_key",
    "RAW_",
    "drive_id",
    "structured_data_id",
    "data" + ":image",
    "UEsDB",
    "source text",
    "slide body",
    "private deck narrative",
    "confidential source",
    "confidential_deck.pdf",
)

ADMIN_EVIDENCE_MARKERS = (
    "route_backed_operator_actions",
    "duplicate_idempotency_replay",
    "admin_adjust_credit",
    "gateway_only_allowed",
    "direct_client_mutation",
    "operator-dashboard-data.json",
)


def build_public_site_model() -> dict:
    return deepcopy(
        {
            "schema_version": PUBLIC_SITE_SCHEMA_VERSION,
            "brand": {
                "primary_display": "A.DreamMaker",
                "full_brand": "ADOTDREAMMAKER",
                "product_name": "A.DreamMaker PPT Maker",
                "category": "host_ai_assistive_extension",
            },
            "surface_separation": {
                "public_landing": {
                    "surface": "public_landing",
                    "status": "korean_first_local_landing",
                    "purpose": "seo_safe_product_explanation_and_google_signup_cta",
                    "admin_route_evidence_exposed": False,
                },
                "account_entry": {
                    "surface": "account_entry",
                    "status": "authenticated_placeholder",
                    "purpose": "account_and_billing_entry_placeholder",
                    "admin_route_evidence_exposed": False,
                },
                "operator_admin": {
                    "surface": "operator_admin",
                    "status": "separate_local_console",
                    "path_hint": "web/commercial-mvp-admin",
                    "purpose": "route_backed_evidence_and_mutation_boundary",
                },
            },
            "product_boundary": {
                "host_ai_responsibilities": [
                    "interpretation",
                    "planning",
                    "writing",
                    "visual_direction",
                    "revision_decision",
                    "source_use_judgment",
                    "asset_need_judgment",
                ],
                "ppt_maker_responsibilities": [
                    "tool_execution",
                    "templates_and_guides",
                    "asset_system_mediation",
                    "rule_based_hooks",
                    "native_pptx_rendering",
                    "evidence",
                    "account_free_credit_and_paid_fair_use_controls",
                    "public_private_safety",
                ],
                "modes": ["assistant", "auto"],
                "default_mode": "assistant",
                "self_hosted_ai_claimed": False,
                "hosted_generation_enabled": False,
                "backend_ai_authoring_enabled": False,
                "renderer_visual_consumption_changed": False,
            },
            "plan_teaser": [
                {
                    "tier": "free",
                    "status": "limited_free_credits",
                    "credit_policy": "limited_credits_referral_replenishable",
                    "editor_access": "preview_only",
                    "viewer_sharing": "watermarked",
                    "reference_design_library": "limited_preview",
                    "style_memory": "limited_preview",
                    "asset_design_packages": "not_included",
                },
                {
                    "tier": "paid",
                    "status": "paid_fair_use",
                    "credit_policy": "no_visible_per_edit_credit_for_normal_workflows",
                    "editor_access": "practical_editor",
                    "viewer_sharing": "watermark_free",
                    "reference_design_library": "useful_capacity",
                    "style_memory": "included",
                    "asset_design_packages": "approved_safe_manifest_when_entitled",
                },
            ],
            "commercial_stack_direction": {
                "cloudflare_gateway": "planned_not_deployed",
                "supabase_control_plane": "local_draft_not_remote_applied",
                "vercel_web": "local_static_skeleton_not_deployed",
                "payment": "not_attached",
                "google_oauth": "target_provider_not_verified",
            },
            "account_entry_placeholder": {
                "requires_authenticated_account": True,
                "login_implemented": False,
                "payment_attached": False,
                "subscription_mutation_enabled": False,
                "hosted_dashboard_sync_enabled": False,
                "display_fields": {
                    "plan": "free_example",
                    "free_credits": "limited_example",
                    "paid_fair_use": "not_active_fixture",
                    "referral_status": "scaffold_pending",
                    "ai_client_session_status": "active_fixture",
                    "entitlement_status": "active_fixture",
                    "viewer_sharing": "watermarked_free_fixture",
                    "style_memory": "preview_only_fixture",
                    "reference_design_library": "preview_only_fixture",
                    "asset_design_packages": "paid_safe_manifest_when_entitled",
                    "billing_entry": "future_payment_not_attached",
                },
            },
            "public_ctas": {
                "primary": "google_signup_cta_pending_provider_verification",
                "secondary": "open_html_workbench_fixture",
                "billing": "future_payment_not_attached",
            },
            "public_landing_content": {
                "korean_first": True,
                "seo_metadata_present": True,
                "google_signup_cta_present": True,
                "assistant_auto_explained": True,
                "html_workbench_explained": True,
                "pdf_pptx_handoff_explained": True,
                "privacy_security_explained": True,
                "faq_present": True,
            },
            "safety_boundary": {
                "raw_prompts_included": False,
                "source_or_slide_text_included": False,
                "local_paths_or_filenames_included": False,
                "previews_or_pptx_binaries_included": False,
                "package_internals_included": False,
                "credentials_or_tokens_included": False,
                "raw_db_urls_included": False,
                "drive_or_docs_identifiers_included": False,
                "admin_route_evidence_in_public_site": False,
            },
        }
    )


def validate_public_site_model(model: dict) -> list[str]:
    errors: list[str] = []

    def expect(condition: bool, label: str) -> None:
        if not condition:
            errors.append(label)

    expect(model.get("schema_version") == PUBLIC_SITE_SCHEMA_VERSION, "public site schema mismatch")
    brand = model.get("brand", {})
    expect(brand.get("primary_display") == "A.DreamMaker", "primary display brand mismatch")
    expect(brand.get("full_brand") == "ADOTDREAMMAKER", "full brand mismatch")

    boundary = model.get("product_boundary", {})
    expect(set(boundary.get("modes", [])) == {"assistant", "auto"}, "public site modes must be Assistant/Auto only")
    expect(boundary.get("default_mode") == "assistant", "Assistant must remain default")
    for disabled in (
        "self_hosted_ai_claimed",
        "hosted_generation_enabled",
        "backend_ai_authoring_enabled",
        "renderer_visual_consumption_changed",
    ):
        expect(boundary.get(disabled) is False, f"{disabled} must remain false")

    plans = model.get("plan_teaser", [])
    expect({plan.get("tier") for plan in plans} == {"free", "paid"}, "plan teaser must stay Free plus Paid")
    free_plan = next((plan for plan in plans if plan.get("tier") == "free"), {})
    paid_plan = next((plan for plan in plans if plan.get("tier") == "paid"), {})
    expect(free_plan.get("credit_policy") == "limited_credits_referral_replenishable", "Free plan must use limited/referral credits")
    expect(free_plan.get("editor_access") == "preview_only", "Free plan editor must be preview_only")
    expect(paid_plan.get("credit_policy") == "no_visible_per_edit_credit_for_normal_workflows", "Paid plan must avoid visible per-edit credits")
    expect(paid_plan.get("editor_access") == "practical_editor", "Paid plan must include practical editor")
    expect(paid_plan.get("viewer_sharing") == "watermark_free", "Paid plan must remove viewer watermark")

    stack = model.get("commercial_stack_direction", {})
    expect(stack.get("cloudflare_gateway") == "planned_not_deployed", "Cloudflare must remain not deployed")
    expect(stack.get("supabase_control_plane") == "local_draft_not_remote_applied", "Supabase must remain local draft")
    expect(stack.get("vercel_web") == "local_static_skeleton_not_deployed", "Vercel must remain not deployed")
    expect(stack.get("payment") == "not_attached", "payment must remain not_attached")
    expect(stack.get("google_oauth") == "target_provider_not_verified", "Google OAuth must remain unverified until remote setup")

    landing = model.get("public_landing_content", {})
    for required in (
        "korean_first",
        "seo_metadata_present",
        "google_signup_cta_present",
        "assistant_auto_explained",
        "html_workbench_explained",
        "pdf_pptx_handoff_explained",
        "privacy_security_explained",
        "faq_present",
    ):
        expect(landing.get(required) is True, f"landing content {required} must be true")

    account = model.get("account_entry_placeholder", {})
    expect(account.get("requires_authenticated_account") is True, "account entry must require authenticated account")
    for disabled in (
        "login_implemented",
        "payment_attached",
        "subscription_mutation_enabled",
        "hosted_dashboard_sync_enabled",
    ):
        expect(account.get(disabled) is False, f"{disabled} must remain false")
    display_fields = account.get("display_fields", {})
    expect(display_fields.get("billing_entry") == "future_payment_not_attached", "billing entry must remain future_payment_not_attached")
    expect(display_fields.get("plan") == "free_example", "account placeholder must use Free/Paid plan vocabulary")
    expect(display_fields.get("paid_fair_use") == "not_active_fixture", "account placeholder must expose paid fair-use posture")

    surfaces = model.get("surface_separation", {})
    expect(surfaces.get("operator_admin", {}).get("path_hint") == "web/commercial-mvp-admin", "admin surface path must remain separate")
    expect(surfaces.get("public_landing", {}).get("admin_route_evidence_exposed") is False, "public landing must not expose admin evidence")
    expect(surfaces.get("account_entry", {}).get("admin_route_evidence_exposed") is False, "account entry must not expose admin evidence")

    safety = model.get("safety_boundary", {})
    for key, value in safety.items():
        expect(value is False, f"safety boundary {key} must be false")

    encoded = str(model)
    for marker in (*FORBIDDEN_PUBLIC_SITE_MARKERS, *ADMIN_EVIDENCE_MARKERS):
        expect(marker not in encoded, f"public site model must not contain forbidden marker: {marker}")
    return errors
