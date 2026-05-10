from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from import_commercial_mvp_reference_designs import FAMILIES, family_evidence_present, recipe_for_family


BASE_DIR = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = BASE_DIR / "web" / "commercial-mvp-html-workbench"
DATA_PATH = WORKBENCH_DIR / "workbench-data.json"
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "commercial_mvp_workbench_handoff_envelope.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def text_role_summary(data: dict[str, Any]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for slide in data["deck"]["slides"]:
        for obj in slide.get("objects", []):
            if obj.get("type") != "text":
                continue
            role = obj.get("textRole") or infer_role(obj)
            summary[role] = summary.get(role, 0) + 1
    return summary


def infer_role(obj: dict[str, Any]) -> str:
    if "page" in str(obj.get("id", "")):
        return "Caption"
    size = int(obj.get("fontSize") or 24)
    if size >= 60:
        return "Title"
    if size >= 44:
        return "H1"
    if size >= 36:
        return "H2"
    if size >= 29:
        return "H3"
    return "Body"


def transform_summary(data: dict[str, Any]) -> list[dict[str, Any]]:
    transforms: list[dict[str, Any]] = []
    for slide in data["deck"]["slides"]:
        for obj in slide.get("objects", []):
            if obj.get("type") not in {"shape", "image"}:
                continue
            item = {
                "slide_id": slide["id"],
                "object_id": obj["id"],
                "object_type": obj["type"],
                "rotation": obj.get("rotation", 0),
                "flipX": bool(obj.get("flipX", False)),
                "flipY": bool(obj.get("flipY", False)),
                "radius": obj.get("radius"),
            }
            if obj.get("type") == "image":
                item["safeRef"] = obj.get("safeRef")
            transforms.append(item)
    return transforms


def recipe_is_content_free(recipe: dict[str, Any]) -> bool:
    content_free_preview = recipe.get("content_free_preview", {})
    synthetic_preview = recipe.get("synthetic_placeholder_preview", {})
    return (
        content_free_preview.get("placeholder_labels_only") is True
        or synthetic_preview.get("placeholder_labels_only") is True
    )


def reference_design_summary(data: dict[str, Any]) -> dict[str, Any]:
    library = data.get("reference_design_library", {})
    recipes = library.get("recipes", [])
    storage = library.get("server_storage_policy", {})
    return {
        "library_id": library.get("library_id"),
        "recipe_count": len(recipes),
        "extraction_source": library.get("extraction_source"),
        "content_free_only": bool(recipes) and all(recipe_is_content_free(recipe) for recipe in recipes),
        "content_free_schema_support": {
            "content_free_preview_placeholder_labels_only": True,
            "synthetic_placeholder_preview_placeholder_labels_only": True,
        },
        "server_stores_original_files": storage.get("stores_original_files") is True,
        "server_stores_source_text": storage.get("stores_source_text") is True,
        "server_stores_slide_images": storage.get("stores_slide_images") is True,
    }


def style_memory_summary(data: dict[str, Any]) -> dict[str, Any]:
    profiles = data.get("style_memory_profiles", [])
    if not profiles:
        return {"profile_count": 0, "visible": False, "controls": []}
    profile = profiles[0]
    return {
        "profile_id": profile.get("profile_id"),
        "profile_count": len(profiles),
        "visible": profile.get("visibility") == "user_visible",
        "controls": profile.get("user_controls", []),
        "separate_from_undo_redo": profile.get("separate_from_undo_redo") is True,
        "separate_from_ai_revision_memory": profile.get("separate_from_ai_revision_memory") is True,
        "public_handoff_summary": profile.get("public_handoff_summary", {}),
    }


def published_view_summary(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "view_id": view.get("view_id"),
            "deck_version_id": view.get("deck_version_id"),
            "route": view.get("route"),
            "plan": view.get("plan"),
            "read_only": view.get("read_only") is True,
            "watermark": view.get("watermark"),
        }
        for view in data.get("published_views", [])
    ]


