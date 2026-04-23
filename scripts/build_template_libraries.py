from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from pptx import Presentation

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.pptx_system import reorder_and_trim_slides


CATALOG_PATH = BASE_DIR / "config" / "template_library_catalog.json"
BLUEPRINT_PATH = BASE_DIR / "config" / "template_blueprints.json"
DEFAULT_MANIFEST_PATH = BASE_DIR / "config" / "template_slot_name_manifest.json"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (BASE_DIR / path).resolve()


def build_library(source_path: Path, output_path: Path, slide_numbers: list[int]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output_path)
    prs = Presentation(str(output_path))
    reorder_and_trim_slides(prs, slide_numbers)
    prs.save(str(output_path))
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build curated PPTX template libraries.")
    parser.add_argument("--catalog-path", default=str(CATALOG_PATH))
    parser.add_argument(
        "--apply-slot-name-manifest",
        action="store_true",
        help="Reapply stable slot:<name> identities after rebuilding libraries.",
    )
    parser.add_argument(
        "--manifest-path",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Manifest used with --apply-slot-name-manifest.",
    )
    parser.add_argument("--blueprint-path", default=str(BLUEPRINT_PATH))
    args = parser.parse_args(argv)

    catalog_path = resolve_path(args.catalog_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for library in catalog["libraries"]:
        source_path = resolve_path(library["source_path"])
        output_path = resolve_path(library["output_path"])
        slide_numbers = [item["slide_no"] for item in library["slides"]]
        built = build_library(source_path, output_path, slide_numbers)
        print(built)

    if args.apply_slot_name_manifest:
        from scripts.manage_template_slot_names import apply_manifest

        apply_manifest(Path(args.manifest_path).resolve(), Path(args.blueprint_path).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
