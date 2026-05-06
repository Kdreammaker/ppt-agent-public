from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.public_report_safety import public_report_issues

PROMPT = "Create a 4-slide planning-first presentation about a beta launch readiness review."
REPO_REPORT_ROOT = BASE_DIR / "outputs" / "reports"
CAPABILITY_KEYS = (
    "output_intent_bounded_effects",
    "approved_package_asset_insertion",
    "approved_structured_native_chart_table_rendering",
    "shared_ir_safe_area_native_chart_table_bounds",
    "b54_style_token_guidance",
)
BLOCKER_KEYS = {
    "shared_ir_layout_density_geometry_text_slot_asset_slot_consumption",
    "font_materialization_without_approved_opaque_package_evidence",
    "html_screenshots_inserted_into_pptx",
    "public_exposure_of_package_internals_or_private_ids",
}
PRIVATE_PATTERNS = {
    "private_path": re.compile(r"[A-Za-z]:\\|/Users/|/home/"),
    "drive_marker": re.compile(r"drive\.google\.com|docs\.google\.com|\bdrive[_-]?id\b", re.IGNORECASE),
    "token": re.compile(r"xox(?:[abprs]|c|d)-|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}", re.IGNORECASE),
    "raw_marker": re.compile(
        r"\bprivate_prompt\b|\braw_payload\b|\bsource_attachment\b|\bapproved_asset_ref\b|\bpreferred_asset_ref\b|\bunapproved_asset_records\b|\bslot_id\b",
        re.IGNORECASE,
    ),
    "package_internal_marker": re.compile(
        r"\bpackage_manifest_id\b|\bstructured_data_id\b|\bpackage[-_: ]manifest[-_: ][A-Za-z0-9_.:-]+\b|\bstructured[-_: ]data[-_: ][A-Za-z0-9_.:-]+\b|\bpackage manifest\b|\binternal package\b|\braw manifest\b|\braw package\b|\braw structured[-_ ]data\b",
        re.IGNORECASE,
    ),
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert_true(isinstance(payload, dict), f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def repo_report_snapshot() -> dict[str, tuple[int, int]]:
    if not REPO_REPORT_ROOT.exists():
        return {}
    snapshot: dict[str, tuple[int, int]] = {}
    for path in REPO_REPORT_ROOT.rglob("*"):
        if path.is_file():
            stat = path.stat()
            snapshot[path.relative_to(REPO_REPORT_ROOT).as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def repo_report_changes(before: dict[str, tuple[int, int]]) -> list[str]:
    after = repo_report_snapshot()
    return sorted(name for name, state in after.items() if before.get(name) != state)


def write_auto_fixture(path: Path, *, malicious: bool = False) -> Path:
    payload = {
        "contract": "ppt-maker.auto-output-intent-policy.v0",
        "status": "ready_for_public_beta_metadata",
        "selected_output_intent": "editable_office",
        "two_variant_policy": {
            "variant_count": 2,
            "variant_ids": ["variant-a", "variant-b"],
            "redesign_enabled": False,
            "variants_receive_same_output_intent": True,
            "selection_policy": "render_two_distinct_variants_then_recommend_variant_a_by_default",
        },
        "renderer_capabilities": {
            "output_intent_bounded_effects": "allowed_when_selected_intent_is_design_visual_or_editable_office",
            "approved_package_asset_insertion": "allowed_only_with_manifest_checksum_size_policy_license_and_slot_evidence",
            "approved_structured_native_chart_table_rendering": "allowed_only_with_approved_structured_data_package_evidence",
            "shared_ir_safe_area_native_chart_table_bounds": "allowed_when_shared_ir_is_explicitly_supplied_and_preflight_passes",
            "b54_style_token_guidance": "spacing_radius_elevation_typography_guidance_only",
        },
        "variant_native_chart_table_counts": {
            "variant_a": {"supported_candidate_count": 5, "blocked_candidate_count": 0},
            "variant_b": {"supported_candidate_count": 5, "blocked_candidate_count": 0},
        },
        "variant_b54_status": {
            "variant_a": {"status": "guidance_consumed", "font_materialization_enabled": False},
            "variant_b": {"status": "guidance_consumed", "font_materialization_enabled": False},
        },
        "asset_system_interpretation": {
            "b53b_palette_seeds": "candidate_reference_only",
            "promotion_ready": "proposal_eligible_not_active_approval",
            "b54_style_tokens": "metadata_recipe_guidance_not_raw_assets_or_full_style_pack",
            "font_handoff": "metadata_only_fallback_stacks_unless_approved_opaque_package_reference_exists",
            "insertable_assets": "approved_package_handoffs_with_manifest_checksum_import_evidence_only",
        },
        "blocked_behavior": {
            "shared_ir_layout_density_geometry_text_slot_asset_slot_consumption": True,
            "font_materialization_without_approved_opaque_package_evidence": True,
            "html_screenshots_inserted_into_pptx": True,
            "public_exposure_of_package_internals_or_private_ids": True,
        },
        "public_beta_reporting": {"capability_status_metadata_allowed": True},
    }
    if malicious:
        payload["renderer_capabilities"]["output_intent_bounded_effects"] = "sk-THISSHOULDNOTLEAK123456"
        payload["renderer_capabilities"]["approved_structured_native_chart_table_rendering"] = (
            "allowed only for structured_data_id=structured-data:SHOULDNOTLEAK"
        )
        payload["renderer_capabilities"]["approved_package_asset_insertion"] = (
            "allowed only from package_manifest_id=package-manifest:SHOULDNOTLEAK"
        )
        payload["asset_system_interpretation"]["insertable_assets"] = (
            "approved internal package reference package manifest SHOULDNOTLEAK"
        )
        payload["asset_system_interpretation"]["font_handoff"] = "raw package identifier SHOULDNOTLEAK"
        payload["package_manifest_id"] = "xoxb-THISSHOULDNOTLEAK123456"
        payload["structured_data_id"] = "AIzaTHISSHOULDNOTLEAK1234567890"
        payload["private_path"] = r"C:\private\package\manifest.json"
        payload["docs_url"] = "https://docs.google.com/document/d/SHOULDNOTLEAK"
        payload["blocked_behavior"]["sk-THISSHOULDNOTLEAK123456"] = True
        payload["blocked_behavior"]["package_manifest_id=package-manifest:SHOULDNOTLEAK"] = True
        payload["blocked_behavior"]["structured_data_id=structured-data:SHOULDNOTLEAK"] = True
    return write_json(path, payload)


def assert_auto_available(summary: dict[str, Any], *, malicious: bool = False) -> None:
    assert_true(summary.get("auto_capability_metadata_enabled") is True, "Auto metadata should be enabled")
    assert_true(summary.get("status") == "available", "Auto metadata should be available")
    assert_true(summary.get("metadata_only") is True, "Auto metadata must remain metadata-only")
    assert_true(summary.get("renderer_behavior") == "unchanged", "Auto metadata changed renderer behavior")
    assert_true(summary.get("auto_policy_redesign_enabled") is False, "Auto redesign should remain disabled")
    assert_true(summary.get("selected_output_intent") == "editable_office", "selected output intent was not exposed")
    assert_true(summary.get("two_variant_policy_status") == "current_two_variant_policy", "two-variant policy status changed")
    policy = summary.get("two_variant_policy")
    assert_true(isinstance(policy, dict) and policy.get("variant_count") == 2, "two-variant count missing")
    assert_true(policy.get("redesign_enabled") is False, "two-variant policy redesign changed")
    capabilities = summary.get("bounded_renderer_capabilities")
    assert_true(isinstance(capabilities, dict), "bounded capabilities missing")
    for key in CAPABILITY_KEYS:
        assert_true(key in capabilities, f"missing capability {key}")
    if malicious:
        assert_true(capabilities["output_intent_bounded_effects"] == "not_available", "token-shaped capability was not replaced")
        assert_true(
            capabilities["approved_structured_native_chart_table_rendering"] == "not_available",
            "structured-data marker inside capability was not replaced",
        )
        assert_true(
            capabilities["approved_package_asset_insertion"] == "not_available",
            "package manifest marker inside capability was not replaced",
        )
    counts = summary.get("native_chart_table_supported_candidate_counts")
    assert_true(counts.get("variant_a", {}).get("supported_candidate_count") == 5, "variant A native count missing")
    assert_true(counts.get("variant_b", {}).get("supported_candidate_count") == 5, "variant B native count missing")
    b54 = summary.get("b54_and_font_status")
    assert_true(b54.get("font_materialization") == "blocked_without_approved_opaque_package_evidence", "font block changed")
    blockers = set(summary.get("public_safe_blocker_categories") or [])
    assert_true(BLOCKER_KEYS <= blockers, "public-safe blocker categories missing")
    if malicious:
        assert_true("sensitive_blocker_category_redacted" in blockers, "sensitive blocker category was not redacted")
        interpretation = summary.get("asset_system_interpretation")
        assert_true(
            interpretation.get("insertable_assets") == "approved_package_handoffs_only",
            "package-internal asset interpretation was not replaced",
        )
        assert_true(
            interpretation.get("font_handoff") == "metadata_only_without_approved_opaque_package",
            "raw package font interpretation was not replaced",
        )


def assert_auto_unavailable(summary: dict[str, Any]) -> None:
    assert_true(summary.get("auto_capability_metadata_enabled") is False, "missing Auto metadata should be disabled")
    assert_true(summary.get("status") == "not_available", "missing Auto metadata should report not_available")
    assert_true(summary.get("renderer_behavior") == "unchanged", "missing Auto metadata changed renderer behavior")


def validate_setup(output_root: Path, fixture: Path | None, *, expected_available: bool, malicious: bool = False) -> dict[str, Any]:
    workspace = output_root / ("workspace-setup-available" if fixture else "workspace-setup-missing")
    command = [
        sys.executable,
        "scripts/ppt_setup.py",
        "--workspace",
        workspace.as_posix(),
        "--force",
        "--skip-version-check",
        "--output-intent",
        "editable_office",
    ]
    if fixture:
        command.extend(["--auto-capability-metadata", fixture.as_posix()])
    result = run(command, timeout=360)
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    summary_path = workspace / "outputs" / "reports" / "public_setup_summary.json"
    markdown_path = workspace / "outputs" / "reports" / "public_setup_summary.md"
    setup_report_path = workspace / "outputs" / "reports" / "ppt_setup_report.json"
    summary = load_json(summary_path)
    setup_report = load_json(setup_report_path)
    markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
    if expected_available:
        assert_auto_available(summary["auto_capability_metadata"], malicious=malicious)
        assert_auto_available(setup_report["auto_capability_metadata"], malicious=malicious)
        assert_true("Auto / Beta Capabilities" in markdown, "setup Markdown missing Auto section")
        assert_true("current_two_variant_policy" in markdown, "setup Markdown missing two-variant policy")
    else:
        assert_auto_unavailable(summary["auto_capability_metadata"])
        assert_auto_unavailable(setup_report["auto_capability_metadata"])
    return {"workspace": workspace.as_posix(), "summary": summary_path.as_posix(), "markdown": markdown_path.as_posix(), "setup_report": setup_report_path.as_posix()}


def validate_make(output_root: Path, fixture: Path | None, *, expected_available: bool, malicious: bool = False) -> dict[str, Any]:
    workspace = output_root / ("workspace-make-available" if fixture else "workspace-make-missing")
    project_id = "auto-capability-metadata-make"
    command = [
        sys.executable,
        "scripts/ppt_make.py",
        PROMPT,
        "--workspace",
        workspace.as_posix(),
        "--mode",
        "assistant",
        "--project-id",
        project_id,
        "--skip-version-check",
        "--output-intent",
        "editable_office",
    ]
    if fixture:
        command.extend(["--auto-capability-metadata", fixture.as_posix()])
    result = run(command, timeout=420)
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report_path = workspace / "outputs" / "projects" / project_id / "reports" / "ppt_make_report.json"
    report = load_json(report_path)
    assert_true(report.get("status") == "waiting_for_approval", "make should remain an Assistant checkpoint")
    if expected_available:
        assert_auto_available(report["auto_capability_metadata"], malicious=malicious)
    else:
        assert_auto_unavailable(report["auto_capability_metadata"])
    return {"workspace": workspace.as_posix(), "report": report_path.as_posix()}


def assert_public_safe(output_root: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    for path in [*output_root.rglob("*.json"), *output_root.rglob("*.md")]:
        path_text = path.as_posix()
        if "/fixtures/" in path_text or "/.ppt-agent/" in path_text:
            continue
        if "reports" not in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in sorted(set(public_report_issues(text))):
            issues.append({"path": path.as_posix(), "issue": name})
    assert_true(not issues, f"public/private scan failed: {issues[:5]}")
    return {"scanned_root": output_root.as_posix(), "issues": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public Auto capability metadata exposure.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    before_reports = repo_report_snapshot()
    fixture = write_auto_fixture(output_root / "fixtures" / "auto_capability_metadata.json")
    malicious_fixture = write_auto_fixture(output_root / "fixtures" / "malicious_auto_capability_metadata.json", malicious=True)
    result = {
        "status": "pass",
        "missing_metadata": {
            "setup": validate_setup(output_root / "missing", None, expected_available=False),
            "make": validate_make(output_root / "missing", None, expected_available=False),
        },
        "supplied_metadata": {
            "setup": validate_setup(output_root / "supplied", fixture, expected_available=True),
            "make": validate_make(output_root / "supplied", fixture, expected_available=True),
        },
        "sensitive_metadata_redacted": {
            "setup": validate_setup(output_root / "sensitive", malicious_fixture, expected_available=True, malicious=True),
            "make": validate_make(output_root / "sensitive", malicious_fixture, expected_available=True, malicious=True),
        },
        "public_private_scan": assert_public_safe(output_root),
    }
    changes = repo_report_changes(before_reports)
    assert_true(not changes, f"repo checkout outputs/reports changed during validation: {changes}")
    result["repo_report_leak_scan"] = {"repo_report_root": REPO_REPORT_ROOT.as_posix(), "changed_files": []}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
