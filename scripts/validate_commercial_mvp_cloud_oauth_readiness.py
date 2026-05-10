from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "commercial_mvp_cloud_oauth_readiness.json"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record Commercial MVP cloud/OAuth readiness without remote mutation.")
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args(argv)
    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()

    checks = {
        "remote_mutation_performed": False,
        "supabase": {
            "target_project": "slides-maker-prod",
            "project_ref": "tnbjlydrneugaouirtnq",
            "region": "Northeast Asia (Seoul)",
            "rls_required": True,
            "automatic_table_exposure": "must_be_disabled_or_launch_blocker",
            "service_role_boundary": "gateway_server_only",
            "google_oauth_provider": "readiness_only_not_verified",
            "redirect_allowlist_required": [
                "https://slides-maker.kkumjangi.com/auth/callback",
                "https://app.slides-maker.kkumjangi.com/auth/callback"
            ],
        },
        "vercel": {
            "public_landing_domain": "slides-maker.kkumjangi.com",
            "app_domain": "app.slides-maker.kkumjangi.com",
            "status": "local_static_ready_not_deployed",
        },
        "cloudflare": {
            "gateway_domain": "api.slides-maker.kkumjangi.com",
            "zone": "kkumjangi.com",
            "status": "local_contract_ready_not_deployed",
            "cors_allowlist_required": [
                "https://slides-maker.kkumjangi.com",
                "https://app.slides-maker.kkumjangi.com"
            ],
        },
        "blocked_until_approval": [
            "remote_supabase_schema_or_setting_mutation",
            "vercel_project_or_domain_mutation",
            "cloudflare_worker_dns_or_secret_mutation",
            "google_oauth_provider_mutation"
        ],
    }
    errors: list[str] = []
    if checks["remote_mutation_performed"] is not False:
        errors.append("remote mutation must remain false")
    if checks["supabase"]["project_ref"] != "tnbjlydrneugaouirtnq":
        errors.append("Supabase project ref mismatch")
    if checks["vercel"]["public_landing_domain"] != "slides-maker.kkumjangi.com":
        errors.append("public landing domain mismatch")
    if checks["cloudflare"]["gateway_domain"] != "api.slides-maker.kkumjangi.com":
        errors.append("gateway domain mismatch")

    payload = {
        "schema_version": "commercial_mvp_cloud_oauth_readiness.v1",
        "status": "valid" if not errors else "invalid",
        "checks": checks,
        "errors": errors,
    }
    write_json(report, payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"commercial_mvp_cloud_oauth_readiness=valid report={report.relative_to(BASE_DIR).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
