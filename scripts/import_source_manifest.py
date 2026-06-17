from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.source_catalog import import_source_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga un manifiesto CSV de fuentes en SQLite.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    count = import_source_manifest(args.path)
    print(f"Fuentes catalogadas: {count}")


if __name__ == "__main__":
    main()
