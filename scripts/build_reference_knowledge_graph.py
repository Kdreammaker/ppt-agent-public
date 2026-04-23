from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.reference_pipeline import LIBRARY_ROOT, load_json, write_json

REFERENCE_CATALOG = BASE_DIR / "config" / "reference_catalog.json"
TEMPLATE_DNA = BASE_DIR / "config" / "template_design_dna.json"
OUTPUT = BASE_DIR / "config" / "reference_knowledge_graph.json"


def add_node(nodes: dict[str, dict[str, Any]], node_id: str, node_type: str, label: str, **props: Any) -> None:
    nodes.setdefault(node_id, {"id": node_id, "type": node_type, "label": label, **props})


def add_edge(edges: list[dict[str, Any]], source: str, target: str, edge_type: str, **props: Any) -> None:
    edges.append({"source": source, "target": target, "type": edge_type, **props})


def build_graph() -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    generated_from = ["config/reference_catalog.json", "config/template_design_dna.json", "assets/slides/library/*/metadata/*.json"]

    if REFERENCE_CATALOG.exists():
        catalog = load_json(REFERENCE_CATALOG)
        for slide in catalog.get("slides", []):
            template_id = f"production_template:{slide['slide_id']}"
            add_node(nodes, template_id, "production_template", slide["slide_id"], purpose=slide.get("purpose"), scope=slide.get("scope"))
            for key, node_type, edge_type in (
                ("purpose", "category", "HAS_CATEGORY"),
                ("scope", "deck_type", "FITS_DECK_TYPE"),
                ("density", "layout", "HAS_LAYOUT"),
            ):
                value = slide.get(key)
                if not value:
                    continue
                node_id = f"{node_type}:{value}"
                add_node(nodes, node_id, node_type, str(value))
                add_edge(edges, template_id, node_id, edge_type, confidence=1.0, source_artifact="reference_catalog")
            for tag in slide.get("style_tags", []):
                node_id = f"style:{tag}"
                add_node(nodes, node_id, "style_cluster", str(tag))
                add_edge(edges, template_id, node_id, "HAS_STYLE", confidence=0.8, source_artifact="reference_catalog")

    if TEMPLATE_DNA.exists():
        dna = load_json(TEMPLATE_DNA)
        for slide_id, fields in dna.get("slides", {}).items():
            template_id = f"production_template:{slide_id}"
            add_node(nodes, template_id, "production_template", slide_id)
            for tone in fields.get("tone", []):
                node_id = f"audience:{tone}"
                add_node(nodes, node_id, "audience", str(tone))
                add_edge(edges, template_id, node_id, "FITS_AUDIENCE", confidence=0.65, source_artifact="template_design_dna")
            structure = fields.get("structure")
            if structure:
                node_id = f"layout:{structure}"
                add_node(nodes, node_id, "layout", str(structure))
                add_edge(edges, template_id, node_id, "HAS_LAYOUT", confidence=0.75, source_artifact="template_design_dna")

    for metadata_path in LIBRARY_ROOT.glob("*/metadata/*.json"):
        metadata = load_json(metadata_path)
        for record in metadata.get("slides", []):
            identity = record.get("identity", {})
            curation = record.get("curation", {})
            slide_id = identity.get("slide_id")
            if not slide_id:
                continue
            node_id = f"slide:{slide_id}"
            add_node(nodes, node_id, "slide", str(slide_id), quality=curation.get("quality_label"))
            quality_id = f"quality_label:{curation.get('quality_label')}"
            add_node(nodes, quality_id, "quality_label", str(curation.get("quality_label")))
            add_edge(edges, node_id, quality_id, "HAS_QUALITY", confidence=1.0, source_artifact="library_metadata")
            category = record.get("semantic_seed", {}).get("initial_category_guess", {}).get("value")
            if category:
                category_id = f"category:{category}"
                add_node(nodes, category_id, "category", str(category))
                add_edge(edges, node_id, category_id, "HAS_CATEGORY", confidence=0.35, source_artifact="semantic_seed")

    return {
        "schema_version": "1.0",
        "generated_from": generated_from,
        "nodes": sorted(nodes.values(), key=lambda node: node["id"]),
        "edges": sorted(edges, key=lambda edge: (edge["source"], edge["type"], edge["target"])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build reference knowledge graph JSON.")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args(argv)
    output = Path(args.output)
    if not output.is_absolute():
        output = (BASE_DIR / output).resolve()
    graph = build_graph()
    write_json(output, graph)
    print(f"nodes={len(graph['nodes'])} edges={len(graph['edges'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