def referral_summary(data: dict[str, Any]) -> dict[str, Any]:
    referral = data.get("referral_entitlement", {})
    return {
        "public_plans": referral.get("plan_model", {}).get("public_plans", []),
        "paid_visible_per_edit_credit": referral.get("plan_model", {}).get("paid_visible_per_edit_credit") is True,
        "raw_signup_reward": referral.get("referral_code", {}).get("raw_signup_reward") is True,
        "activation_event_count": len(referral.get("activation_events", [])),
        "free_credit_ledger_count": len(referral.get("free_credit_ledger", [])),
        "paid_fair_use_ref": referral.get("paid_fair_use_entitlement", {}).get("entitlement_ref"),
    }


def safe_asset_design_refs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "design_package_id": data.get("design_package", {}).get("design_package_id"),
        "theme_id": data.get("theme_tokens", {}).get("theme_id"),
        "master_style_id": (data.get("master_styles") or [{}])[0].get("master_style_id"),
        "layout_recipe_ids": [item.get("layout_recipe_id") for item in data.get("layout_recipes", [])],
        "component_recipe_ids": [item.get("component_recipe_id") for item in data.get("component_recipes", [])],
        "reference_recipe_ids": [item.get("recipe_id") for item in data.get("reference_design_library", {}).get("recipes", [])],
    }


def create_handoff(data: dict[str, Any], target: str, mode: str) -> dict[str, Any]:
    if mode not in {"assistant", "auto"}:
        raise ValueError("mode must be assistant or auto")
    if target not in {"pdf", "pptx"}:
        raise ValueError("target must be pdf or pptx")
    return {
        "schema_version": "commercial_mvp_workbench_handoff_cli.v1",
        "status": "handoff_ready",
        "envelope": {
            "envelope_version": "commercial_mvp_host_ai_export_handoff.v1",
            "target_export_kind": target,
            "safe_project_label": "A.DreamMaker PPT Maker",
            "safe_deck_label": data["deck"]["safe_label"],
            "scope": "all_slides",
            "mode": mode,
            "design_guide_version": data["design_guide_package"]["version"],
            "design_package_ref": {
                "design_package_id": data["design_package"]["design_package_id"],
                "manifest_hash": data["design_package"]["manifest_hash"],
                "source_kind": data["design_package"]["source_kind"],
                "theme_id": data["theme_tokens"]["theme_id"],
                "master_style_id": data["master_styles"][0]["master_style_id"],
                "token_set_id": data["theme_tokens"]["token_set_id"],
                "asset_system_package_ref": data["design_package"].get("asset_system_package_ref"),
            },
            "work_state_reference": {
                "deck_id": data["deck"]["deck_id"],
                "slide_count": len(data["deck"]["slides"]),
                "canvas": data["deck"]["canvas"],
                "fixture_metadata": data["fixture_metadata"],
                "text_role_summary": text_role_summary(data),
                "shape_image_transform_summary": transform_summary(data)[:40],
            },
            "sanitized_operation_summary": [
                {
                    "kind": "cli_handoff_created",
                    "summary": "CLI generated a sanitized workbench handoff envelope.",
                }
            ],
            "revision_memory": [
                {
                    "kind": item.get("kind"),
                    "mode": item.get("mode"),
                    "summary": item.get("summary"),
                }
                for item in data.get("revision_memory", [])[-8:]
            ],
            "reference_design_library": reference_design_summary(data),
            "style_memory": style_memory_summary(data),
            "published_views": published_view_summary(data),
            "referral_entitlement": referral_summary(data),
            "safe_asset_design_refs": safe_asset_design_refs(data),
            "approved_asset_refs": [
                {"slide_id": item["slide_id"], "object_id": item["object_id"], "safeRef": item["safeRef"]}
                for item in transform_summary(data)
                if item.get("safeRef")
            ],
            "forbidden_content_absent": True,
            "final_result_ref": None,
        },
        "honesty": {
            "fake_completion_enabled": False,
            "final_received": False,
            "requires_real_host_ai_result_ref": True,
        },
    }


