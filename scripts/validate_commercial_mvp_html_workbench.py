from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = BASE_DIR / "web" / "commercial-mvp-html-workbench"
DATA_PATH = WORKBENCH_DIR / "workbench-data.json"
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "commercial_mvp_html_workbench_validation.json"

REQUIRED_FILES = (
    "index.html",
    "viewer.html",
    "styles.css",
    "workbench.js",
    "viewer.js",
    "workbench-data.json",
    "generated-work-state.example.json",
    "generated-work-states/ir-final_user_test_polish.json",
    "generated-work-states/sales-final_user_test_polish.json",
    "generated-work-states/portfolio-final_user_test_polish.json",
    "package.json",
    "locales/en.json",
    "locales/ko.json",
    "scripts/build.mjs",
)

FORBIDDEN_LITERAL_MARKERS = (
    "MO" + "NIQ",
    "sample" + "_html_slides",
    "sample" + "_pptx_slides",
    "data" + ":image",
    "base" + "64,",
    "Authorization" + ":",
    "Bearer" + " ",
    "api" + "_key",
    "service" + "_role",
    "supabase" + ".co",
    "drive" + ".google.com",
    "docs" + ".google.com",
    "raw" + " prompt",
    "backend" + " chain-of-thought",
    "export" + " complete",
    "complete" + " export",
)

ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/(?:Users|home)/", re.IGNORECASE),
)

KOREAN_RE = re.compile(r"[가-힣]")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect(condition: bool, label: str, errors: list[str]) -> None:
    if not condition:
        errors.append(label)


def recipe_is_content_free(recipe: dict[str, Any]) -> bool:
    return (
        recipe.get("content_free_preview", {}).get("placeholder_labels_only") is True
        or recipe.get("synthetic_placeholder_preview", {}).get("placeholder_labels_only") is True
    )


def validate_content_free_schema_parity(errors: list[str]) -> dict[str, Any]:
    cases = {
        "legacy_content_free_preview": {
            "content_free_preview": {"placeholder_labels_only": True}
        },
        "current_synthetic_placeholder_preview": {
            "synthetic_placeholder_preview": {"placeholder_labels_only": True}
        },
        "mixed_prefers_either_true": {
            "content_free_preview": {"placeholder_labels_only": True},
            "synthetic_placeholder_preview": {"placeholder_labels_only": False},
        },
        "negative_no_placeholder_labels": {
            "synthetic_placeholder_preview": {"placeholder_labels_only": False}
        },
    }
    results = {name: recipe_is_content_free(recipe) for name, recipe in cases.items()}
    expect(results["legacy_content_free_preview"] is True, "legacy content_free_preview schema must count as content-free", errors)
    expect(results["current_synthetic_placeholder_preview"] is True, "current synthetic_placeholder_preview schema must count as content-free", errors)
    expect(results["mixed_prefers_either_true"] is True, "content-free predicate must accept either schema when true", errors)
    expect(results["negative_no_placeholder_labels"] is False, "content-free predicate must reject false placeholder flags", errors)
    return results


