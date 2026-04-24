from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.reference_pipeline import ASSET_CATALOG_PATH, ASSET_ROOTS_PATH, base_relative, load_json, write_json

KIND_BY_SUFFIX = {
    ".svg": "icon_svg",
    ".png": "icon_png",
    ".jpg": "illustration",
    ".jpeg": "illustration",
    ".webp": "illustration",
    ".ttf": "font",
    ".otf": "font",
    ".woff": "font",
    ".woff2": "font",
}

THEME_PATHS = [
    BASE_DIR / "config" / "pptx_theme.example.json",
    BASE_DIR / "config" / "pptx_theme.neutral_modern.json",
]
CHART_PRESETS = [
    {
        "asset_id": "chart_preset.simple_bar_chart",
        "source_path": "system/pptx_system.py",
        "preset_name": "simple_bar_chart",
        "recommended_use": "basic bar-chart slot rendering",
        "style_tags": ["chart", "bar", "data_visualization"],
    }
]
IMAGE_POLICIES = [
    {
        "asset_id": "image_policy.user_supplied_or_generated",
        "source_path": "config/ppt_asset_roots.json",
        "policy_name": "user_supplied_or_generated_image",
        "recommended_use": "image slot sourcing policy for user-provided or future generated visuals",
        "style_tags": ["image", "slot_policy", "user_supplied", "generated_asset_ready"],
    }
]
EXTERNAL_RECOMMENDED_SETS = {
    "default-ui-icons",
    "dashboard-report-icons",
    "technical-security-cloud-icons",
    "blog-webpage-visuals",
    "korean-ui-fonts",
}
PUBLIC_ASSET_CONTRIBUTION_GATE = "https://github.com/Kdreammaker/ai-asset-contribution-gate"
EXTERNAL_ASSET_WORKSPACE_ALIAS = "external_asset_registry"


def safe_id(value: str) -> str:
    result = "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
    while "__" in result:
        result = result.replace("__", "_")
    return result or "asset"


def classify(path: Path, root_id: str) -> str:
    kind = KIND_BY_SUFFIX.get(path.suffix.casefold(), "other")
    if root_id == "fonts":
        return "font"
    if root_id == "icons" and kind == "illustration":
        return "icon_png"
    return kind


def asset_class_for_kind(kind: str) -> str:
    if kind.startswith("icon"):
        return "icon"
    if kind == "font":
        return "typography"
    if kind == "illustration":
        return "image"
    return "image"


def base_asset_fields(
    *,
    asset_id: str,
    asset_class: str,
    source_type: str,
    source_path: str | None,
    license_value: str,
    license_action: str = "none",
    risk_level: str = "unknown",
    production_eligible: bool = True,
    style_tags: list[str] | None = None,
    recommended_use: str = "ppt_support_asset",
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_class": asset_class,
        "source_type": source_type,
        "source_path": source_path,
        "license": license_value,
        "license_action": license_action,
        "risk_level": risk_level,
        "production_eligible": production_eligible,
        "allowed_for_ppt": production_eligible,
        "style_tags": style_tags or [],
        "recommended_use": recommended_use,
    }


def build_asset(root: dict[str, Any], path: Path) -> dict[str, Any]:
    root_id = str(root["root_id"])
    kind = classify(path, root_id)
    tags = [root_id]
    if kind.startswith("icon"):
        tags.append("icon")
    if kind == "font":
        tags.append("font")
    asset = {
        **base_asset_fields(
            asset_id=f"{root_id}.{safe_id(path.stem)}",
            asset_class=asset_class_for_kind(kind),
            source_type="local_file",
            source_path=base_relative(path),
            license_value=root.get("default_license", "unknown"),
            risk_level="unknown",
            production_eligible=bool(root.get("allowed_for_ppt", True)),
            style_tags=tags,
        ),
        # `kind` is retained as the compatibility field used by older validators and callers.
        "kind": kind,
        "cjk_support": None if kind != "font" else any(token in path.name.casefold() for token in ("noto", "cjk", "kr", "korea", "malgun")),
        "installed_locally": None if kind != "font" else False,
    }
    return asset


