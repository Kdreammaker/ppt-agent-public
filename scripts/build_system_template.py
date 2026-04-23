from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.pptx_system import ThemeConfig, build_curated_template, load_catalog


WORKDIR = BASE_DIR
SOURCE_TEMPLATE = WORKDIR / "assets" / "slides" / "references" / "template.pptx"
CATALOG_PATH = WORKDIR / "config" / "template_catalog.json"
THEME_PATH = WORKDIR / "config" / "pptx_theme.example.json"
OUTPUT_PATH = WORKDIR / "outputs" / "cache" / "template_system_base.pptx"


def main() -> Path:
    catalog = load_catalog(CATALOG_PATH)
    theme = ThemeConfig.from_json(THEME_PATH)

    return build_curated_template(
        source_template=SOURCE_TEMPLATE,
        output_path=OUTPUT_PATH,
        keep_slides=catalog["recipes"]["system_base"],
        placeholder_map=catalog["placeholder_translation"],
        theme=theme,
    )


if __name__ == "__main__":
    print(main())