def collect_file_text(errors: list[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for relative in REQUIRED_FILES:
        path = WORKBENCH_DIR / relative
        expect(path.exists(), f"missing workbench file: {relative}", errors)
        if path.exists():
            texts[relative] = read_text(path)
    return texts


def validate_private_boundary(texts: dict[str, str], data: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    combined = "\n".join(texts.values())
    encoded_data = json.dumps(data, ensure_ascii=False, sort_keys=True)
    scan_blob = f"{combined}\n{encoded_data}"
    marker_hits = [marker for marker in FORBIDDEN_LITERAL_MARKERS if marker in scan_blob]
    path_hits = [pattern.pattern for pattern in ABSOLUTE_PATH_PATTERNS if pattern.search(scan_blob)]
    for marker in marker_hits:
        errors.append(f"forbidden marker in workbench files: {marker}")
    for pattern in path_hits:
        errors.append(f"absolute/private path marker in workbench files: {pattern}")
    return {
        "forbidden_literal_hits": marker_hits,
        "absolute_path_pattern_hits": path_hits,
        "checked_files": len(texts),
    }


def validate_data(data: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    expect(data.get("schema_version") == "commercial_mvp_html_workbench.v1", "schema version mismatch", errors)
    fixture = data.get("fixture_metadata", {})
    expect(fixture.get("is_fixture") is True, "fixture metadata must label current deck as fixture", errors)
    expect(fixture.get("not_host_ai_generated_output") is True, "fixture must not claim host-AI generated output", errors)
    expect(fixture.get("not_benchmark_copy") is True, "fixture must not claim benchmark copy", errors)
    boundary = data.get("product_boundary", {})
    expect(boundary.get("default_mode") == "assistant", "Assistant must be default mode", errors)
    expect(set(boundary.get("modes", [])) == {"assistant", "auto"}, "Assistant/Auto must be the only modes", errors)
    expect(boundary.get("backend_ai_chat_embedded") is False, "embedded backend AI chat must remain disabled", errors)
    expect(boundary.get("diagnostics_hidden_in_normal_mode") is True, "diagnostics must be hidden in normal mode", errors)

    guide = data.get("design_guide_package", {})
    expect(guide.get("version") == "commercial_mvp_presentation_design_guide.v1", "design guide version missing", errors)
    for key in (
        "design_package_id",
        "manifest_hash",
        "source_kind",
        "theme_id",
        "master_style_ids",
        "layout_recipe_ids",
        "component_recipe_ids",
        "text_style_role_ids",
        "token_set_ids",
    ):
        expect(key in guide, f"design guide missing safe manifest field: {key}", errors)
    expect(len(guide.get("recipes_used", [])) >= 10, "design guide recipe coverage missing", errors)
    expect("system_prompt_summary" in guide, "host-AI system prompt package summary missing", errors)
    design_package = data.get("design_package", {})
    expect(design_package.get("source_kind") in {"tracked_doc", "server_manifest", "approved_asset_system"}, "design package source_kind invalid", errors)
    expect("asset_system_package_ref" in design_package, "design package must expose safe asset-system ref field", errors)
    expect(data.get("theme_tokens", {}).get("theme_id"), "theme tokens missing theme_id", errors)
    expect(data.get("master_styles"), "master styles missing", errors)
    master_surface = data.get("master_style_surface", {})
    expect(master_surface.get("preview_enabled") is True, "Master Style surface preview missing", errors)
    for key in ("apply_semantics", "override_semantics", "reset_semantics", "lock_semantics"):
        expect(master_surface.get(key), f"Master Style surface missing {key}", errors)
    expect(master_surface.get("raw_ids_only_in_normal_inspector") is False, "Master Style must not be raw ids only in normal inspector", errors)
    roles = data.get("text_style_roles", {})
    required_roles = {"Title", "H1", "H2", "H3", "Body", "Caption", "Bullet"}
    expect(required_roles <= set(roles), "required text style roles missing", errors)
    for role in required_roles:
        role_data = roles.get(role, {})
        for key in ("fontFamilyToken", "fontSize", "fontWeight", "color", "lineHeight", "paragraphSpacing", "overflowPolicy", "letterSpacing"):
            expect(key in role_data, f"{role} missing text style field {key}", errors)
        expect(role_data.get("letterSpacing") == 0, f"{role} letter spacing must default to 0", errors)
    expect(data.get("layout_recipes"), "layout recipes missing", errors)
    expect(data.get("component_recipes"), "component recipes missing", errors)
    expect(data.get("revision_memory"), "revision memory missing", errors)
    library = data.get("reference_design_library", {})
    expect(library.get("extraction_source") == "local_host_ai_design_analysis_only", "Reference Design Library must use local-host-AI analysis boundary", errors)
    storage = library.get("server_storage_policy", {})
    for key in ("stores_original_files", "stores_source_text", "stores_slide_images", "stores_local_paths", "stores_private_urls", "stores_prompt_payloads"):
        expect(storage.get(key) is False, f"Reference Design Library server storage boundary failed: {key}", errors)
    expect(library.get("recipes"), "Reference Design Library recipe scaffold missing", errors)
    importer = library.get("importer", {})
    expect(importer.get("status") in {"content_free_importer_ready", "content_free_metric_importer_ready"}, "Reference Design Library importer missing", errors)
    expect(set(importer.get("benchmark_family_ids", [])) >= {"ir", "sales", "portfolio"}, "Reference Design Library importer must cover IR/sales/portfolio families", errors)
    for key in ("stores_source_dom", "stores_source_text", "stores_source_coordinates", "stores_source_screenshots", "stores_image_urls", "stores_source_filenames", "stores_business_content"):
        expect(importer.get(key) is False, f"Reference Design Library importer must block {key}", errors)
    for recipe in library.get("recipes", []):
        expect("relative_geometry" not in recipe, "Reference Design Library recipe must not store source coordinates", errors)
        expect(recipe.get("source_kind") in {"pptx_pdf_html_local_analysis", "local_pptx_html_family_metric_analysis"}, "Reference Design Library recipe source kind missing metric analysis", errors)
        if recipe.get("source_kind") == "local_pptx_html_family_metric_analysis":
            metrics = recipe.get("analysis_metrics", {})
            expect(metrics.get("stores_source_filenames") is False, "Reference Design Library metrics must not store source filenames", errors)
            expect(metrics.get("stores_exact_coordinates") is False, "Reference Design Library metrics must not store exact coordinates", errors)
            for key in ("palette_roles", "typography_roles", "layout_archetypes", "component_recipes", "image_slot_treatment", "chart_table_style", "density", "spacing_rhythm", "synthetic_placeholder_preview"):
                expect(key in recipe, f"Reference Design Library metric recipe missing {key}", errors)
        preview = recipe.get("synthetic_placeholder_preview") or recipe.get("content_free_preview", {})
        expect(recipe_is_content_free(recipe), "Reference Design Library recipe must satisfy shared CLI/MCP/UI content-free predicate", errors)
        expect(preview.get("placeholder_labels_only") is True, "Reference Design Library preview must be content-free", errors)
        expect(preview.get("uses_source_slide_text") is False, "Reference Design Library preview must not use source text", errors)
        expect(preview.get("uses_source_slide_image") is False, "Reference Design Library preview must not use source slide image", errors)
        expect(preview.get("uses_source_coordinates") is not True, "Reference Design Library preview must not use source coordinates", errors)
    style_profiles = data.get("style_memory_profiles", [])
    expect(style_profiles, "Style Memory profile scaffold missing", errors)
    for profile in style_profiles:
        expect(profile.get("visibility") == "user_visible", "Style Memory must be user visible", errors)
        expect({"view", "reset", "delete"} <= set(profile.get("user_controls", [])), "Style Memory controls must include view/reset/delete", errors)
        expect(profile.get("separate_from_undo_redo") is True, "Style Memory must be separate from undo/redo", errors)
        expect(profile.get("separate_from_ai_revision_memory") is True, "Style Memory must be separate from AI revision memory", errors)
        expect(profile.get("public_handoff_summary", {}).get("content_free") is True, "Style Memory handoff summary must be content-free", errors)
    views = data.get("published_views", [])
    expect({view.get("plan") for view in views} >= {"free", "paid"}, "published viewer must include Free and Paid share posture", errors)
    for view in views:
        expect(view.get("read_only") is True, "published viewer must be read-only", errors)
        expect(view.get("editing_api_exposed") is False, "published viewer must not expose editing API", errors)
        expect(view.get("raw_workbench_state_exposed") is False, "published viewer must not expose raw workbench state", errors)
        expect(view.get("raw_asset_urls_exposed") is False, "published viewer must not expose raw asset URLs", errors)
        expect(view.get("package_internals_exposed") is False, "published viewer must not expose package internals", errors)
    free_view = next((view for view in views if view.get("plan") == "free"), {})
    paid_view = next((view for view in views if view.get("plan") == "paid"), {})
    expect(free_view.get("watermark") == "made_with_attribution", "Free published viewer must carry attribution/watermark", errors)
    expect(paid_view.get("watermark") == "none", "Paid published viewer must be watermark-free", errors)
    referral = data.get("referral_entitlement", {})
    plan_model = referral.get("plan_model", {})
    expect(plan_model.get("public_plans") == ["free", "paid"], "plan model must remain Free plus Paid", errors)
    expect(plan_model.get("paid_visible_per_edit_credit") is False, "Paid plan must avoid visible per-edit credit UX", errors)
    expect(referral.get("referral_code", {}).get("raw_signup_reward") is False, "referral reward must not be raw-signup based", errors)
    expect(referral.get("activation_events"), "referral activation event scaffold missing", errors)
    expect(referral.get("free_credit_ledger"), "free credit ledger scaffold missing", errors)
    expect(referral.get("paid_fair_use_entitlement", {}).get("normal_editing_visible_credit_meter") is False, "paid fair-use must be separate from free credit ledger", errors)
    generated = data.get("generated_work_state_loading", {})
    expect("host_ai_generated_work_state" in generated.get("accepted_input_kinds", []), "generated work-state loading path missing", errors)
    expect(generated.get("separate_from_fixture_data") is True, "generated work-state path must be separate from fixture data", errors)
    expect(generated.get("fixture_path") == "workbench-data.json", "fixture path must remain explicit", errors)
    expect(generated.get("generated_example_path") == "generated-work-state.example.json", "generated example path missing", errors)
    asset_system = data.get("asset_system_consumption", {})
    if asset_system.get("approved_package_consumed") or asset_system.get("approved_design_package_consumed"):
        expect(asset_system.get("render_use_evidence") is True, "approved asset/design package claims require render-use evidence", errors)
    else:
        expect(asset_system.get("ui_claim") == "asset-system-ready", "asset-system copy must remain ready/scaffold without approved evidence", errors)
        expect(asset_system.get("copy_must_not_claim_fused_assets") is True, "asset-system scaffold must block fused-asset claims", errors)
    local_assets = data.get("local_asset_connection_ux", {})
    expect(local_assets.get("font_connection", {}).get("stores_font_file") is False, "local font UX must not store font files in product state", errors)
    expect(local_assets.get("image_connection", {}).get("stores_raw_image_path") is False, "local image UX must not store raw image paths", errors)

    hooks = data.get("export_hooks", {})
    allowed = hooks.get("allowed_statuses", [])
    expect(
        allowed == [
            "handoff_ready",
            "handoff_sent",
            "awaiting_host_ai",
            "proposal_ready",
            "blocked",
            "final_received",
        ],
        "export status model mismatch",
        errors,
    )
    expect(hooks.get("current_status") == "handoff_ready", "export hook must start handoff_ready", errors)
    expect(hooks.get("real_host_result_ref") is None, "fixture must not include fake final result reference", errors)
    expect(hooks.get("proposal_return_handling", {}).get("raw_payload_stored") is False, "proposal return handling must not store raw payload", errors)
    expect(hooks.get("result_return_handling", {}).get("final_received_requires_real_result_ref") is True, "final_received must require a real result reference", errors)
    expect(hooks.get("direct_browser_dom_export") is False, "direct browser DOM export must be false", errors)
    expect(hooks.get("html_parsing_for_export") is False, "HTML parsing for export must be false", errors)
    expect(hooks.get("fake_completion_enabled") is False, "fake export completion must be disabled", errors)

    deck = data.get("deck", {})
    canvas = deck.get("canvas", {})
    slides = deck.get("slides", [])
    expect(canvas == {"width": 1600, "height": 900}, "workbench canvas must be 1600x900", errors)
    expect(len(slides) >= 10, "deck must contain at least 10 slides", errors)
    expect(deck.get("language") == "ko-KR", "Korean deck smoke language missing", errors)
    object_kinds: set[str] = set()
    page_numbers = 0
    korean_text_blocks = 0
    for index, slide in enumerate(slides, start=1):
        expect(slide.get("id"), f"slide {index} missing id", errors)
        expect(slide.get("title"), f"slide {index} missing title", errors)
        objects = slide.get("objects", [])
        expect(len(objects) >= 5, f"slide {index} too sparse for workbench smoke", errors)
        ids = [obj.get("id") for obj in objects]
        expect(len(ids) == len(set(ids)), f"slide {index} object ids are not unique", errors)
        if any(obj.get("text") == f"{index:02d}" for obj in objects if obj.get("type") == "text"):
            page_numbers += 1
        for obj in objects:
            object_kinds.add(str(obj.get("type")))
            for field in ("x", "y", "w", "h", "z"):
                expect(isinstance(obj.get(field), (int, float)), f"{obj.get('id')} missing numeric {field}", errors)
            if obj.get("type") == "text" and KOREAN_RE.search(str(obj.get("text", ""))):
                korean_text_blocks += 1
                expect(float(obj.get("lineHeight", 1.0)) >= 1.12, f"{obj.get('id')} Korean line height too tight", errors)
            if obj.get("type") == "image":
                expect(str(obj.get("safeRef", "")).startswith("asset:"), f"{obj.get('id')} image must use safe ref", errors)
                expect("://" not in str(obj.get("safeRef", "")), f"{obj.get('id')} image safe ref must not be URL", errors)
    expect({"text", "shape", "image", "table", "line"} <= object_kinds, "deck must include common editable object kinds", errors)
    expect(page_numbers == len(slides), "page number consistency missing", errors)
    expect(korean_text_blocks >= 20, "Korean text wrapping coverage too thin", errors)
    return {
        "slide_count": len(slides),
        "object_kinds": sorted(object_kinds),
        "page_numbered_slides": page_numbers,
        "korean_text_blocks": korean_text_blocks,
        "fixture_metadata": fixture,
        "master_style_surface": master_surface.get("surface_id"),
        "text_style_roles": sorted(roles),
        "design_package_source": design_package.get("source_kind"),
        "reference_design_importer_families": importer.get("benchmark_family_ids", []),
        "reference_design_recipes": len(library.get("recipes", [])),
        "reference_design_content_free_only": bool(library.get("recipes")) and all(recipe_is_content_free(recipe) for recipe in library.get("recipes", [])),
        "style_memory_profiles": len(style_profiles),
        "published_view_count": len(views),
        "referral_activation_events": len(referral.get("activation_events", [])),
        "asset_system_claim": asset_system.get("ui_claim"),
        "generated_work_state_loader": generated.get("load_path_status"),
    }


def validate_ui(texts: dict[str, str], errors: list[str]) -> dict[str, Any]:
    html = texts.get("index.html", "")
    js = texts.get("workbench.js", "")
    css = texts.get("styles.css", "")
    combined = f"{html}\n{js}\n{css}"
    required_markers = (
        "data-mode=\"assistant\"",
        "data-mode=\"auto\"",
        "data-action=\"export-pdf\"",
        "data-action=\"export-pptx\"",
        "data-surface=\"master-style\"",
        "data-surface=\"design-library\"",
        "data-surface=\"memory-share\"",
        "data-surface=\"export-handoff\"",
        "data-action=\"duplicate-object\"",
        "data-action=\"delete-object\"",
        "data-action=\"bring-forward\"",
        "data-action=\"send-backward\"",
        "data-action=\"align-left\"",
        "data-action=\"align-center\"",
        "data-action=\"align-right\"",
        "data-action=\"align-top\"",
        "data-action=\"align-middle\"",
        "data-action=\"align-bottom\"",
        "data-action=\"distribute-horizontal\"",
        "data-action=\"distribute-vertical\"",
        "data-action=\"rotate-minus-15\"",
        "data-action=\"rotate-plus-15\"",
        "data-action=\"rotate-minus-90\"",
        "data-action=\"rotate-plus-90\"",
        "data-action=\"rotate-reset\"",
        "data-action=\"flip-horizontal\"",
        "data-action=\"flip-vertical\"",
        "data-action=\"zoom-fit\"",
        "data-action=\"toggle-theme\"",
        "data-locale=\"ko\"",
        "data-locale=\"en\"",
        "id=\"text-role\"",
        "id=\"shape-radius\"",
        "id=\"master-palette\"",
        "id=\"master-type-scale\"",
        "id=\"master-radius\"",
        "id=\"reference-library\"",
        "id=\"style-memory\"",
        "id=\"published-view\"",
        "id=\"referral-credit\"",
        "id=\"local-assets\"",
        "id=\"object-style-summary\"",
        "data-action=\"style-memory-reset\"",
        "data-action=\"style-memory-delete\"",
        "data-action=\"master-apply\"",
        "data-action=\"master-override\"",
        "data-action=\"master-reset\"",
        "data-action=\"master-lock\"",
        "data-action=\"import-reference-recipes\"",
        "apply-reference-recipe",
        "data-action=\"reset-reference-recipe\"",
        "data-action=\"add-text\"",
        "data-dev-diagnostics hidden",
        "normalizeWorkbenchState",
        "textToParagraphs",
        "applyRichTextPatch",
        "toggleBullet",
        "selectedObjectIds",
        "distributeSelected",
        "transformSelected",
        "textRotationDisabled",
        "beginInlineTextEdit",
        "commitInlineTextEdit",
        "handlePlainTextPaste",
        "startObjectDrag",
        "startResize",
        "duplicateSelectedObject",
        "deleteSelectedObject",
        "changeZOrder",
        "referenceDesignHandoffSummary",
        "styleMemoryHandoffSummary",
        "publishedViewHandoffSummary",
        "referralCreditHandoffSummary",
        "safeAssetDesignRefs",
        "openFeatureSurface",
        "closeFeatureSurface",
        "applyMasterStyle",
        "importReferenceRecipes",
        "applyReferenceRecipe",
        "resetReferenceRecipe",
        "loadGeneratedWorkbenchState",
        "validateGeneratedWorkbenchInput",
        "resetStyleMemory",
        "deleteStyleMemory",
        "createExportEnvelope",
        "handoff_sent",
        "awaiting_host_ai",
        "proposal_ready",
        "blocked",
        "final_received",
        "@media (min-width: 1440px)",
        "@media (min-width: 1600px)",
        "@media (min-width: 1920px)",
        "@media (min-width: 2300px)",
        "@media (max-width: 1080px)",
        "published-viewer",
        "UI_TEXT",
        "applyLocaleText",
        "collectUnsafeAssetRefs",
        "MASTER_STYLE_PRESETS",
        "TYPE_SCALE_PRESETS",
    )
    missing = [marker for marker in required_markers if marker not in combined]
    for marker in missing:
        errors.append(f"workbench UI missing marker: {marker}")
    expect(html.count("data-mode=") == 2, "workbench must expose exactly two modes", errors)
    inspector_start = html.find('<aside class="inspector"')
    inspector_end = html.find("</aside>", inspector_start)
    inspector_html = html[inspector_start:inspector_end] if inspector_start >= 0 and inspector_end >= 0 else html
    moved_blocks = (
        "Master style",
        "AI revision memory",
        "Reference Design Library",
        "Style Memory",
        "Published viewer",
        "Referral and credits",
        "Local font/image links",
        "Host-AI export",
    )
    inspector_hits = [label for label in moved_blocks if label in inspector_html]
    for label in inspector_hits:
        errors.append(f"normal inspector still exposes moved product surface: {label}")
    expect("contenteditable" in js, "direct canvas editing must use an inline visible edit path", errors)
    expect("innerHTML" not in js, "workbench must avoid raw innerHTML updates", errors)
    expect("DOMParser" not in js, "workbench must not parse arbitrary DOM", errors)
    expect("function recipeIsContentFree" in js, "workbench UI must use shared content-free recipe predicate", errors)
    expect("content_free_preview?.placeholder_labels_only" in js and "synthetic_placeholder_preview?.placeholder_labels_only" in js, "workbench UI content-free predicate must accept legacy and current schemas", errors)
    expect("grid-template-rows: auto auto minmax(0, 1fr)" in css, "workbench product surfaces must not add a grid row that crushes canvas", errors)
    expect(".feature-surface {\n  position: fixed;" in css, "product surfaces must be overlay drawers", errors)
    expect("availableHeight" in texts.get("viewer.js", "") and "viewer-topbar-height" in texts.get("viewer.js", ""), "viewer scale must account for visible height and topbar", errors)
    return {
        "required_marker_count": len(required_markers),
        "missing_markers": missing,
        "diagnostics_hidden_markup": "data-dev-diagnostics hidden" in html,
        "normal_inspector_product_surface_hits": inspector_hits,
        "surface_overlay_drawer": ".feature-surface {\n  position: fixed;" in css,
        "viewer_height_aware_scaling": "availableHeight" in texts.get("viewer.js", ""),
        "content_free_predicate_shared": "function recipeIsContentFree" in js,
    }


def validate_viewer_payload(errors: list[str]) -> dict[str, Any]:
    path = WORKBENCH_DIR / "viewer-data.json"
    if not path.exists():
        errors.append("published viewer payload missing; run workbench build first")
        return {"viewer_data_present": False}
    data = read_json(path)
    expect(data.get("schema_version") == "commercial_mvp_published_viewer.v1", "published viewer schema mismatch", errors)
    expect(data.get("read_only") is True, "viewer payload must be read-only", errors)
    expect(data.get("editing_api_exposed") is False, "viewer payload must not expose editing API", errors)
    expect(data.get("raw_workbench_state_exposed") is False, "viewer payload must not expose raw workbench state", errors)
    expect(data.get("raw_asset_urls_exposed") is False, "viewer payload must not expose raw asset URLs", errors)
    expect(data.get("package_internals_exposed") is False, "viewer payload must not expose package internals", errors)
    forbidden_keys = {"revision_memory", "style_memory_profiles", "referral_entitlement", "export_hooks", "operation_log", "design_package", "reference_design_library"}
    encoded = json.dumps(data, ensure_ascii=False)
    for key in forbidden_keys:
        expect(key not in encoded, f"viewer payload exposes private workbench key: {key}", errors)
    return {
        "viewer_data_present": True,
        "slide_count": len(data.get("slides", [])),
        "read_only": data.get("read_only") is True,
        "watermark": data.get("watermark", {}),
    }


def validate_generated_work_state_example(errors: list[str]) -> dict[str, Any]:
    path = WORKBENCH_DIR / "generated-work-state.example.json"
    if not path.exists():
        errors.append("generated work-state example missing")
        return {"generated_example_present": False}
    data = read_json(path)
    expect(data.get("schema_version") == "commercial_mvp_generated_work_state.v1", "generated work-state schema mismatch", errors)
    expect(data.get("source_kind") == "host_ai_generated_work_state", "generated work-state must not be fixture", errors)
    expect(data.get("deck_id") != "safe-deck-smart-clinic-ops", "generated work-state must be separate from fixture deck id", errors)
    expect(data.get("design_package", {}).get("design_package_id") == "design-package-generated-loader-proof-v1", "generated work-state must carry custom design package proof", errors)
    expect(data.get("theme_tokens", {}).get("theme_id") == "theme-generated-loader-proof-green-v1", "generated work-state must carry custom theme proof", errors)
    expect(data.get("revision_memory", [{}])[0].get("memory_id") == "revmem-generated-example", "generated work-state must carry revision memory proof", errors)
    expect(data.get("export_hooks", {}).get("current_status") == "handoff_ready", "generated work-state must carry export state proof", errors)
    expect(data.get("forbidden_content_absent") is True, "generated work-state must declare forbidden content absent", errors)
    encoded = json.dumps(data, ensure_ascii=False)
    for marker in ("script_payload", "style_payload", "embed_payload", "package_internal_payload", "data" + ":image", "base" + "64,"):
        expect(marker not in encoded, f"generated work-state example contains blocked marker: {marker}", errors)
    return {
        "generated_example_present": True,
        "source_kind": data.get("source_kind"),
        "slide_count": len(data.get("slides", [])),
        "separate_from_fixture": data.get("deck_id") != "safe-deck-smart-clinic-ops",
        "design_package_id": data.get("design_package", {}).get("design_package_id"),
        "theme_id": data.get("theme_tokens", {}).get("theme_id"),
        "revision_memory_count": len(data.get("revision_memory", [])),
    }


def validate_generated_work_state_family_files(errors: list[str]) -> dict[str, Any]:
    state_dir = WORKBENCH_DIR / "generated-work-states"
    summaries: dict[str, Any] = {}
    for family in ("ir", "sales", "portfolio"):
        path = state_dir / f"{family}-final_user_test_polish.json"
        if not path.exists():
            errors.append(f"generated {family} work-state file missing")
            summaries[family] = {"present": False}
            continue
        data = read_json(path)
        encoded = json.dumps(data, ensure_ascii=False)
        expect(data.get("schema_version") == "commercial_mvp_generated_work_state.v1", f"{family} generated state schema mismatch", errors)
        expect(data.get("source_kind") == "host_ai_generated_work_state", f"{family} generated state source kind invalid", errors)
        expect(data.get("fixture") is False, f"{family} generated state fixture flag must be false", errors)
        expect(data.get("fixture_metadata", {}).get("is_fixture") is False, f"{family} generated state fixture metadata must be false", errors)
        expect(data.get("deck_id"), f"{family} generated state missing deck id", errors)
        expect(data.get("safe_label"), f"{family} generated state missing safe label", errors)
        expect(data.get("design_package", {}).get("design_package_id"), f"{family} generated state missing design package id", errors)
        expect(data.get("theme_tokens", {}).get("theme_id"), f"{family} generated state missing theme id", errors)
        expect(len(data.get("revision_memory", [])) >= 1, f"{family} generated state missing revision memory", errors)
        expect(data.get("export_hooks", {}).get("current_status") == "handoff_ready", f"{family} generated state must start handoff_ready", errors)
        expect(data.get("export_hooks", {}).get("real_host_result_ref") is None, f"{family} generated state must not fake final result", errors)
        safe_refs = data.get("safe_asset_refs", [])
        expect(len(safe_refs) >= 3, f"{family} generated state safe asset refs missing", errors)
        for ref in safe_refs:
            value = str(ref.get("safe_asset_ref", ""))
            expect(value.startswith("asset:"), f"{family} safe asset ref must start with asset:", errors)
            expect("://" not in value and "\\" not in value and "/" not in value, f"{family} safe asset ref must not be path or URL", errors)
        recipes = data.get("reference_design_library", {}).get("recipes", [])
        expect(recipes and all(recipe_is_content_free(recipe) for recipe in recipes), f"{family} generated state must reference content-free RDL recipe", errors)
        for marker in ("script_payload", "style_payload", "embed_payload", "package_internal_payload", "data" + ":image", "base" + "64,", "sample" + "_html_slides", "sample" + "_pptx_slides"):
            expect(marker not in encoded, f"{family} generated state contains blocked marker: {marker}", errors)
        summaries[family] = {
            "present": True,
            "deck_id": data.get("deck_id"),
            "safe_label": data.get("safe_label"),
            "fixture": data.get("fixture"),
            "slide_count": len(data.get("slides", [])),
            "design_package_id": data.get("design_package", {}).get("design_package_id"),
            "theme_id": data.get("theme_tokens", {}).get("theme_id"),
            "revision_memory_count": len(data.get("revision_memory", [])),
            "export_status": data.get("export_hooks", {}).get("current_status"),
            "safe_asset_ref_count": len(safe_refs),
            "reference_recipe_ids": [recipe.get("recipe_id") for recipe in recipes],
        }
    return summaries


def simulate_object_edits(data: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    deck = json.loads(json.dumps(data["deck"]))
    slide = deck["slides"][0]
    text_obj = next(obj for obj in slide["objects"] if obj["type"] == "text")
    image_obj = next(obj for obj in slide["objects"] if obj["type"] == "image")
    original_text = text_obj["text"]
    original_x = image_obj["x"]
    original_w = image_obj["w"]
    original_z = image_obj["z"]

    text_obj["text"] = "직접 편집 smoke: 한국어 줄바꿈 확인"
    image_obj["x"] += 25
    image_obj["w"] += 40
    copied = json.loads(json.dumps(image_obj))
    copied["id"] = "validator-duplicate"
    copied["z"] = max(obj["z"] for obj in slide["objects"]) + 1
    slide["objects"].append(copied)
    slide["objects"] = [obj for obj in slide["objects"] if obj["id"] != copied["id"]]
    image_obj["z"] += 1
    image_obj["rotation"] = 15
    image_obj["flipX"] = True
    image_obj["flipY"] = True
    shape_obj = next(obj for obj in slide["objects"] if obj["type"] == "shape")
    shape_obj["radius"] = 24

    selected = [obj for obj in slide["objects"] if obj["type"] in {"text", "shape"}][:3]
    left = min(obj["x"] for obj in selected)
    for obj in selected:
        obj["x"] = left
    top_values = [obj["y"] for obj in sorted(selected, key=lambda item: item["y"])]
    if len(top_values) >= 3:
        step = (top_values[-1] - top_values[0]) / (len(top_values) - 1)
        distributed = [round(top_values[0] + step * index) for index in range(len(top_values))]
    else:
        distributed = top_values
    text_obj["textRole"] = "Bullet"
    text_obj["paragraphs"] = [
        {
            "role": "Bullet",
            "alignment": "left",
            "bullet": True,
            "bulletLevel": 0,
            "spacingAfter": 4,
            "overflowPolicy": "wrap",
            "runs": [
                {"text": "직접 편집 smoke: ", "fontSize": 24, "fontWeight": 600, "color": "#151515"},
                {"text": "한국어 줄바꿈", "fontSize": 24, "fontWeight": 800, "color": "#F2D76B"},
            ],
        }
    ]

    expect(text_obj["text"] != original_text, "text edit simulation did not mutate state", errors)
    expect(image_obj["x"] != original_x, "move simulation did not mutate state", errors)
    expect(image_obj["w"] != original_w, "resize simulation did not mutate state", errors)
    expect(image_obj["z"] > original_z, "z-order simulation did not mutate state", errors)
    expect(image_obj["rotation"] == 15 and image_obj["flipX"] and image_obj["flipY"], "shape/image transform simulation failed", errors)
    expect(shape_obj["radius"] == 24, "shape radius simulation failed", errors)
    expect(text_obj["paragraphs"][0]["bullet"] is True, "bullet paragraph simulation failed", errors)
    expect(len(text_obj["paragraphs"][0]["runs"]) == 2, "rich text run simulation failed", errors)
    expect(all(obj["id"] != "validator-duplicate" for obj in slide["objects"]), "delete simulation failed", errors)
    return {
        "direct_text_edit_mutated": text_obj["text"] != original_text,
        "move_mutated": image_obj["x"] != original_x,
        "resize_mutated": image_obj["w"] != original_w,
        "duplicate_then_delete_covered": all(obj["id"] != "validator-duplicate" for obj in slide["objects"]),
        "z_order_mutated": image_obj["z"] > original_z,
        "multi_select_align_covered": len({obj["x"] for obj in selected}) == 1,
        "distribute_covered": distributed == sorted(distributed),
        "shape_image_transform_covered": image_obj["rotation"] == 15 and image_obj["flipX"] and image_obj["flipY"],
        "shape_radius_covered": shape_obj["radius"] == 24,
        "paragraph_bullet_covered": text_obj["paragraphs"][0]["bullet"] is True,
        "rich_text_runs_covered": len(text_obj["paragraphs"][0]["runs"]) == 2,
    }


def write_report(report: Path, payload: dict[str, Any]) -> None:
    write_json(report, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Commercial MVP HTML slide workbench.")
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args(argv)
    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()

    errors: list[str] = []
    texts = collect_file_text(errors)
    data = read_json(DATA_PATH)
    data_summary = validate_data(data, errors)
    ui_summary = validate_ui(texts, errors)
    boundary_summary = validate_private_boundary(texts, data, errors)
    edit_summary = simulate_object_edits(data, errors)
    viewer_summary = validate_viewer_payload(errors)
    generated_summary = validate_generated_work_state_example(errors)
    generated_family_summary = validate_generated_work_state_family_files(errors)
    content_free_schema_parity = validate_content_free_schema_parity(errors)
    payload = {
        "schema_version": "commercial_mvp_html_workbench_validation.v1",
        "status": "valid" if not errors else "invalid",
        "data_summary": data_summary,
        "ui_summary": ui_summary,
        "private_boundary": boundary_summary,
        "edit_simulation": edit_summary,
        "viewer_read_only": viewer_summary,
        "generated_work_state": generated_summary,
        "generated_work_state_families": generated_family_summary,
        "content_free_schema_parity": content_free_schema_parity,
        "export_hook_honesty": {
            "pdf_hook_present": True,
            "pptx_hook_present": True,
            "fake_final_success": False,
            "real_final_result_reference_present": False,
            "direct_browser_dom_export": False,
        },
        "errors": errors,
    }
    write_report(report, payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "commercial_mvp_html_workbench=valid "
        f"slides={data_summary['slide_count']} korean_text_blocks={data_summary['korean_text_blocks']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
