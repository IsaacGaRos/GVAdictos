from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.paths import DB_PATH, EXPORTS_DIR, ensure_runtime_dirs


def main() -> None:
    ensure_runtime_dirs()
    if not DB_PATH.exists():
        raise SystemExit("No existe la base de datos todavia.")
    target = EXPORTS_DIR / f"backup_gvadicto_{datetime.now():%Y%m%d_%H%M%S}.sqlite"
    shutil.copy2(DB_PATH, target)
    print(target)


if __name__ == "__main__":
    main()
