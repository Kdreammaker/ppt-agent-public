from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

COMPILE_TARGETS = [
    "system/blueprint_loader.py",
    "system/deck_models.py",
    "system/guide_packet.py",
    "system/intake_models.py",
    "system/pptx_system.py",
    "system/strategy_router.py",
    "system/template_engine.py",
    "system/template_text_dna.py",
    "system/text_summarizer.py",
    "scripts/manage_template_slot_names.py",
    "scripts/build_template_libraries.py",
    "scripts/build_reference_catalog.py",
    "scripts/build_template_design_dna.py",
    "scripts/validate_template_design_dna.py",
    "scripts/build_ppt_asset_catalog.py",
    "scripts/validate_ppt_asset_catalog.py",
    "scripts/validate_public_gate_toolkit_dependency.py",
    "scripts/validate_brand_style_contract.py",
    "scripts/validate_public_gate_sync_path.py",
    "scripts/bootstrap_public_gate_workspace.py",
    "scripts/validate_public_private_ci_boundary.py",
    "scripts/validate_security_permission_policy.py",
    "scripts/validate_public_thin_ppt_smoke.py",
    "scripts/ppt_private_connector.py",
    "scripts/private_runtime_build_bridge.py",
    "scripts/validate_public_private_runtime_connector.py",
    "scripts/validate_private_mode_parity.py",
    "scripts/render_template_thumbnails.py",
    "scripts/recommend_assistant_templates.py",
    "scripts/validate_assistant_visual_recommendations.py",
    "scripts/run_auto_self_correction.py",
    "scripts/validate_auto_self_correction_report.py",
    "scripts/validate_auto_mode_pipeline.py",
    "scripts/validate_chart_table_slots.py",
    "scripts/validate_template_text_dna_cleanup.py",
    "scripts/analyze_responsive_blueprint_readiness.py",
    "scripts/build_html_deck.py",
    "scripts/validate_html_output.py",
    "scripts/build_dual_outputs.py",
    "scripts/validate_dual_output_flow.py",
    "scripts/patch_deck_spec.py",
    "scripts/validate_spec_patch_flow.py",
    "scripts/ppt_cli_history.py",
    "scripts/validate_cli_history.py",
    "scripts/mcp_adapter.py",
    "scripts/validate_mcp_adapter.py",
    "scripts/ppt_agent.py",
    "scripts/ppt_agent_mcp_adapter.py",
    "scripts/validate_agent_skill_contract.py",
    "scripts/validate_agent_skill_smoke.py",
    "scripts/validate_auto_strategy_registry.py",
    "scripts/validate_guide_packet_pipeline.py",
    "scripts/validate_intent_taxonomy.py",
    "scripts/validate_strategy_router.py",
    "scripts/render_ascii_blueprint.py",
    "scripts/validate_ascii_blueprint.py",
    "scripts/validate_blueprint_mode_policy.py",
    "scripts/build_reference_quality_dna.py",
    "scripts/validate_reference_quality_dna.py",
    "scripts/mock_gateway_metadata_recommendation.py",
    "scripts/validate_gateway_metadata_recommendation_mock.py",
    "scripts/build_deck.py",
    "scripts/build_variant_review_deck.py",
    "scripts/test_llm_summary_guardrail.py",
    "scripts/test_runtime_enhancements.py",
    "scripts/test_variation_penalty.py",
    "scripts/test_intake_composer_guardrails.py",
    "scripts/test_industry_spec_composer.py",
    "scripts/validate_asset_aware_composer.py",
    "scripts/validate_public_cli_contract.py",
    "scripts/validate_private_gateway_contract.py",
    "scripts/validate_gateway_contract_hardening.py",
    "scripts/validate_invite_beta_release_boundary.py",
    "scripts/validate_private_invite_installer.py",
    "scripts/ppt_workspace_entitlement.py",
    "scripts/validate_workspace_code_entitlement.py",
    "scripts/validate_workspace_code_issuance_masking.py",
    "scripts/validate_workspace_code_admin_fixtures.py",
    "scripts/validate_private_admin_gateway_activation_service.py",
    "scripts/validate_local_path_hardening.py",
    "scripts/ppt_support_bundle.py",
    "scripts/validate_local_diagnostic_support_bundle.py",
    "scripts/build_clean_release_export.py",
    "scripts/validate_clean_release_export.py",
    "scripts/validate_beta_output_quality.py",
    "scripts/validate_output_quality_gates.py",
    "scripts/validate_first_slide_quality.py",
    "scripts/validate_visual_content_image_gate.py",
    "scripts/build_beta_packaging_dry_run.py",
    "scripts/validate_beta_packaging_dry_run.py",
    "scripts/validate_public_private_repo_split.py",
    "scripts/validate_beta_documentation_pack.py",
    "scripts/validate_invite_beta_final_qa.py",
    "scripts/validate_post_beta_cto_product_review.py",
    "scripts/validate_document_rag_intake_evaluation.py",
    "scripts/validate_invite_beta_acceptance_matrix.py",
    "scripts/validate_invite_beta_release_candidate_gate.py",
    "scripts/validate_golden_path_beta_ux.py",
    "scripts/ppt_cli_workspace.py",
    "scripts/validate_public_cli_workspace.py",
    "scripts/validate_pattern_selection_intelligence.py",
    "scripts/validate_deck_intake.py",
    "scripts/normalize_slack_intake.py",
    "scripts/validate_slack_intake_contract.py",
    "scripts/maker_runtime.py",
    "scripts/validate_maker_runtime_execution.py",
    "scripts/validate_slide_feedback_memory.py",
    "scripts/validate_reference_curation.py",
    "scripts/validate_template_library_grades.py",
    "scripts/apply_reference_review_labels.py",
    "scripts/reference_pipeline.py",
    "scripts/output_bundles.py",
    "scripts/deliver_project_output.py",
    "scripts/send_delivery_slack_message.py",
    "scripts/build_delivery_summary.py",
    "scripts/validate_delivery_summary_contract.py",
    "scripts/parse_reference_deck.py",
    "scripts/sync_reference_quality_buckets.py",
    "scripts/compose_deck_spec_from_intake.py",
    "scripts/validate_template_blueprints.py",
    "scripts/validate_visual_smoke.py",
    "scripts/validate_design_quality.py",
    "scripts/validate_deck_design_review.py",
    "scripts/validate_pptx_package.py",
    "scripts/inspect_template_aspect_ratios.py",
    "scripts/inspect_template_static_artifacts.py",
    "scripts/diagnose_template_text_readback.py",
    "scripts/validate_visual_drift.py",
    "scripts/build_template_index_db.py",
    "scripts/validate_project_manifest.py",
    "scripts/validate_run_manifest.py",
    "scripts/validate_output_delivery_manifest.py",
    "scripts/validate_production_build_bundle.py",
    "scripts/ppt_system.py",
    "scripts/run_regression_gate.py",
]

