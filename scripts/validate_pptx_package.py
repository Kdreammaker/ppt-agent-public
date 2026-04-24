from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def duplicate_entries(path: Path) -> list[tuple[str, int]]:
    with ZipFile(path) as zf:
        counts = Counter(zf.namelist())
    return sorted((name, count) for name, count in counts.items() if count > 1)


def validate(path: Path) -> list[tuple[str, int]]:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pptx":
        raise ValueError(f"Expected a .pptx file, got: {path}")
    return duplicate_entries(path)


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python scripts/validate_pptx_package.py <pptx> [<pptx> ...]", file=sys.stderr)
        return 2

    failed = False
    for value in argv:
        path = Path(value).resolve()
        try:
            duplicates = validate(path)
        except (BadZipFile, FileNotFoundError, ValueError) as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failed = True
            continue

        if duplicates:
            failed = True
            details = ", ".join(f"{name} x{count}" for name, count in duplicates)
            print(f"{path}: duplicate package entries found: {details}", file=sys.stderr)
        else:
            print(f"{path}: package entries OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
