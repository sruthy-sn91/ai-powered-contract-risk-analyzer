from pathlib import Path
from backend.app.core.config import settings

def _ensure_dir(path: str, name: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(
            f"{name} not found at: {p}\n"
            f"Set {name}_DIR in .env or place data under ./data/{name.lower()}"
        )
    return p

def acord_dir() -> Path:
    return _ensure_dir(settings.ACORD_DIR, "ACORD")

def cuad_dir() -> Path:
    return _ensure_dir(settings.CUAD_DIR, "CUAD")

def policies_dir() -> Path:
    return _ensure_dir(settings.POLICIES_DIR, "POLICIES")

def index_dir() -> Path:
    p = Path(settings.INDEX_DIR).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p