LLM_SUMMARY_ENV_KEYS = [
    "PPTX_ENABLE_LLM_SUMMARY",
    "PPTX_LLM_SUMMARY_MOCK_JSON",
    "PPTX_LLM_SUMMARY_MOCK_TEXT",
]

REGRESSION_SPECS = [
    "data/specs/jb_meeting_component_preset_spec.json",
    "data/specs/jb_meeting_design_elevated_spec.json",
    "data/specs/jb_meeting_component_modular_spec.json",
    "data/specs/jb_meeting_deck_spec.json",
    "data/specs/jb_meeting_blueprint_spec.json",
    "data/specs/portfolio_auto_selection_sample.json",
    "data/specs/report_auto_selection_sample.json",
    "data/specs/sales_auto_selection_sample.json",
    "data/specs/template_slide_sample_spec.json",
    "data/specs/chart_table_slot_sample_spec.json",
    "data/specs/business_growth_review_spec.json",
    "data/specs/travel_experience_plan_spec.json",
]

DECKS = [
    "outputs/decks/jb_meeting_component_preset_system.pptx",
    "outputs/decks/jb_meeting_design_elevated_system.pptx",
    "outputs/decks/jb_meeting_component_modular_system.pptx",
    "outputs/decks/jb_meeting_internal_share_deck_system.pptx",
    "outputs/decks/jb_meeting_blueprint_system.pptx",
    "outputs/decks/portfolio_auto_selection_sample.pptx",
    "outputs/decks/report_auto_selection_sample.pptx",
    "outputs/decks/sales_auto_selection_sample.pptx",
    "outputs/decks/template_slide_sample_system.pptx",
    "outputs/decks/chart_table_slot_sample.pptx",
    "outputs/decks/business_growth_review.pptx",
    "outputs/decks/travel_experience_plan.pptx",
]