def build_theme_assets() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for theme_path in THEME_PATHS:
        if not theme_path.exists():
            continue
        theme = json.loads(theme_path.read_text(encoding="utf-8"))
        theme_name = safe_id(str(theme.get("name") or theme_path.stem))
        source_path = base_relative(theme_path)
        colors = theme.get("colors", {})
        sizes = theme.get("sizes", {})
        font_family = str(theme.get("font_family") or "unknown")
        assets.append(
            {
                **base_asset_fields(
                    asset_id=f"theme.{theme_name}",
                    asset_class="theme",
                    source_type="local_config",
                    source_path=source_path,
                    license_value="internal-config",
                    risk_level="low",
                    style_tags=["theme", theme_name],
                    recommended_use="ppt theme config",
                ),
                "kind": "theme",
                "theme_name": theme.get("name"),
                "font_family": font_family,
                "color_roles": sorted(colors),
                "font_size_roles": sorted(sizes),
            }
        )
        assets.append(
            {
                **base_asset_fields(
                    asset_id=f"palette.{theme_name}",
                    asset_class="palette",
                    source_type="local_config",
                    source_path=source_path,
                    license_value="internal-config",
                    risk_level="low",
                    style_tags=["palette", theme_name],
                    recommended_use="theme color palette",
                ),
                "kind": "palette",
                "theme_name": theme.get("name"),
                "colors": colors,
            }
        )
        assets.append(
            {
                **base_asset_fields(
                    asset_id=f"typography.{theme_name}.{safe_id(font_family)}",
                    asset_class="typography",
                    source_type="local_config",
                    source_path=source_path,
                    license_value="system-font-or-theme-config",
                    risk_level="low",
                    style_tags=["typography", "korean", safe_id(font_family)],
                    recommended_use="theme typography defaults",
                ),
                "kind": "font",
                "font_family": font_family,
                "cjk_support": font_family in {"Malgun Gothic", "맑은 고딕"} or "gothic" in font_family.casefold(),
                "installed_locally": None,
                "font_size_roles": sizes,
            }
        )
    return assets


def build_chart_preset_assets() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for preset in CHART_PRESETS:
        source_path = str(preset["source_path"])
        assets.append(
            {
                **base_asset_fields(
                    asset_id=str(preset["asset_id"]),
                    asset_class="chart_preset",
                    source_type="local_code",
                    source_path=source_path,
                    license_value="internal-code",
                    risk_level="low",
                    style_tags=list(preset["style_tags"]),
                    recommended_use=str(preset["recommended_use"]),
                ),
                "kind": "chart_preset",
                "preset_name": preset["preset_name"],
            }
        )
    return assets


def build_image_policy_assets() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for policy in IMAGE_POLICIES:
        assets.append(
            {
                **base_asset_fields(
                    asset_id=str(policy["asset_id"]),
                    asset_class="image",
                    source_type="local_config",
                    source_path=str(policy["source_path"]),
                    license_value="user-provided-or-generated-policy",
                    risk_level="low",
                    style_tags=list(policy["style_tags"]),
                    recommended_use=str(policy["recommended_use"]),
                ),
                "kind": "illustration",
                "policy_name": policy["policy_name"],
                "policy_notes": {
                    "binary_asset_included": False,
                    "requires_runtime_materialization": True,
                    "do_not_copy_external_assets": True,
                },
            }
        )
    return assets


def default_external_workspace() -> Path | None:
    env_value = os.environ.get("PPT_AGENT_EXTERNAL_ASSET_WORKSPACE")
    if env_value:
        candidate = Path(env_value).expanduser().resolve()
        return candidate if candidate.exists() else None
    legacy_sibling_name = "assets " + "achivement for work"
    sibling = BASE_DIR.parent / legacy_sibling_name
    return sibling if sibling.exists() else None


def external_asset_class(asset_type: str) -> str:
    if asset_type == "font":
        return "typography"
    if asset_type == "icon":
        return "icon"
    if asset_type in {"illustration", "image"}:
        return "image"
    return "image"