def open_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "commercial_mvp_workbench_open.v1",
        "status": "ready",
        "open_command": "python scripts/ppt_commercial_mvp_workbench.py open",
        "relative_entrypoint": "web/commercial-mvp-html-workbench/index.html",
        "slide_count": len(data["deck"]["slides"]),
        "default_mode": data["product_boundary"]["default_mode"],
        "modes": data["product_boundary"]["modes"],
        "fixture_only": bool(data.get("fixture_metadata", {}).get("is_fixture")),
        "published_viewer_route": "web/commercial-mvp-html-workbench/viewer.html",
        "reference_design_library": reference_design_summary(data),
        "style_memory": style_memory_summary(data),
        "referral_entitlement": referral_summary(data),
        "generated_work_state_loading": data.get("generated_work_state_loading", {}),
    }


def reference_design_payload(data: dict[str, Any]) -> dict[str, Any]:
    library = data.get("reference_design_library", {})
    return {
        "schema_version": "commercial_mvp_reference_design_recipe_payload.v1",
        "status": "valid",
        "summary": reference_design_summary(data),
        "library_id": library.get("library_id"),
        "extraction_source": library.get("extraction_source"),
        "server_storage_policy": library.get("server_storage_policy"),
        "allowed_recipe_fields": library.get("allowed_recipe_fields"),
        "recipes": library.get("recipes", []),
        "forbidden_content_absent": True,
    }


def imported_reference_design_payload(families: list[str] | None = None) -> dict[str, Any]:
    selected = families or sorted(FAMILIES)
    recipes = [recipe_for_family(family) for family in selected]
    return {
        "schema_version": "commercial_mvp_reference_design_importer.v2",
        "status": "valid",
        "summary": {
            "recipe_count": len(recipes),
            "content_free_only": bool(recipes) and all(recipe_is_content_free(recipe) for recipe in recipes),
            "content_free_schema_support": {
                "content_free_preview_placeholder_labels_only": True,
                "synthetic_placeholder_preview_placeholder_labels_only": True,
            },
        },
        "importer_boundary": {
            "local_host_ai_first": True,
            "server_original_file_upload": False,
            "stores_raw_dom": False,
            "stores_source_text": False,
            "stores_source_coordinates": False,
            "stores_source_screenshots": False,
            "stores_image_urls": False,
            "stores_source_filenames": False,
            "stores_business_content": False,
        },
        "family_evidence": {
            family: family_evidence_present(family)
            for family in selected
        },
        "recipes": recipes,
        "forbidden_content_absent": True,
    }


def viewer_payload(data: dict[str, Any], plan: str) -> dict[str, Any]:
    if plan not in {"free", "paid"}:
        raise ValueError("plan must be free or paid")
    view = next((item for item in data.get("published_views", []) if item.get("plan") == plan), None)
    if not view:
        raise ValueError(f"published view not configured for plan: {plan}")
    return {
        "schema_version": "commercial_mvp_published_view_status.v1",
        "status": "ready",
        "view_id": view.get("view_id"),
        "route": "web/commercial-mvp-html-workbench/viewer.html",
        "plan": plan,
        "read_only": True,
        "watermark": view.get("watermark"),
        "editing_api_exposed": False,
        "raw_workbench_state_exposed": False,
        "raw_asset_urls_exposed": False,
        "package_internals_exposed": False,
    }