VISUAL_SMOKE = [
    ("outputs/decks/jb_meeting_component_preset_system.pptx", "outputs/reports/jb_meeting_component_preset_visual_smoke.json", "data/specs/jb_meeting_component_preset_spec.json"),
    ("outputs/decks/jb_meeting_design_elevated_system.pptx", "outputs/reports/jb_meeting_design_elevated_visual_smoke.json", "data/specs/jb_meeting_design_elevated_spec.json"),
    ("outputs/decks/jb_meeting_component_modular_system.pptx", "outputs/reports/jb_meeting_component_modular_visual_smoke.json", "data/specs/jb_meeting_component_modular_spec.json"),
    ("outputs/decks/jb_meeting_internal_share_deck_system.pptx", "outputs/reports/jb_meeting_internal_share_deck_visual_smoke.json", "data/specs/jb_meeting_deck_spec.json"),
    ("outputs/decks/jb_meeting_blueprint_system.pptx", "outputs/reports/jb_meeting_blueprint_visual_smoke.json", "data/specs/jb_meeting_blueprint_spec.json"),
    ("outputs/decks/portfolio_auto_selection_sample.pptx", "outputs/reports/portfolio_auto_selection_sample_visual_smoke.json", "data/specs/portfolio_auto_selection_sample.json"),
    ("outputs/decks/report_auto_selection_sample.pptx", "outputs/reports/report_auto_selection_sample_visual_smoke.json", "data/specs/report_auto_selection_sample.json"),
    ("outputs/decks/sales_auto_selection_sample.pptx", "outputs/reports/sales_auto_selection_sample_visual_smoke.json", "data/specs/sales_auto_selection_sample.json"),
    ("outputs/decks/template_slide_sample_system.pptx", "outputs/reports/template_slide_sample_visual_smoke.json", "data/specs/template_slide_sample_spec.json"),
    ("outputs/decks/chart_table_slot_sample.pptx", "outputs/reports/chart_table_slot_sample_visual_smoke.json", "data/specs/chart_table_slot_sample_spec.json"),
]

QUALITY = [
    ("outputs/decks/jb_meeting_component_preset_system.pptx", "outputs/reports/jb_meeting_component_preset_quality.json", None),
    ("outputs/decks/jb_meeting_design_elevated_system.pptx", "outputs/reports/jb_meeting_design_elevated_quality.json", None),
    ("outputs/decks/jb_meeting_component_modular_system.pptx", "outputs/reports/jb_meeting_component_modular_quality.json", None),
    ("outputs/decks/jb_meeting_internal_share_deck_system.pptx", "outputs/reports/jb_meeting_internal_share_deck_quality.json", None),
    ("outputs/decks/template_slide_sample_system.pptx", "outputs/reports/template_slide_sample_quality.json", "data/specs/template_slide_sample_spec.json"),
]


def run(args: list[str]) -> None:
    printable = " ".join(args)
    print(f"$ {printable}", flush=True)
    subprocess.run(args, cwd=BASE_DIR, check=True)


def disable_llm_summary_for_gate() -> None:
    for key in LLM_SUMMARY_ENV_KEYS:
        os.environ.pop(key, None)


def load_json(path: str) -> dict:
    return json.loads((BASE_DIR / path).read_text(encoding="utf-8"))


def assert_zero_summary(report_path: str, label: str) -> None:
    data = load_json(report_path)
    summary = data.get("summary", data)
    for key in ("errors", "warnings"):
        value = summary.get(key, 0)
        if value != 0:
            raise AssertionError(f"{label} has {key}={value}: {report_path}")
    issues = summary.get("issues", summary.get("issue_count", 0))
    issue_count = len(issues) if isinstance(issues, list) else issues
    if issue_count != 0:
        raise AssertionError(f"{label} has issues={issue_count}: {report_path}")


