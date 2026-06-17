from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.laws.importer import import_law


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa una ley TXT/MD en GVAdicto.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--name", help="Nombre de la norma")
    args = parser.parse_args()

    law_id = import_law(args.path, args.name)
    print(f"Ley importada con id {law_id}")


if __name__ == "__main__":
    main()