def host_return_payload(data: dict[str, Any], return_kind: str, return_ref: str | None) -> dict[str, Any]:
    if return_kind not in {"proposal", "final"}:
        raise ValueError("return-kind must be proposal or final")
    if return_kind == "proposal":
        return {
            "schema_version": "commercial_mvp_host_ai_return_handling.v1",
            "status": "proposal_ready",
            "return_kind": "proposal",
            "proposal_ref": return_ref or "host-proposal-safe-ref-demo",
            "preview_before_apply": data.get("export_hooks", {}).get("proposal_return_handling", {}).get("preview_before_apply") is True,
            "apply_mutates_work_state": True,
            "reject_keeps_work_state": True,
            "raw_payload_stored": False,
        }
    if not return_ref or not return_ref.startswith("host-result-safe-ref"):
        return {
            "schema_version": "commercial_mvp_host_ai_return_handling.v1",
            "status": "awaiting_host_ai",
            "return_kind": "final",
            "final_received": False,
            "requires_real_result_ref": True,
            "reason": "safe_result_ref_required",
        }
    return {
        "schema_version": "commercial_mvp_host_ai_return_handling.v1",
        "status": "final_received",
        "return_kind": "final",
        "final_received": True,
        "result_ref": return_ref,
        "binary_file_in_envelope": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Commercial MVP HTML workbench CLI helper.")
    sub = parser.add_subparsers(dest="command", required=True)
    open_cmd = sub.add_parser("open")
    open_cmd.add_argument("--report", default=None)
    recipe = sub.add_parser("design-recipe")
    recipe.add_argument("--report", default=(BASE_DIR / "outputs" / "reports" / "commercial_mvp_reference_design_recipe.json").as_posix())
    imported_recipe = sub.add_parser("import-design-recipes")
    imported_recipe.add_argument("--family", action="append", choices=sorted(FAMILIES))
    imported_recipe.add_argument("--report", default=(BASE_DIR / "outputs" / "reports" / "commercial_mvp_reference_design_importer.json").as_posix())
    viewer = sub.add_parser("viewer")
    viewer.add_argument("--plan", choices=["free", "paid"], default="free")
    viewer.add_argument("--report", default=(BASE_DIR / "outputs" / "reports" / "commercial_mvp_published_viewer_status.json").as_posix())
    host_return = sub.add_parser("host-return")
    host_return.add_argument("--return-kind", choices=["proposal", "final"], required=True)
    host_return.add_argument("--return-ref", default=None)
    host_return.add_argument("--report", default=(BASE_DIR / "outputs" / "reports" / "commercial_mvp_host_ai_return_handling.json").as_posix())
    handoff = sub.add_parser("handoff")
    handoff.add_argument("--target", choices=["pdf", "pptx"], required=True)
    handoff.add_argument("--mode", choices=["assistant", "auto"], default="assistant")
    handoff.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args()

    data = read_json(DATA_PATH)
    if args.command == "open":
        payload = open_summary(data)
        if args.report:
            report = Path(args.report)
            if not report.is_absolute():
                report = (BASE_DIR / report).resolve()
            write_json(report, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "design-recipe":
        report = Path(args.report)
        if not report.is_absolute():
            report = (BASE_DIR / report).resolve()
        payload = reference_design_payload(data)
        write_json(report, payload)
        print(json.dumps({"status": payload["status"], "report": report.relative_to(BASE_DIR).as_posix()}, ensure_ascii=False))
        return 0

    if args.command == "import-design-recipes":
        report = Path(args.report)
        if not report.is_absolute():
            report = (BASE_DIR / report).resolve()
        payload = imported_reference_design_payload(args.family)
        write_json(report, payload)
        print(json.dumps({"status": payload["status"], "recipes": len(payload["recipes"]), "report": report.relative_to(BASE_DIR).as_posix()}, ensure_ascii=False))
        return 0

    if args.command == "viewer":
        report = Path(args.report)
        if not report.is_absolute():
            report = (BASE_DIR / report).resolve()
        payload = viewer_payload(data, args.plan)
        write_json(report, payload)
        print(json.dumps({"status": payload["status"], "plan": args.plan, "report": report.relative_to(BASE_DIR).as_posix()}, ensure_ascii=False))
        return 0

    if args.command == "host-return":
        report = Path(args.report)
        if not report.is_absolute():
            report = (BASE_DIR / report).resolve()
        payload = host_return_payload(data, args.return_kind, args.return_ref)
        write_json(report, payload)
        print(json.dumps({"status": payload["status"], "report": report.relative_to(BASE_DIR).as_posix()}, ensure_ascii=False))
        return 0

    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()
    payload = create_handoff(data, args.target, args.mode)
    write_json(report, payload)
    print(json.dumps({"status": payload["status"], "report": report.relative_to(BASE_DIR).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
