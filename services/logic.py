import json
from pathlib import Path
from typing import List, Set

from models.types import DraftInput, RecommendationResponse, HeroSuggestion

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HEROES_PATH = DATA_DIR / "heroes.json"
META_PATH = DATA_DIR / "meta.json"


def load_valid_heroes() -> Set[str]:
    if not HEROES_PATH.exists():
        raise FileNotFoundError(f"Файл {HEROES_PATH} не найден. Обнови его через скрипт meta_loader.")
    with open(HEROES_PATH, encoding="utf-8") as f:
        return {hero["name"].lower() for hero in json.load(f)}


def load_meta_data() -> dict:
    if not META_PATH.exists():
        raise FileNotFoundError(f"Файл {META_PATH} не найден. Запусти meta_loader.py.")
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)


def clean_heroes(raw_list: List[str], valid_heroes: Set[str], max_len: int, role: str) -> List[str]:
    cleaned = []
    for h in raw_list:
        h_clean = h.lower()
        if h_clean in valid_heroes and h_clean not in cleaned:
            cleaned.append(h_clean)
        else:
            print(f"⚠️ Герой '{h}' не распознан и исключён из списка {role}.")
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
    target_role = role_map.get(user_role.lower(), user_role)

    for name, info in meta.items():
        if name.startswith("_") or name in excluded:
            continue
        if target_role.lower() in [r.lower() for r in info.get("roles", [])]:
            suggestions.append({
                "name": name,
                "score": info.get("winrate", 0),
                "reason": f"Высокий винрейт для роли {user_role}"
            })

    top = sorted(suggestions, key=lambda h: h["score"], reverse=True)[:3]
    return [HeroSuggestion(**s) for s in top]


def generate_recommendation(draft: DraftInput) -> RecommendationResponse:
    valid_heroes = load_valid_heroes()
    meta = load_meta_data()
    warnings = []

    clean_enemy = clean_heroes(draft.enemy_heroes, valid_heroes, 5, "врагов")
    clean_ally = clean_heroes(draft.ally_heroes, valid_heroes, 4, "союзников")

    user_hero = draft.user_hero.lower() if draft.user_hero else None
    if user_hero and user_hero not in valid_heroes:
        warnings.append(f"⚠️ Герой '{user_hero}' не найден в базе. Игнорируется.")
        user_hero = None

    excluded_heroes = set(clean_enemy + clean_ally)
    if user_hero:
        excluded_heroes.add(user_hero)

    suggestions = recommend_by_meta(draft.user_role, excluded_heroes, meta) if not user_hero else []

    if not suggestions and not user_hero:
        warnings.append("⚠️ Не удалось подобрать героев по мета-данным и роли.")

    return RecommendationResponse(
        suggested_heroes=suggestions,
        lane_opponents=clean_enemy[:2],
        starting_items=["tango", "branches", "circlet"],
        build_easy=["boots", "witch_blade", "aghanims_scepter"],
        build_even=["boots", "kaya", "bkb"],
        build_hard=["boots", "euls", "ghost_scepter"],
        warnings=warnings
    )
