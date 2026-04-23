from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.deck_models import validate_deck_spec

REPORTS_DIR = BASE_DIR / "outputs" / "reports"
RUNS_DIR = BASE_DIR / "outputs" / "runs"
PROJECTS_DIR = BASE_DIR / "outputs" / "projects"
AUTHORING_REPORT_SUFFIXES = (
    "text_overflow",
    "slide_selection_rationale",
    "deck_slot_map",
)
VALIDATION_REPORT_SUFFIXES = (
    "visual_smoke",
    "quality",
    "design_review",
)


def resolve_path(base_dir: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def load_spec(spec_path: str | Path) -> tuple[dict[str, Any], Path]:
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    validate_deck_spec(spec)
    return spec, spec_path.parent


def default_run_id(output_path: Path) -> str:
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{output_path.stem}"


def default_project_id(output_path: Path) -> str:
    return output_path.stem


def utc_timestamp() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def relative_to_base(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return Path(os.path.relpath(resolved, BASE_DIR)).as_posix()


def deck_report_paths(output_path: Path, *, include_validation_reports: bool = False) -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    suffixes = set(AUTHORING_REPORT_SUFFIXES)
    if include_validation_reports:
        suffixes.update(VALIDATION_REPORT_SUFFIXES)
    paths: list[Path] = []
    for suffix in sorted(suffixes):
        paths.extend(sorted(REPORTS_DIR.glob(f"{output_path.stem}_{suffix}.json")))
        paths.extend(sorted(REPORTS_DIR.glob(f"{output_path.stem}_{suffix}.md")))
    return paths


def visual_smoke_preview_dir(output_path: Path) -> Path:
    return BASE_DIR / "outputs" / "previews" / "visual_smoke" / output_path.stem


def copy_tree_contents(source: Path, target: Path) -> list[str]:
    copied: list[str] = []
    if not source.exists():
        return copied
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        copied.append(destination.relative_to(BASE_DIR).as_posix())
    return copied


def resolved_project_doc_paths(spec: dict[str, Any], spec_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for value in [spec.get("design_brief_path"), *spec.get("doc_paths", [])]:
        path = resolve_path(spec_dir, value)
        if path and path.exists() and path.is_file():
            paths.append(path)
    return paths


def resolved_project_image_paths(spec: dict[str, Any], spec_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for slide in spec.get("slides", []):
        for image in slide.get("images", []):
            path = resolve_path(spec_dir, image.get("path"))
            if path and path.exists() and path.is_file():
                paths.append(path)
        for value in slide.get("image_slots", {}).values():
            path = resolve_path(spec_dir, value)
            if path and path.exists() and path.is_file():
                paths.append(path)
    return sorted({path.resolve() for path in paths})


def write_project_readme(
    *,
    project_dir: Path,
    project_id: str,
    output_path: Path,
    copied_docs: list[str],
    copied_images: list[str],
    copied_previews: list[str],
) -> None:
    lines = [
        f"# {project_id}",
        "",
        "This folder is a project-scoped PPT output bundle. Open this folder first when reviewing or revising the deck.",
        "",
        "## Main Files",
        f"- `deck/{output_path.name}`: final PPTX deck",
        "- `specs/`: source deck spec used for generation",
        "- `docs/`: design brief and other authoring notes",
        "- `assets/images/`: images referenced by the deck spec",
        "- `previews/`: rendered slide images/PDF from visual smoke checks when available",
        "- `reports/`: validation and authoring reports",
        "- `project_manifest.json`: machine-readable project bundle manifest",
        "",
        "## Bundle Status",
        f"- Documents copied: {len(copied_docs)}",
        f"- Images copied: {len(copied_images)}",
        f"- Preview files copied: {len(copied_previews)}",
        "",
        "Compatibility outputs may still exist under `outputs/decks/` and `outputs/reports/`, but this project folder is the writer-facing bundle.",
        "",
    ]
    (project_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def mirror_project_outputs(
    *,
    project_id: str,
    spec_path: Path,
    output_path: Path,
    validation_results: list[dict[str, Any]] | None = None,
    reference_capture: dict[str, Any] | None = None,
) -> Path:
    spec, spec_dir = load_spec(spec_path)
    project_dir = (PROJECTS_DIR / project_id).resolve()
    if not project_dir.is_relative_to(PROJECTS_DIR.resolve()):
        raise ValueError(f"project_id resolves outside outputs/projects: {project_id}")
    if project_dir.exists():
        shutil.rmtree(project_dir)
    deck_dir = project_dir / "deck"
    docs_dir = project_dir / "docs"
    image_dir = project_dir / "assets" / "images"
    reports_dir = project_dir / "reports"
    specs_dir = project_dir / "specs"
    previews_dir = project_dir / "previews"
    exports_dir = project_dir / "exports"
    for directory in (deck_dir, docs_dir, image_dir, reports_dir, specs_dir, previews_dir, exports_dir):
        directory.mkdir(parents=True, exist_ok=True)

    copied_docs: list[str] = []
    copied_images: list[str] = []
    copied_reports: list[str] = []
    copied_previews: list[str] = []

    if output_path.exists():
        shutil.copy2(output_path, deck_dir / output_path.name)
    if spec_path.exists():
        shutil.copy2(spec_path, specs_dir / spec_path.name)

    for doc in resolved_project_doc_paths(spec, spec_dir):
        target = docs_dir / doc.name
        shutil.copy2(doc, target)
        copied_docs.append(target.relative_to(BASE_DIR).as_posix())

    for image in resolved_project_image_paths(spec, spec_dir):
        target = image_dir / image.name
        shutil.copy2(image, target)
        copied_images.append(target.relative_to(BASE_DIR).as_posix())

    include_validation_reports = bool(validation_results)
    for report in deck_report_paths(output_path, include_validation_reports=include_validation_reports):
        target = reports_dir / report.name
        shutil.copy2(report, target)
        copied_reports.append(target.relative_to(BASE_DIR).as_posix())

    if include_validation_reports:
        copied_previews = copy_tree_contents(visual_smoke_preview_dir(output_path), previews_dir)

    write_project_readme(
        project_dir=project_dir,
        project_id=project_id,
        output_path=output_path,
        copied_docs=copied_docs,
        copied_images=copied_images,
        copied_previews=copied_previews,
    )

    manifest = {
        "schema_version": "1.0",
        "project_id": project_id,
        "created_at": utc_timestamp(),
        "source": {
            "input_spec_path": relative_to_base(spec_path),
            "output_deck_path": relative_to_base(output_path),
        },
        "bundle": {
            "project_root": relative_to_base(project_dir),
            "deck_path": relative_to_base(deck_dir / output_path.name),
            "spec_path": relative_to_base(specs_dir / spec_path.name),
            "doc_paths": copied_docs,
            "image_paths": copied_images,
            "report_paths": copied_reports,
            "preview_paths": copied_previews,
        },
        "validation_results": validation_results or [],
        "known_caveats": [],
    }
    if reference_capture is not None:
        manifest["reference_capture"] = reference_capture
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def mirror_run_outputs(
    *,
    run_id: str,
    spec_path: Path,
    output_path: Path,
    validation_results: list[dict[str, Any]] | None = None,
) -> Path:
    run_dir = (RUNS_DIR / run_id).resolve()
    if not run_dir.is_relative_to(RUNS_DIR.resolve()):
        raise ValueError(f"run_id resolves outside outputs/runs: {run_id}")
    deck_dir = run_dir / "decks"
    reports_dir = run_dir / "reports"
    specs_dir = run_dir / "specs"
    previews_dir = run_dir / "previews"
    visual_previews_dir = previews_dir / "visual_smoke" / output_path.stem
    for directory in (deck_dir, reports_dir, specs_dir, previews_dir):
        directory.mkdir(parents=True, exist_ok=True)

    copied_reports: list[str] = []
    copied_previews: list[str] = []
    if output_path.exists():
        shutil.copy2(output_path, deck_dir / output_path.name)
    if spec_path.exists():
        shutil.copy2(spec_path, specs_dir / spec_path.name)
    include_validation_reports = bool(validation_results)
    for report in deck_report_paths(output_path, include_validation_reports=include_validation_reports):
        target = reports_dir / report.name
        shutil.copy2(report, target)
        copied_reports.append(target.relative_to(BASE_DIR).as_posix())
    if include_validation_reports:
        copied_previews = copy_tree_contents(visual_smoke_preview_dir(output_path), visual_previews_dir)

    source = {
        "input_spec_path": relative_to_base(spec_path),
        "output_deck_path": relative_to_base(output_path),
    }
    bundle = {
        "run_root": relative_to_base(run_dir),
        "deck_path": relative_to_base(deck_dir / output_path.name),
        "spec_path": relative_to_base(specs_dir / spec_path.name),
        "report_paths": copied_reports,
        "preview_paths": copied_previews,
    }

    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "created_at": utc_timestamp(),
        "source": source,
        "bundle": bundle,
        "report_paths": copied_reports,
        "validation_results": validation_results or [],
        "known_caveats": [],
        "input_spec_path": source["input_spec_path"],
        "output_deck_path": source["output_deck_path"],
        "run_deck_path": bundle["deck_path"],
        "run_spec_path": bundle["spec_path"],
    }
    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path
