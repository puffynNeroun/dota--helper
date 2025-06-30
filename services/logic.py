import json
import logging
from pathlib import Path
from typing import List, Set

from models.types import DraftInput, RecommendationResponse, HeroSuggestion

# Настройка логгера
logger = logging.getLogger(__name__)

# Пути к данным
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HEROES_PATH = DATA_DIR / "heroes.json"
META_PATH = DATA_DIR / "meta.json"

# === Загрузка списка допустимых героев ===
def load_valid_heroes() -> Set[str]:
    if not HEROES_PATH.exists():
        raise FileNotFoundError(f"Файл {HEROES_PATH} не найден. Обнови его через скрипт meta_loader.")
    with open(HEROES_PATH, encoding="utf-8") as f:
        return {hero["name"].lower() for hero in json.load(f)}

# === Загрузка мета-данных ===
def load_meta_data() -> dict:
    if not META_PATH.exists():
        raise FileNotFoundError(f"Файл {META_PATH} не найден. Запусти meta_loader.py.")
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)

# === Очистка и валидация списков героев ===
def clean_heroes(raw_list: List[str], valid_heroes: Set[str], max_len: int, role: str) -> List[str]:
    cleaned = []
    for h in raw_list:
        h_clean = h.lower()
        if h_clean in valid_heroes and h_clean not in cleaned:
            cleaned.append(h_clean)
        else:
            logger.warning(f"⚠️ Герой '{h}' не распознан и исключён из списка {role}.")
    return cleaned[:max_len]

# === Подбор героев по мете и роли ===
def recommend_by_meta(user_role: str, excluded: Set[str], meta: dict) -> List[HeroSuggestion]:
    role_map = {
        "carry": ["Carry"],
        "mid": ["Nuker"],
        "offlane": ["Initiator", "Durable"],
        "pos4": ["Support", "Disabler"],
        "pos5": ["Support", "Disabler"],
    }

    normalized_role = user_role.strip().lower()
    target_roles = role_map.get(normalized_role)

    if not target_roles:
        logger.warning(f"⚠️ Роль '{user_role}' не распознана. Подбор невозможен.")
        return []

    logger.info(f"🎯 Подбор героев для клиентской роли '{normalized_role}' через: {target_roles}")

    suggestions = []
    for name, info in meta.items():
        if name.startswith("_") or name in excluded:
            continue

        hero_roles = [r.lower() for r in info.get("roles", [])]
        if any(role.lower() in hero_roles for role in target_roles):
            suggestions.append({
                "name": name,
                "score": info.get("winrate", 0),
                "reason": f"Рекомендован для роли {normalized_role}"
            })

    top = sorted(suggestions, key=lambda h: h["score"], reverse=True)[:3]
    return [HeroSuggestion(**s) for s in top]

# === Генерация полной рекомендации ===
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

    suggestions = []
    if not user_hero:
        suggestions = recommend_by_meta(draft.user_role, excluded_heroes, meta)

        if not suggestions:
            # Fallback: выбираем топ-3 героев по винрейту
            fallback = sorted(
                [
                    {"name": k, "score": v.get("winrate", 0), "reason": "Лучший винрейт вне зависимости от роли"}
                    for k, v in meta.items()
                    if k not in excluded_heroes and not k.startswith("_")
                ],
                key=lambda h: h["score"],
                reverse=True
            )[:3]
            suggestions = [HeroSuggestion(**h) for h in fallback]
            warnings.append("⚠️ Не удалось подобрать героев по роли — показаны лучшие по винрейту.")

    return RecommendationResponse(
        suggested_heroes=suggestions,
        lane_opponents=clean_enemy[:2],
        starting_items=["tango", "branches", "circlet"],
        build_easy=["boots", "witch_blade", "aghanims_scepter"],
        build_even=["boots", "kaya", "bkb"],
        build_hard=["boots", "euls", "ghost_scepter"],
        warnings=warnings
    )
