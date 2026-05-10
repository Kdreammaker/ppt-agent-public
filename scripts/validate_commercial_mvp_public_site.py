from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.commercial_mvp_web_site import (
    ADMIN_EVIDENCE_MARKERS,
    FORBIDDEN_PUBLIC_SITE_MARKERS,
    PUBLIC_SITE_SCHEMA_VERSION,
    build_public_site_model,
    validate_public_site_model,
)


SITE_DIR = BASE_DIR / "web" / "commercial-mvp-site"
DATA_PATH = SITE_DIR / "public-site-data.json"
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "commercial_mvp_public_site_validation.json"
REQUIRED_FILES = (
    "index.html",
    "account.html",
    "styles.css",
    "site.js",
    "public-site-data.json",
    "package.json",
    "vercel.json",
    "locales/en.json",
    "locales/ko.json",
)


def expect(condition: bool, label: str, errors: list[str]) -> None:
    if not condition:
        errors.append(label)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        errors.append(f"{path.as_posix()} cannot be read as UTF-8 JSON: {exc}")
        return {}


def flatten_keys(payload: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in payload.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(flatten_keys(value, full))
        else:
            keys.add(full)
    return keys


def validate_files(errors: list[str]) -> dict[str, int]:
    for relative in REQUIRED_FILES:
        expect((SITE_DIR / relative).exists(), f"missing public site file: {relative}", errors)

    texts = {relative: read_text(SITE_DIR / relative) for relative in REQUIRED_FILES if relative.endswith((".html", ".css", ".js", ".json"))}
    combined = "\n".join(texts.values())

    expect("A.DreamMaker" in texts.get("index.html", ""), "public landing must show primary brand", errors)
    expect("ADOTDREAMMAKER" in texts.get("index.html", ""), "public landing must include full brand context", errors)
    expect("host AI" in texts.get("index.html", "") or "HOST-AI" in texts.get("index.html", ""), "public landing must state host-AI extension positioning", errors)
    expect("Google로 시작하기" in texts.get("index.html", ""), "public landing must expose Korean Google signup CTA", errors)
    expect("HTML 워크벤치 보기" in texts.get("index.html", ""), "public landing must link to workbench preview", errors)
    expect("PDF/PPTX" in texts.get("index.html", ""), "public landing must explain PDF/PPTX handoff", errors)
    expect("PRIVACY / SECURITY" in texts.get("index.html", ""), "public landing must include privacy/security section", errors)
    expect("FAQ" in texts.get("index.html", ""), "public landing must include FAQ", errors)
    expect("payment not attached" in texts.get("account.html", "").lower(), "account entry must state payment not attached", errors)
    expect("operator-dashboard-data.json" not in combined, "public site must not load admin dashboard data", errors)
    expect("route-backed" not in combined.lower(), "public site must not expose route-backed admin evidence", errors)
    expect("admin_adjust_credit" not in combined, "public site must not expose admin credit route evidence", errors)
    expect("#171717" in texts.get("styles.css", "") and "#0f0f0f" in texts.get("styles.css", ""), "public site must use dark surface tokens", errors)
    expect("#F4D35E" in texts.get("styles.css", "") and "#FFD12B" in texts.get("styles.css", ""), "public site must use yellow brand tokens", errors)
    expect("linear-gradient" not in texts.get("styles.css", ""), "public site must avoid gradient wash", errors)
    expect("box-shadow" not in texts.get("styles.css", ""), "public site must avoid heavy shadows", errors)

    for marker in (*FORBIDDEN_PUBLIC_SITE_MARKERS, *ADMIN_EVIDENCE_MARKERS):
        expect(marker not in combined, f"public site files must not contain forbidden marker: {marker}", errors)

    return {
        "files_checked": len(REQUIRED_FILES),
        "index_bytes": len(texts.get("index.html", "")),
        "account_bytes": len(texts.get("account.html", "")),
        "css_bytes": len(texts.get("styles.css", "")),
        "js_bytes": len(texts.get("site.js", "")),
    }


def validate_locale_parity(errors: list[str]) -> dict[str, Any]:
    en = read_json(SITE_DIR / "locales" / "en.json", errors)
    ko = read_json(SITE_DIR / "locales" / "ko.json", errors)
    expect(en.get("locale") == "en", "public site en locale mismatch", errors)
    expect(ko.get("locale") == "ko", "public site ko locale mismatch", errors)
    expect(flatten_keys(en) == flatten_keys(ko), "public site locale key parity mismatch", errors)
    return {
        "default_locale": "en",
        "locales": 2,
        "locale_keys": len(flatten_keys(en)),
    }


def validate_data(errors: list[str]) -> dict[str, Any]:
    expected = build_public_site_model()
    errors.extend(validate_public_site_model(expected))
    actual = read_json(DATA_PATH, errors)
    expect(actual == expected, "tracked public site data must match current model", errors)
    expect(actual.get("schema_version") == PUBLIC_SITE_SCHEMA_VERSION, "public site data schema mismatch", errors)
    boundary = actual.get("product_boundary", {})
    stack = actual.get("commercial_stack_direction", {})
    account = actual.get("account_entry_placeholder", {})
    plans = actual.get("plan_teaser", [])
    expect(set(boundary.get("modes", [])) == {"assistant", "auto"}, "public site data must keep Assistant/Auto only", errors)
    expect(boundary.get("default_mode") == "assistant", "public site data must keep Assistant default", errors)
    expect(stack.get("payment") == "not_attached", "public site data must keep payment not attached", errors)
    expect(stack.get("google_oauth") == "target_provider_not_verified", "public site data must keep Google OAuth honest", errors)
    expect(stack.get("vercel_web") == "local_static_skeleton_not_deployed", "public site must remain not deployed", errors)
    landing = actual.get("public_landing_content", {})
    for key in (
        "korean_first",
        "seo_metadata_present",
        "google_signup_cta_present",
        "assistant_auto_explained",
        "html_workbench_explained",
        "pdf_pptx_handoff_explained",
        "privacy_security_explained",
        "faq_present",
    ):
        expect(landing.get(key) is True, f"public landing content missing {key}", errors)
    expect(account.get("login_implemented") is False, "account entry must not implement login", errors)
    expect(account.get("payment_attached") is False, "account entry must not attach payment", errors)
    expect(account.get("hosted_dashboard_sync_enabled") is False, "account entry must not sync hosted dashboard", errors)
    expect({plan.get("tier") for plan in plans} == {"free", "paid"}, "public plan teaser must use Free plus Paid", errors)
    free_plan = next((plan for plan in plans if plan.get("tier") == "free"), {})
    paid_plan = next((plan for plan in plans if plan.get("tier") == "paid"), {})
    expect(free_plan.get("credit_policy") == "limited_credits_referral_replenishable", "Free plan must use limited/referral credits", errors)
    expect(free_plan.get("editor_access") == "preview_only", "Free plan editor must be preview_only", errors)
    expect(paid_plan.get("credit_policy") == "no_visible_per_edit_credit_for_normal_workflows", "Paid plan must avoid visible per-edit credits", errors)
    expect(paid_plan.get("editor_access") == "practical_editor", "Paid plan must include practical editor", errors)
    expect(paid_plan.get("viewer_sharing") == "watermark_free", "Paid plan must remove viewer watermark", errors)
    encoded = json.dumps(actual, ensure_ascii=False, sort_keys=True)
    for marker in (*FORBIDDEN_PUBLIC_SITE_MARKERS, *ADMIN_EVIDENCE_MARKERS):
        expect(marker not in encoded, f"public site data must not contain forbidden marker: {marker}", errors)
    return {
        "schema_version": actual.get("schema_version"),
        "plans": len(plans),
        "plan_tiers": [plan.get("tier") for plan in plans],
        "modes": boundary.get("modes", []),
        "payment": stack.get("payment"),
        "vercel_web": stack.get("vercel_web"),
        "account_entry_status": actual.get("surface_separation", {}).get("account_entry", {}).get("status"),
    }


def write_report(report: Path, errors: list[str], file_summary: dict[str, int], locale_summary: dict[str, Any], data_summary: dict[str, Any]) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "commercial_mvp_public_site_validation.v1",
        "status": "valid" if not errors else "invalid",
        "file_summary": file_summary,
        "locale_summary": locale_summary,
        "data_summary": data_summary,
        "public_landing_implemented": True,
        "account_entry_placeholder_implemented": True,
        "admin_operator_surface_separate": True,
        "admin_route_evidence_exposed_to_public": False,
        "production_deploy_enabled": False,
        "cloudflare_deploy_enabled": False,
        "supabase_remote_apply_enabled": False,
        "payment_enabled": False,
        "hosted_generation_enabled": False,
        "backend_ai_authoring_enabled": False,
        "renderer_visual_consumption_changed": False,
        "central_run_status_sync_enabled": False,
        "errors": errors,
    }
    report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Commercial MVP public landing and account entry surface.")
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args(argv)
    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()

    errors: list[str] = []
    file_summary = validate_files(errors)
    locale_summary = validate_locale_parity(errors)
    data_summary = validate_data(errors)
    write_report(report, errors, file_summary, locale_summary, data_summary)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "commercial_mvp_public_site=valid "
        f"plans={data_summary['plans']} account_entry={data_summary['account_entry_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
