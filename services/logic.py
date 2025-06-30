import json
from pathlib import Path
from typing import List, Set

from models.types import DraftInput, RecommendationResponse, HeroSuggestion

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HEROES_PATH = DATA_DIR / "heroes.json"
META_PATH = DATA_DIR / "meta.json"


def load_valid_heroes() -> Set[str]:
    if not HEROES_PATH.exists():
        raise FileNotFoundError(f"Файл {HEROES_PATH} не найден. Обнови его с помощью скрипта.")
    with open(HEROES_PATH, encoding="utf-8") as f:
        data = json.load(f)
        return {hero["name"].lower() for hero in data}


def load_meta_data() -> dict:
    if not META_PATH.exists():
        raise FileNotFoundError(f"Файл {META_PATH} не найден. Запусти meta_loader.py.")
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)


def clean_heroes(raw_list: List[str], valid_heroes: Set[str], max_len: int, role: str) -> List[str]:
    cleaned = []
    for h in raw_list:
        h_clean = h.lower()
        if h_clean in valid_heroes:
            if h_clean not in cleaned:
                cleaned.append(h_clean)
        else:
            print(f"⚠️ Герой '{h}' не распознан и исключён из {role}.")
    return cleaned[:max_len]


def recommend_by_meta(user_role: str, excluded: Set[str], meta: dict) -> List[HeroSuggestion]:
    role_map = {
        "mid": "Midlaner",
        "safelane": "Carry",
        "offlane": "Offlaner",
        "support": "Support",
        "hard support": "Hard Support"
    }

    suggestions = []
    target_role = role_map.get(user_role.lower(), user_role.lower())

    for name, info in meta.items():
        if name in excluded:
            continue
        if target_role.lower() in [r.lower() for r in info.get("roles", [])]:
            suggestions.append({
                "name": name,
                "score": info.get("winrate", 0),
                "reason": f"Топ по винрейту для роли {user_role}"
            })

    # Сортировка по винрейту
    top = sorted(suggestions, key=lambda h: h["score"], reverse=True)[:3]
    return [HeroSuggestion(**s) for s in top]


def generate_recommendation(draft: DraftInput) -> RecommendationResponse:
    valid_heroes = load_valid_heroes()
    meta = load_meta_data()
    warnings = []

    clean_enemy = clean_heroes(draft.enemy_heroes, valid_heroes, max_len=5, role="врагов")
    clean_ally = clean_heroes(draft.ally_heroes, valid_heroes, max_len=4, role="союзников")

    user_hero = draft.user_hero.lower() if draft.user_hero else None
    if user_hero and user_hero not in valid_heroes:
        warnings.append(f"Ваш герой '{user_hero}' не найден в базе. Игнорируется.")
        user_hero = None

    excluded_heroes = set(clean_enemy + clean_ally)
    if user_hero:
        excluded_heroes.add(user_hero)

    suggestions = []
    if not user_hero:
        suggestions = recommend_by_meta(draft.user_role, excluded_heroes, meta)
        if not suggestions:
            warnings.append("⚠️ Не удалось подобрать героев по роли и мета-данным.")

    lane_opponents = clean_enemy[:2] if clean_enemy else []

    return RecommendationResponse(
        suggested_heroes=suggestions,
        lane_opponents=lane_opponents,
        starting_items=["tango", "branches", "circlet"],
        build_easy=["boots", "witch_blade", "aghanims_scepter"],
        build_even=["boots", "kaya", "bkb"],
        build_hard=["boots", "euls", "ghost_scepter"],
        warnings=warnings
    )