def assert_slot_invariants() -> None:
    audit = load_json("outputs/reports/template_slot_name_audit.json")
    manifest = load_json("config/template_slot_name_manifest.json")
    status = audit["summary"]["by_status"]
    result = {
        "ok": status.get("ok", 0),
        "rename_available": status.get("rename_available", 0),
        "manifest_count": len(manifest.get("entries", [])),
    }
    print(f"slot_invariants={result}")
    if result != {"ok": 958, "rename_available": 0, "manifest_count": 958}:
        raise AssertionError(f"Unexpected slot invariants: {result}")


def assert_design_dna_coverage() -> None:
    reference = load_json("config/reference_catalog.json")
    design_dna = load_json("config/template_design_dna.json")
    reference_slide_ids = {slide["slide_id"] for slide in reference.get("slides", [])}
    dna_slide_ids = set(design_dna.get("slides", {}))
    missing = sorted(reference_slide_ids - dna_slide_ids)
    extra = sorted(dna_slide_ids - reference_slide_ids)
    if missing or extra:
        raise AssertionError(
            f"Template Design DNA coverage mismatch: missing={missing[:5]}, extra={extra[:5]}"
        )
    print(f"design_dna_slides={len(dna_slide_ids)}")


def assert_reports() -> None:
    for _, report, _ in VISUAL_SMOKE:
        assert_zero_summary(report, "visual smoke")
    for _, report, _ in QUALITY:
        assert_zero_summary(report, "design quality")

    readback = load_json("outputs/reports/template_text_readback_diagnostics.json").get("summary", {})
    if readback.get("total_rows") != 174 or readback.get("by_classification", {}).get("present") != 174:
        raise AssertionError(f"Unexpected readback summary: {readback}")

    drift = load_json("outputs/reports/visual_baseline_drift.json")
    if drift.get("structural_errors") != 0:
        raise AssertionError(f"Visual drift structural_errors={drift.get('structural_errors')}")
    overflow_events = 0
    rationale_reports = 0
    slot_map_reports = 0
    for deck in DECKS:
        report = f"outputs/reports/{Path(deck).stem}_text_overflow.json"
        payload = load_json(report)
        overflow_events += int(payload.get("summary", {}).get("cutoff_events", 0))
        rationale_report = f"outputs/reports/{Path(deck).stem}_slide_selection_rationale.json"
        rationale_payload = load_json(rationale_report)
        if int(rationale_payload.get("summary", {}).get("slides", 0)) <= 0:
            raise AssertionError(f"Slide selection rationale report has no slides: {rationale_report}")
        rationale_reports += 1
        slot_map_report = f"outputs/reports/{Path(deck).stem}_deck_slot_map.json"
        slot_map_payload = load_json(slot_map_report)
        if int(slot_map_payload.get("summary", {}).get("mapped_slots", 0)) <= 0:
            raise AssertionError(f"Deck slot map report has no mapped slots: {slot_map_report}")
        slot_map_reports += 1
    print(
        "report_invariants="
        + json.dumps(
            {
                "visual_reports": len(VISUAL_SMOKE),
                "quality_reports": len(QUALITY),
                "rationale_reports": rationale_reports,
                "slot_map_reports": slot_map_reports,
                "readback_total": readback.get("total_rows"),
                "drift_warning_slides": drift.get("warning_slides", 0),
                "text_cutoff_events": overflow_events,
            },
            ensure_ascii=False,
        )
    )


def slide_selection_rationale_reports() -> list[str]:
    return [
        f"outputs/reports/{Path(deck).stem}_slide_selection_rationale.json"
        for deck in DECKS
    ]


