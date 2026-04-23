from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def preferred_blueprint_source(path: str | Path) -> Path:
    source = Path(path)
    if source.is_dir():
        return source
    shard_dir = source.with_suffix("")
    if shard_dir.is_dir():
        return shard_dir
    return source


def load_blueprints(path: str | Path) -> dict[str, Any]:
    source = preferred_blueprint_source(path)
    if source.is_dir():
        return load_sharded_blueprints(source)
    return json.loads(source.read_text(encoding="utf-8"))


def save_blueprints(path: str | Path, data: dict[str, Any]) -> None:
    target = Path(path)
    if target.suffix == "":
        save_sharded_blueprints(target, data)
        return
    shard_dir = target if target.is_dir() else target.with_suffix("")
    if target.is_dir() or shard_dir.is_dir():
        save_sharded_blueprints(shard_dir, data)
        if not target.is_dir():
            write_blueprint_file(target, data)
        return
    write_blueprint_file(target, data)


def export_blueprint_file(path: str | Path, data: dict[str, Any]) -> None:
    write_blueprint_file(Path(path), data)


def load_sharded_blueprints(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    registry_path = directory / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    slides: dict[str, Any] = {}

    for library in registry.get("libraries", []):
        shard_path = directory / library["path"]
        shard = json.loads(shard_path.read_text(encoding="utf-8"))
        for slide_id, blueprint in shard.get("slides", {}).items():
            if slide_id in slides:
                raise ValueError(f"Duplicate blueprint slide_id across shards: {slide_id}")
            slides[slide_id] = blueprint

    return {"version": registry.get("version"), "slides": dict(sorted(slides.items()))}


def save_sharded_blueprints(directory: str | Path, data: dict[str, Any]) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, dict[str, Any]] = {}
    for slide_id, blueprint in sorted(data.get("slides", {}).items()):
        library_id = blueprint.get("library_id")
        if not library_id:
            raise ValueError(f"Blueprint is missing library_id: {slide_id}")
        grouped.setdefault(library_id, {})[slide_id] = blueprint

    libraries = []
    for library_id, slides in sorted(grouped.items()):
        shard_name = f"{library_id}.json"
        shard_path = directory / shard_name
        shard = {
            "version": data.get("version"),
            "library_id": library_id,
            "slides": slides,
        }
        write_blueprint_file(shard_path, shard)
        libraries.append({"library_id": library_id, "path": shard_name, "slide_count": len(slides)})

    registry = {"version": data.get("version"), "libraries": libraries}
    write_blueprint_file(directory / "registry.json", registry)


def write_blueprint_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
