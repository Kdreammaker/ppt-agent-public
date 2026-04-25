from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from html import escape
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.deck_models import validate_deck_spec

DEFAULT_HTML_ROOT = BASE_DIR / "outputs" / "html"
OUTPUTS_ROOT = BASE_DIR / "outputs"
DEFAULT_THEME = {
    "font_family": "Arial",
    "colors": {
        "primary": "#10213B",
        "accent_1": "#1D49F3",
        "accent_2": "#2ECE7B",
        "dark": "#272727",
        "gray": "#626D80",
        "mid": "#7A8494",
        "white": "#FFFFFF",
        "light": "#F6F8FC",
        "panel": "#EFF4FB",
        "border": "#E0E5EE",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_path(base_dir: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def require_repo_output_path(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    allowed_roots = [OUTPUTS_ROOT.resolve()]
    workspace = os.environ.get("PPT_AGENT_WORKSPACE")
    if workspace:
        allowed_roots.append((Path(workspace) / "outputs").resolve())
    if not any(resolved == root or resolved.is_relative_to(root) for root in allowed_roots):
        roots = ", ".join(root.as_posix() for root in allowed_roots)
        raise ValueError(f"{label} must stay under one of [{roots}]: {resolved}")
    return resolved


def base_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "deck"


def normalize_color(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"#?[0-9A-Fa-f]{6}", text):
        return "#" + text.lstrip("#").upper()
    return fallback


def load_theme(spec: dict[str, Any], spec_dir: Path) -> dict[str, Any]:
    theme_path = resolve_path(spec_dir, spec.get("theme_path"))
    if theme_path and theme_path.exists():
        data = load_json(theme_path)
    else:
        data = dict(DEFAULT_THEME)
    colors = dict(DEFAULT_THEME["colors"])
    colors.update(data.get("colors", {}))
    data["colors"] = {key: normalize_color(value, colors.get(key, "#000000")) for key, value in colors.items()}
    data["font_family"] = str(data.get("font_family") or DEFAULT_THEME["font_family"])
    return data


def spec_output_stem(spec: dict[str, Any], spec_dir: Path, spec_path: Path) -> str:
    output_path = resolve_path(spec_dir, spec.get("output_path"))
    if output_path:
        return output_path.stem
    return spec_path.stem


def default_output_path(spec: dict[str, Any], spec_dir: Path, spec_path: Path) -> Path:
    return DEFAULT_HTML_ROOT / spec_output_stem(spec, spec_dir, spec_path) / "index.html"


def text_slots(slide: dict[str, Any]) -> dict[str, str]:
    raw = slide.get("text_slots", {})
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items() if str(value).strip()}
    return {}


def slide_selector(slide: dict[str, Any]) -> dict[str, Any]:
    raw = slide.get("slide_selector", {})
    return raw if isinstance(raw, dict) else {}


def slide_purpose(slide: dict[str, Any]) -> str:
    selector = slide_selector(slide)
    return str(selector.get("purpose") or slide.get("purpose") or "content")


def preferred_title(slide: dict[str, Any], index: int) -> str:
    slots = text_slots(slide)
    for key in ("title", "headline", "hero_title", "cover_title", "section_title"):
        if slots.get(key):
            return slots[key]
    values = [str(item) for item in slide.get("text_values", []) if str(item).strip()]
    if values:
        return values[0]
    return f"Slide {index}"


def preferred_subtitle(slide: dict[str, Any]) -> str:
    slots = text_slots(slide)
    for key in ("subtitle", "kicker", "section_header", "summary", "body"):
        if slots.get(key):
            return slots[key]
    return ""


def body_slot_items(slide: dict[str, Any]) -> list[tuple[str, str]]:
    skipped = {"title", "headline", "hero_title", "cover_title", "section_title", "subtitle", "kicker"}
    items = [(key, value) for key, value in text_slots(slide).items() if key not in skipped]
    values = [str(item) for item in slide.get("text_values", []) if str(item).strip()]
    if values:
        title = preferred_title(slide, 0)
        for idx, value in enumerate(values, start=1):
            if idx == 1 and value == title:
                continue
            items.append((f"text_{idx}", value))
    return items


def asset_intents_by_slide(spec: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    by_slide: dict[int, list[dict[str, Any]]] = {}
    for intent in spec.get("asset_intents", []):
        if not isinstance(intent, dict):
            continue
        slide_number = intent.get("slide_number")
        if isinstance(slide_number, int):
            by_slide.setdefault(slide_number, []).append(intent)
    return by_slide


def render_slot_list(items: list[tuple[str, str]]) -> str:
    if not items:
        return '<p class="muted">No additional text slots.</p>'
    lines = []
    for key, value in items:
        lines.append(
            '<div class="slot-row">'
            f'<span class="slot-key">{escape(key.replace("_", " ").title())}</span>'
            f'<span class="slot-value">{escape(value)}</span>'
            "</div>"
        )
    return "\n".join(lines)


def render_chart_slot(name: str, chart: dict[str, Any]) -> str:
    categories = [str(item) for item in chart.get("categories", [])]
    values = [float(item) for item in chart.get("values", [])]
    if not categories or len(categories) != len(values):
        return ""
    max_value = max(max(values), 1.0)
    bars = []
    for category, value in zip(categories, values):
        width = max(4, min(100, round((value / max_value) * 100)))
        bars.append(
            '<div class="bar-row">'
            f'<span class="bar-label">{escape(category)}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{width}%"></span></span>'
            f'<span class="bar-value">{escape(str(value).rstrip("0").rstrip("."))}</span>'
            "</div>"
        )
    return (
        '<figure class="chart-block">'
        f'<figcaption>{escape(name.replace("_", " ").title())}</figcaption>'
        + "\n".join(bars)
        + "</figure>"
    )


def render_table_slot(name: str, table: dict[str, Any]) -> str:
    headers = [str(item) for item in table.get("headers", [])]
    rows = [[str(cell) for cell in row] for row in table.get("rows", [])]
    if not rows:
        return ""
    head = ""
    if headers:
        head = "<thead><tr>" + "".join(f"<th>{escape(item)}</th>" for item in headers) + "</tr></thead>"
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>")
    return (
        '<figure class="table-block">'
        f'<figcaption>{escape(name.replace("_", " ").title())}</figcaption>'
        "<table>"
        + head
        + "<tbody>"
        + "".join(body_rows)
        + "</tbody></table></figure>"
    )


def render_media_panel(slide: dict[str, Any], intents: list[dict[str, Any]]) -> str:
    image_slots = slide.get("image_slots", {})
    image_count = len(image_slots) if isinstance(image_slots, dict) else 0
    placeholders = [intent for intent in intents if intent.get("role") == "image_placeholder"]
    icons = [intent for intent in intents if intent.get("role") == "icon"]
    chunks: list[str] = []
    if image_count or placeholders:
        label = "Image"
        if placeholders and placeholders[0].get("slot"):
            label = str(placeholders[0]["slot"]).replace("_", " ").title()
        chunks.append(
            '<div class="media-placeholder">'
            '<span class="media-mark"></span>'
            f'<strong>{escape(label)}</strong>'
            '<small>User-supplied or generated asset slot</small>'
            "</div>"
        )
    for icon in icons[:2]:
        chunks.append(
            '<div class="icon-intent">'
            '<span class="icon-symbol">+</span>'
            f'<span>{escape(str(icon.get("asset_id", "icon")).split(".")[-1].replace("_", " "))}</span>'
            "</div>"
        )
    if not chunks:
        chunks.append('<div class="media-placeholder quiet"><span class="media-mark"></span><strong>Visual area</strong></div>')
    return '<aside class="media-panel">' + "\n".join(chunks) + "</aside>"


def render_slide(slide: dict[str, Any], index: int, total: int, intents: list[dict[str, Any]]) -> str:
    title = preferred_title(slide, index)
    subtitle = preferred_subtitle(slide)
    purpose = slide_purpose(slide)
    chart_blocks = [
        render_chart_slot(str(name), chart)
        for name, chart in (slide.get("chart_slots", {}) or {}).items()
        if isinstance(chart, dict)
    ]
    table_blocks = [
        render_table_slot(str(name), table)
        for name, table in (slide.get("table_slots", {}) or {}).items()
        if isinstance(table, dict)
    ]
    body = render_slot_list(body_slot_items(slide))
    return f"""
<section class="deck-slide" data-slide-number="{index}" data-purpose="{escape(purpose)}">
  <div class="slide-shell">
    <header class="slide-heading">
      <div class="slide-meta"><span>{index:02d}</span><span>{escape(purpose.replace("_", " ").title())}</span><span>{total:02d}</span></div>
      <h2>{escape(title)}</h2>
      {f'<p>{escape(subtitle)}</p>' if subtitle else ''}
    </header>
    <main class="slide-grid">
      <section class="content-panel">
        {body}
        {''.join(chart_blocks)}
        {''.join(table_blocks)}
      </section>
      {render_media_panel(slide, intents)}
    </main>
  </div>
</section>"""


def deck_language(spec: dict[str, Any]) -> str:
    text = json.dumps(spec, ensure_ascii=False)
    return "ko" if re.search(r"[\uac00-\ud7a3]", text) else "en"


def build_html(spec_path: Path, output_path: Path | None = None) -> tuple[Path, Path]:
    spec_path = spec_path.resolve()
    spec_dir = spec_path.parent
    spec = load_json(spec_path)
    validate_deck_spec(spec)
    theme = load_theme(spec, spec_dir)
    output_path = require_repo_output_path(output_path or default_output_path(spec, spec_dir, spec_path), label="HTML output path")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path.with_name("html_manifest.json")
    slides = spec.get("slides", [])
    intents_by_slide = asset_intents_by_slide(spec)
    colors = theme["colors"]
    created_at = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    slide_markup = "\n".join(
        render_slide(slide, index, len(slides), intents_by_slide.get(index, []))
        for index, slide in enumerate(slides, start=1)
    )
    html = f"""<!doctype html>
<html lang="{deck_language(spec)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="ppt-output-role" content="final_html">
  <title>{escape(str(spec.get("name", output_path.stem)))}</title>
  <style>
    :root {{
      --primary: {colors["primary"]};
      --accent-a: {colors["accent_1"]};
      --accent-b: {colors["accent_2"]};
      --dark: {colors["dark"]};
      --gray: {colors["gray"]};
      --mid: {colors["mid"]};
      --white: {colors["white"]};
      --light: {colors["light"]};
      --panel: {colors["panel"]};
      --border: {colors["border"]};
      --font: "{escape(str(theme["font_family"]))}", Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: var(--font);
      color: var(--dark);
      background: var(--light);
    }}
    .deck-root {{
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }}
    .deck-toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 20px;
      color: var(--white);
      background: var(--primary);
    }}
    .deck-toolbar strong {{
      font-size: 15px;
      font-weight: 700;
    }}
    .deck-toolbar span {{
      color: rgba(255,255,255,.78);
      font-size: 12px;
    }}
    .deck-actions {{
      display: flex;
      gap: 8px;
    }}
    .deck-actions button {{
      width: 34px;
      height: 34px;
      border: 1px solid rgba(255,255,255,.32);
      border-radius: 6px;
      color: var(--white);
      background: rgba(255,255,255,.12);
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
    }}
    .deck-stage {{
      width: min(1280px, 100vw);
      margin: 0 auto;
      padding: 18px;
    }}
    .deck-slide {{
      display: none;
      aspect-ratio: 16 / 9;
      min-height: 520px;
      background: var(--white);
      border: 1px solid var(--border);
      box-shadow: 0 18px 50px rgba(15, 23, 42, .14);
    }}
    .deck-slide.active {{
      display: block;
    }}
    .slide-shell {{
      height: 100%;
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 24px;
      padding: clamp(28px, 4vw, 58px);
      overflow: hidden;
    }}
    .slide-heading {{
      display: grid;
      gap: 10px;
    }}
    .slide-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--accent-a);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    h2 {{
      margin: 0;
      max-width: 940px;
      color: var(--primary);
      font-size: clamp(30px, 4.6vw, 54px);
      line-height: 1.04;
      letter-spacing: 0;
    }}
    .slide-heading p {{
      margin: 0;
      max-width: 820px;
      color: var(--gray);
      font-size: clamp(15px, 2vw, 22px);
      line-height: 1.38;
    }}
    .slide-grid {{
      min-height: 0;
      display: grid;
      grid-template-columns: minmax(0, 1.3fr) minmax(240px, .7fr);
      gap: 22px;
      align-items: stretch;
    }}
    .content-panel {{
      min-width: 0;
      display: grid;
      align-content: start;
      gap: 12px;
    }}
    .slot-row {{
      display: grid;
      grid-template-columns: minmax(116px, .24fr) minmax(0, 1fr);
      gap: 14px;
      padding: 12px 0;
      border-bottom: 1px solid var(--border);
    }}
    .slot-key {{
      color: var(--mid);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .slot-value {{
      color: var(--dark);
      font-size: clamp(14px, 1.4vw, 18px);
      line-height: 1.38;
      overflow-wrap: anywhere;
    }}
    .media-panel {{
      min-width: 0;
      display: grid;
      align-content: stretch;
      gap: 12px;
    }}
    .media-placeholder {{
      min-height: 180px;
      display: grid;
      place-items: center;
      gap: 8px;
      padding: 20px;
      border: 1px dashed var(--accent-b);
      background: var(--panel);
      color: var(--primary);
      text-align: center;
    }}
    .media-placeholder small {{
      color: var(--gray);
      font-size: 12px;
    }}
    .media-placeholder.quiet {{
      border-color: var(--border);
      color: var(--mid);
    }}
    .media-mark {{
      width: 52px;
      aspect-ratio: 1;
      border: 8px solid rgba(29, 73, 243, .16);
      border-top-color: var(--accent-a);
      border-radius: 50%;
    }}
    .icon-intent {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px;
      border: 1px solid var(--border);
      background: var(--white);
      color: var(--gray);
      font-size: 13px;
    }}
    .icon-symbol {{
      display: inline-grid;
      place-items: center;
      width: 28px;
      aspect-ratio: 1;
      border-radius: 50%;
      background: var(--accent-b);
      color: var(--white);
      font-weight: 700;
    }}
    .chart-block, .table-block {{
      margin: 10px 0 0;
      padding: 14px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,.72);
    }}
    figcaption {{
      margin-bottom: 12px;
      color: var(--primary);
      font-weight: 700;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 90px 1fr 54px;
      gap: 10px;
      align-items: center;
      margin: 8px 0;
      font-size: 12px;
    }}
    .bar-track {{
      height: 12px;
      background: var(--border);
    }}
    .bar-fill {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, var(--accent-a), var(--accent-b));
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 8px;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
    th {{
      color: var(--primary);
      background: var(--panel);
    }}
    .muted {{
      color: var(--gray);
    }}
    @media (max-width: 760px) {{
      .deck-toolbar {{
        padding: 10px 12px;
      }}
      .deck-stage {{
        padding: 10px;
      }}
      .deck-slide {{
        aspect-ratio: auto;
        min-height: calc(100vh - 76px);
      }}
      .slide-shell {{
        padding: 24px;
      }}
      .slide-grid {{
        grid-template-columns: 1fr;
      }}
      .slot-row {{
        grid-template-columns: 1fr;
        gap: 4px;
      }}
    }}
  </style>
</head>
<body>
  <div class="deck-root" data-output-role="final_html" data-slide-count="{len(slides)}" data-source-spec="{escape(base_relative(spec_path))}">
    <nav class="deck-toolbar" aria-label="Deck controls">
      <div><strong>{escape(str(spec.get("name", output_path.stem)))}</strong><br><span>HTML final output</span></div>
      <div class="deck-actions">
        <button type="button" id="prevSlide" title="Previous slide" aria-label="Previous slide">&#8249;</button>
        <button type="button" id="nextSlide" title="Next slide" aria-label="Next slide">&#8250;</button>
      </div>
    </nav>
    <main class="deck-stage" aria-live="polite">
      {slide_markup}
    </main>
  </div>
  <script>
    const slides = Array.from(document.querySelectorAll('.deck-slide'));
    let current = 0;
    function show(index) {{
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, idx) => {{
        slide.classList.toggle('active', idx === current);
        slide.setAttribute('aria-hidden', idx === current ? 'false' : 'true');
      }});
    }}
    document.getElementById('prevSlide').addEventListener('click', () => show(current - 1));
    document.getElementById('nextSlide').addEventListener('click', () => show(current + 1));
    document.addEventListener('keydown', (event) => {{
      if (event.key === 'ArrowLeft') show(current - 1);
      if (event.key === 'ArrowRight' || event.key === ' ') show(current + 1);
    }});
    show(0);
  </script>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "created_at": created_at,
        "output_role": "final_html",
        "source_spec_path": base_relative(spec_path),
        "html_path": base_relative(output_path),
        "deck_name": spec.get("name"),
        "slide_count": len(slides),
        "asset_policy": "single_file_no_remote_assets",
        "human_editable_outputs": ["pptx", "google_slides"],
        "browser_delivery_outputs": ["html"],
        "preview_derivatives": ["pdf", "png"],
        "notes": "HTML is a final browser/share/presentation output. PPTX and Google Slides remain preferred human-editable outputs.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path, manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a single-file HTML final output from a deck spec.")
    parser.add_argument("spec_path")
    parser.add_argument("--output", default=None, help="Optional HTML output path. Defaults to outputs/html/<deck>/index.html.")
    args = parser.parse_args(argv)
    spec_path = Path(args.spec_path)
    output_path = Path(args.output) if args.output else None
    html_path, manifest_path = build_html(spec_path, output_path)
    print(html_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