def main() -> int:
    disable_llm_summary_for_gate()
    run([sys.executable, "-m", "py_compile", *COMPILE_TARGETS])
    run([sys.executable, "scripts/test_llm_summary_guardrail.py"])
    run([sys.executable, "scripts/test_runtime_enhancements.py"])
    run([sys.executable, "scripts/test_variation_penalty.py"])
    run([sys.executable, "scripts/test_intake_composer_guardrails.py"])
    run([sys.executable, "scripts/test_industry_spec_composer.py"])
    run([sys.executable, "scripts/validate_asset_aware_composer.py"])
    run([sys.executable, "scripts/validate_public_cli_contract.py"])
    run([sys.executable, "scripts/validate_private_gateway_contract.py"])
    run([sys.executable, "scripts/validate_gateway_contract_hardening.py"])
    run([sys.executable, "scripts/validate_invite_beta_release_boundary.py"])
    run([sys.executable, "scripts/validate_private_invite_installer.py"])
    run([sys.executable, "scripts/validate_workspace_code_entitlement.py"])
    run([sys.executable, "scripts/validate_workspace_code_issuance_masking.py"])
    run([sys.executable, "scripts/validate_workspace_code_admin_fixtures.py"])
    run([sys.executable, "scripts/validate_private_admin_gateway_activation_service.py"])
    run([sys.executable, "scripts/validate_local_path_hardening.py"])
    run([sys.executable, "scripts/validate_local_diagnostic_support_bundle.py"])
    run([sys.executable, "scripts/validate_clean_release_export.py"])
    run([sys.executable, "scripts/validate_beta_output_quality.py"])
    run([sys.executable, "scripts/validate_output_quality_gates.py"])
    run([sys.executable, "scripts/validate_first_slide_quality.py"])
    run([sys.executable, "scripts/validate_visual_content_image_gate.py"])
    run([sys.executable, "scripts/validate_beta_packaging_dry_run.py"])
    run([sys.executable, "scripts/validate_public_private_repo_split.py"])
    run([sys.executable, "scripts/validate_beta_documentation_pack.py"])
    run([sys.executable, "scripts/validate_invite_beta_acceptance_matrix.py"])
    run([sys.executable, "scripts/validate_invite_beta_release_candidate_gate.py"])
    run([sys.executable, "scripts/validate_invite_beta_final_qa.py"])
    run([sys.executable, "scripts/validate_post_beta_cto_product_review.py"])
    run([sys.executable, "scripts/validate_document_rag_intake_evaluation.py"])
    run([sys.executable, "scripts/validate_golden_path_beta_ux.py"])
    run([sys.executable, "scripts/validate_public_cli_workspace.py"])
    run([sys.executable, "scripts/validate_deck_intake.py"])
    run([sys.executable, "scripts/validate_slack_intake_contract.py"])
    run([sys.executable, "scripts/validate_maker_runtime_execution.py"])
    run([sys.executable, "scripts/validate_slide_feedback_memory.py"])
    run([sys.executable, "scripts/validate_reference_curation.py"])
    run([sys.executable, "scripts/build_production_template_index.py"])
    run([sys.executable, "scripts/validate_template_library_grades.py"])
    run([sys.executable, "scripts/build_ppt_asset_catalog.py"])
    run([sys.executable, "scripts/validate_ppt_asset_catalog.py"])
    run([sys.executable, "scripts/validate_public_gate_toolkit_dependency.py"])
    run([sys.executable, "scripts/validate_brand_style_contract.py"])
    run([sys.executable, "scripts/validate_public_gate_sync_path.py"])
    run([sys.executable, "scripts/bootstrap_public_gate_workspace.py", "--workspace", "outputs/bootstrap_smoke_workspace", "--force-readme"])
    run([sys.executable, "scripts/validate_public_private_ci_boundary.py"])
    run([sys.executable, "scripts/validate_security_permission_policy.py"])
    run([sys.executable, "scripts/validate_public_thin_ppt_smoke.py", "--skip-export-refresh"])
    run([sys.executable, "scripts/validate_public_private_runtime_connector.py"])
    run([sys.executable, "scripts/validate_private_mode_parity.py"])
    run([sys.executable, "scripts/validate_template_blueprints.py"])
    run(
        [
            sys.executable,
            "scripts/manage_template_slot_names.py",
            "--output-json",
            "outputs/reports/template_slot_name_audit.json",
            "--output-md",
            "outputs/reports/template_slot_name_audit.md",
            "--summary",
        ]
    )
    assert_slot_invariants()
    assert_design_dna_coverage()
    run([sys.executable, "scripts/validate_template_design_dna.py"])
    run([sys.executable, "scripts/render_template_thumbnails.py", "--check"])
    run([sys.executable, "scripts/recommend_assistant_templates.py", "--sample", "--check"])
    run([sys.executable, "scripts/validate_assistant_visual_recommendations.py"])
    run([sys.executable, "scripts/run_auto_self_correction.py", "--spec", "data/specs/template_slide_sample_spec.json", "--max-attempts", "2", "--check"])
    run([sys.executable, "scripts/validate_auto_self_correction_report.py"])
    run([sys.executable, "scripts/validate_auto_mode_pipeline.py"])
    run([sys.executable, "scripts/validate_chart_table_slots.py"])
    run([sys.executable, "scripts/analyze_responsive_blueprint_readiness.py"])
    run([sys.executable, "scripts/compose_deck_spec_from_intake.py", "data/intake/business_growth_review.json"])
    run([sys.executable, "scripts/compose_deck_spec_from_intake.py", "data/intake/travel_experience_plan.json"])
    run([sys.executable, "scripts/build_html_deck.py", "data/specs/business_growth_review_spec.json"])
    run(
        [
            sys.executable,
            "scripts/validate_html_output.py",
            "outputs/html/business_growth_review/index.html",
            "--manifest",
            "outputs/html/business_growth_review/html_manifest.json",
        ]
    )
    run([sys.executable, "scripts/validate_dual_output_flow.py"])
    run([sys.executable, "scripts/validate_spec_patch_flow.py"])
    run([sys.executable, "scripts/validate_cli_history.py"])
    run([sys.executable, "scripts/validate_mcp_adapter.py"])
    run([sys.executable, "scripts/validate_auto_strategy_registry.py"])
    run([sys.executable, "scripts/validate_intent_taxonomy.py"])
    run([sys.executable, "scripts/validate_strategy_router.py"])
    run([sys.executable, "scripts/validate_guide_packet_pipeline.py"])
    run([sys.executable, "scripts/validate_agent_skill_contract.py"])
    run([sys.executable, "scripts/validate_agent_skill_smoke.py"])
    run([sys.executable, "scripts/validate_ascii_blueprint.py"])
    run([sys.executable, "scripts/validate_blueprint_mode_policy.py"])
    run([sys.executable, "scripts/validate_reference_quality_dna.py"])
    run([sys.executable, "scripts/validate_gateway_metadata_recommendation_mock.py"])

    for spec in REGRESSION_SPECS:
        run([sys.executable, "scripts/build_deck.py", spec])

    run([sys.executable, "scripts/validate_pptx_package.py", *DECKS])
    run([sys.executable, "scripts/validate_template_text_dna_cleanup.py"])

    for deck, report, spec in VISUAL_SMOKE:
        run([sys.executable, "scripts/validate_visual_smoke.py", deck, report, "--spec", spec, "--keep-images"])

    for deck, report, spec in QUALITY:
        args = [sys.executable, "scripts/validate_design_quality.py", deck, report]
        if spec:
            args.extend(["--template-spec", spec])
        run(args)

    run(
        [
            sys.executable,
            "scripts/diagnose_template_text_readback.py",
            "--output-json",
            "outputs/reports/template_text_readback_diagnostics.json",
            "--output-md",
            "outputs/reports/template_text_readback_diagnostics.md",
        ]
    )
    run([sys.executable, "scripts/validate_visual_drift.py"])
    run(
        [
            sys.executable,
            "scripts/validate_deck_design_review.py",
            "--gate-config",
            "config/deck_design_review_gate.json",
            "--enforce-gate-config",
        ]
    )
    run([sys.executable, "scripts/validate_production_build_bundle.py"])
    run([sys.executable, "scripts/validate_delivery_summary_contract.py"])
    pattern_selection_args = [sys.executable, "scripts/validate_pattern_selection_intelligence.py"]
    for report in slide_selection_rationale_reports():
        pattern_selection_args.extend(["--report", report])
    run(pattern_selection_args)
    assert_reports()
    print("regression gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
