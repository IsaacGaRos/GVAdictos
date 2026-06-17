from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "db" / "gvadicto.sqlite"
EXPORTS_DIR = ROOT_DIR / "data" / "exports"
LAW_SOURCES_DIR = ROOT_DIR / "data" / "sources" / "leyes_originales"


def ensure_runtime_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LAW_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
