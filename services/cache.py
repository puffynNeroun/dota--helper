import json
from pathlib import Path
from typing import Optional, Dict

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

def _get_cache_path(build_id: str) -> Path:
    return CACHE_DIR / f"{build_id}.json"

def save_build_to_cache(build_id: str, data: Dict) -> None:
    path = _get_cache_path(build_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_build_from_cache(build_id: str) -> Optional[Dict]:
    path = _get_cache_path(build_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