def build_external_registry_references(external_workspace: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if external_workspace is None:
        return [], {
            "enabled": False,
            "reason": "external asset workspace not found or not configured",
            "policy": "registry-first; no external mutation",
        }
    recommended_path = external_workspace / "downloaded-assets" / "registry" / "recommended-assets.json"
    if not recommended_path.exists():
        return [], {
            "enabled": False,
            "reason": "recommended-assets.json not found",
            "policy": "registry-first; no external mutation",
        }

    payload = json.loads(recommended_path.read_text(encoding="utf-8-sig"))
    assets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for asset_set in payload.get("sets", []):
        set_id = str(asset_set.get("id") or "")
        if set_id not in EXTERNAL_RECOMMENDED_SETS:
            continue
        for item in asset_set.get("items", []):
            if item.get("asset_uid") is None:
                continue
            if item.get("status", "active") != "active":
                continue
            asset_type = str(item.get("asset_type") or "unknown")
            source_name = str(item.get("source_name") or "unknown")
            asset_name = str(item.get("asset_name") or item.get("role") or item.get("asset_uid"))
            asset_id = f"external.{safe_id(set_id)}.{safe_id(source_name)}.{safe_id(asset_name)}"
            suffix = 2
            base_id = asset_id
            while asset_id in seen:
                asset_id = f"{base_id}_{suffix}"
                suffix += 1
            seen.add(asset_id)
            risk_level = str(item.get("risk_level") or "unknown")
            license_action = str(item.get("license_action") or "none")
            brand_guidelines_required = bool(item.get("brand_guidelines_required", False))
            production_eligible = risk_level != "restricted" and not brand_guidelines_required
            assets.append(
                {
                    **base_asset_fields(
                        asset_id=asset_id,
                        asset_class=external_asset_class(asset_type),
                        source_type="external_registry_reference",
                        source_path=None,
                        license_value=str(item.get("license_class") or "unknown"),
                        license_action=license_action,
                        risk_level=risk_level,
                        production_eligible=production_eligible,
                        style_tags=[
                            "external_registry",
                            safe_id(set_id),
                            safe_id(asset_type),
                            safe_id(source_name),
                        ],
                        recommended_use="external registry reference for future PPT materialization",
                    ),
                    "kind": "font" if asset_type == "font" else ("icon_svg" if asset_type == "icon" else "illustration"),
                    "external_asset_uid": item.get("asset_uid"),
                    "external_set_id": set_id,
                    "external_source_name": source_name,
                    "external_asset_name": asset_name,
                    "external_relative_path": item.get("relative_path"),
                    "policy_notes": {
                        "status": item.get("status", "active"),
                        "brand_guidelines_required": brand_guidelines_required,
                        "attribution_required": bool(item.get("attribution_required", False)),
                        "notes_for_ai": item.get("notes_for_ai"),
                    },
                }
            )
    return assets, {
        "enabled": True,
        "workspace_ref": EXTERNAL_ASSET_WORKSPACE_ALIAS,
        "source": "downloaded-assets/registry/recommended-assets.json",
        "public_contribution_gate": PUBLIC_ASSET_CONTRIBUTION_GATE,
        "private_reference_analysis_required": True,
        "records": len(assets),
        "policy": "registry-first; active recommended records only; no external mutation",
    }


def dedupe_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for asset in assets:
        asset_id = str(asset["asset_id"])
        suffix = 2
        base_id = asset_id
        while asset_id in seen:
            asset_id = f"{base_id}_{suffix}"
            suffix += 1
        asset["asset_id"] = asset_id
        seen.add(asset_id)
        result.append(asset)
    return sorted(result, key=lambda item: item["asset_id"])


def build_catalog(external_workspace: Path | None = None) -> dict[str, Any]:
    roots_config = load_json(ASSET_ROOTS_PATH)
    assets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots_config.get("roots", []):
        root_path = BASE_DIR / str(root.get("path", ""))
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob("*")):
            if not path.is_file() or path.name.upper() in {"README.md"}:
                continue
            if path.suffix.casefold() not in KIND_BY_SUFFIX:
                continue
            asset = build_asset(root, path)
            suffix = 2
            base_id = asset["asset_id"]
            while asset["asset_id"] in seen:
                asset["asset_id"] = f"{base_id}_{suffix}"
                suffix += 1
            seen.add(asset["asset_id"])
            assets.append(asset)
    assets.extend(build_theme_assets())
    assets.extend(build_chart_preset_assets())
    assets.extend(build_image_policy_assets())
    external_assets, external_summary = build_external_registry_references(external_workspace)
    assets.extend(external_assets)
    assets = dedupe_assets(assets)
    return {
        "schema_version": "1.1",
        "generated_from": "config/ppt_asset_roots.json",
        "generated_from_details": {
            "local_roots": "config/ppt_asset_roots.json",
            "theme_configs": [base_relative(path) for path in THEME_PATHS if path.exists()],
            "chart_presets": [item["asset_id"] for item in CHART_PRESETS],
            "image_policies": [item["asset_id"] for item in IMAGE_POLICIES],
            "external_registry": external_summary,
        },
        "selection_policy": {
            "raw_folders_are_not_source_of_truth": True,
            "external_assets_are_registry_references_only": True,
            "do_not_hard_code_external_absolute_paths": True,
            "brand_assets_require_explicit_request": True,
            "public_asset_contribution_gate": PUBLIC_ASSET_CONTRIBUTION_GATE,
            "public_gate_usage": "candidate intake and safety review only",
            "private_reference_analysis_required": True,
            "private_assetization_required": True,
            "private_registry_activation_required": True,
            "workspace_asset_transfer": {
                "allowed_by_default": False,
                "requires_manifest": True,
                "requires_explicit_approval": True,
                "public_exposure_allowed": False,
                "forbidden_public_payloads": [
                    "private references",
                    "binary assets",
                    "registry exports",
                    "local absolute paths",
                    "Drive linkage",
                    "work logs",
                ],
            },
        },
        "assets": assets,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PPT asset catalog.")
    parser.add_argument("--output", default=str(ASSET_CATALOG_PATH))
    parser.add_argument(
        "--external-asset-workspace",
        default=None,
        help="Optional path to the governed external asset workspace. Reads registry metadata only.",
    )
    args = parser.parse_args(argv)
    output = Path(args.output)
    if not output.is_absolute():
        output = (BASE_DIR / output).resolve()
    external_workspace = Path(args.external_asset_workspace).resolve() if args.external_asset_workspace else default_external_workspace()
    catalog = build_catalog(external_workspace=external_workspace)
    write_json(output, catalog)
    print(f"asset_count={len(catalog['assets'])}")
    print(base_relative(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
