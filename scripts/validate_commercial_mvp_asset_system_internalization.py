from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "web" / "commercial-mvp-html-workbench" / "workbench-data.json"
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "commercial_mvp_asset_system_internalization.json"

PRIVATE_MARKERS = (
    "approval_log",
    "assetization_worklog",
    "package_manifest_id",
    "structured_data_id",
    "raw_reference",
    "workspace_path",
)
PATH_PATTERN = re.compile(r"[A-Za-z]:\\|/(?:Users|home)/", re.IGNORECASE)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate approved-result-only asset-system internalization posture.")
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args(argv)
    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    design_package = data.get("design_package", {})
    asset_system = data.get("asset_system_consumption", {})
    refs = {
        "design_package_id": design_package.get("design_package_id"),
        "source_kind": design_package.get("source_kind"),
        "asset_system_package_ref": design_package.get("asset_system_package_ref"),
        "safe_manifest_ids_only": True,
        "theme_id": data.get("theme_tokens", {}).get("theme_id"),
        "layout_recipe_ids": [item.get("layout_recipe_id") for item in data.get("layout_recipes", [])],
        "component_recipe_ids": [item.get("component_recipe_id") for item in data.get("component_recipes", [])],
        "font_metadata_only": data.get("local_asset_connection_ux", {}).get("font_connection", {}).get("stores_font_metadata") is True,
        "raw_assetization_workflow_imported": False,
    }
    encoded_refs = json.dumps(
        {
            "design_package": design_package,
            "theme_tokens": data.get("theme_tokens", {}),
            "layout_recipes": data.get("layout_recipes", []),
            "component_recipes": data.get("component_recipes", []),
            "local_asset_connection_ux": data.get("local_asset_connection_ux", {}),
        },
        ensure_ascii=False,
    )
    for marker in PRIVATE_MARKERS:
        if marker in encoded_refs:
            errors.append(f"asset-system internalization exposes private marker: {marker}")
    if PATH_PATTERN.search(encoded_refs):
        errors.append("asset-system internalization exposes local path pattern")
    if design_package.get("source_kind") not in {"tracked_doc", "server_manifest", "approved_asset_system", "imported_approved_asset_result"}:
        errors.append("unsupported design package source_kind")
    if asset_system.get("approved_package_consumed") or asset_system.get("approved_design_package_consumed"):
        if asset_system.get("render_use_evidence") is not True:
            errors.append("approved asset-system consumption claim lacks render-use evidence")
    elif asset_system.get("ui_claim") != "asset-system-ready":
        errors.append("asset-system UI claim must remain asset-system-ready without approved package evidence")
    if data.get("local_asset_connection_ux", {}).get("image_connection", {}).get("stores_raw_image_path") is not False:
        errors.append("image connection must not store raw image path")

    payload = {
        "schema_version": "commercial_mvp_asset_system_internalization.v1",
        "status": "valid" if not errors else "invalid",
        "refs": refs,
        "asset_system_consumption": {
            "status": asset_system.get("status"),
            "ui_claim": asset_system.get("ui_claim"),
            "approved_package_consumed": asset_system.get("approved_package_consumed") is True,
            "approved_design_package_consumed": asset_system.get("approved_design_package_consumed") is True,
            "render_use_evidence": asset_system.get("render_use_evidence") is True,
        },
        "allowed_internalization": [
            "safe_manifest_id",
            "theme_token",
            "layout_recipe",
            "component_recipe",
            "font_icon_metadata",
            "license_policy_metadata"
        ],
        "blocked_internalization": [
            "raw_reference_assetization_workflow",
            "raw_workspace_path",
            "package_internals",
            "approval_logs"
        ],
        "errors": errors,
    }
    write_json(report, payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"commercial_mvp_asset_system_internalization=valid report={report.relative_to(BASE_DIR).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
