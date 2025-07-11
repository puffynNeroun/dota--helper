import json
import logging
from pathlib import Path
from typing import List, Set

from models.types import (
    DraftInput,
    RecommendationResponse,
    HeroSuggestion,
    BuildPlan,
    BuildVariant,
    BuildOptionsRequest,
    BuildOptionsResponse,
    DetailedBuildRequest,
    DetailedBuildResponse,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HEROES_PATH = DATA_DIR / "heroes.json"
META_PATH = DATA_DIR / "meta.json"


def load_valid_heroes() -> Set[str]:
    if not HEROES_PATH.exists():
        raise FileNotFoundError(f"Файл {HEROES_PATH} не найден. Обнови через meta_loader.")
    with open(HEROES_PATH, encoding="utf-8") as f:
        return {hero["name"].lower() for hero in json.load(f)}


def load_meta_data() -> dict:
    if not META_PATH.exists():
        raise FileNotFoundError(f"Файл {META_PATH} не найден. Запусти meta_loader.")
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)


def clean_heroes(raw: List[str], valid: Set[str], max_len: int, role: str) -> List[str]:
    result = []
    for h in raw:
        h_l = h.lower()
        if h_l in valid and h_l not in result:
            result.append(h_l)
        else:
            logger.warning(f"⚠️ Герой '{h}' не найден и исключён из списка {role}.")
    return result[:max_len]


def recommend_by_meta(user_role: str, excluded: Set[str], meta: dict) -> List[HeroSuggestion]:
    role_map = {
        "carry": ["Carry"],
        "mid": ["Nuker"],
        "safelane": ["Carry"],
        "offlane": ["Initiator", "Durable"],
        "support": ["Support", "Disabler"],
        "hard support": ["Support", "Disabler"],
    }
    role_norm = user_role.strip().lower()
    mapped = role_map.get(role_norm)
    if not mapped:
        logger.warning(f"⚠️ Роль '{user_role}' не распознана.")
        return []

    logger.info(f"🎯 Поиск героев по ролям {mapped}")
    candidates = []
    for name, info in meta.items():
        if name.startswith("_") or name in excluded:
            continue
        hero_roles = [r.lower() for r in info.get("roles", [])]
        if any(r.lower() in hero_roles for r in mapped):
            candidates.append({
                "name": name,
                "score": info.get("winrate", 0),
                "reason": f"Рекомендован для роли {role_norm}"
            })

    top = sorted(candidates, key=lambda h: h["score"], reverse=True)[:3]
    return [HeroSuggestion(**s) for s in top]


def generate_simple_build(user_hero: str) -> List[BuildPlan]:
    return [
        BuildPlan(
            name="Базовый билд",
            description=f"Стандартный билд на {user_hero.title()}",
            winrate_score=0.52,
            highlight=True,
            build=["boots", "magic_wand", "kaya", "bkb"],
            starting_items=["tango", "branches", "faerie_fire"],
            skill_build=["Q", "E", "Q", "W", "Q", "R", "Q", "W", "W", "W"],
            talents={
                "10": "+20 урона",
                "15": "+10% spell amp",
                "20": "+0.3s stun",
                "25": "+25% magic resistance"
            },
            game_plan={
                "early_game": "Контроль линии и харас врагов.",
                "mid_game": "Подключение к тимфайтам и пуш лайнов.",
                "late_game": "Решающие бои и контроль ключевых героев."
            },
            item_notes={
                "kaya": "Увеличивает магический урон.",
                "bkb": "Необходим против магов и дизейблов."
            }
        )
    ]


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

    excluded = set(clean_enemy + clean_ally)
    if user_hero:
        excluded.add(user_hero)

    suggestions, builds, source = [], [], None

    if not user_hero:
        suggestions = recommend_by_meta(draft.user_role, excluded, meta)
        source = "openai"

        if not suggestions:
            fallback = sorted(
                [
                    {"name": name, "score": info.get("winrate", 0), "reason": "Лучший винрейт вне зависимости от роли"}
                    for name, info in meta.items()
                    if name not in excluded and not name.startswith("_")
                ],
                key=lambda h: h["score"],
                reverse=True
            )[:3]
            suggestions = [HeroSuggestion(**f) for f in fallback]
            warnings.append("⚠️ Не удалось подобрать героев по роли — показаны лучшие по винрейту.")
            source = "fallback"
    else:
        builds = generate_simple_build(user_hero)
        source = "fallback"

    return RecommendationResponse(
        recommended_aspect=draft.aspect or "общий",
        builds=builds,
        suggested_heroes=suggestions,
        lane_opponents=clean_enemy[:2],
        starting_items=["tango", "branches", "circlet"],
        build_easy=["boots", "witch_blade", "aghanims_scepter"],
        build_even=["boots", "kaya", "bkb"],
        build_hard=["boots", "euls", "ghost_scepter"],
        warnings=warnings,
        source=source
    )


def fallback_build_options(_: BuildOptionsRequest) -> List[BuildVariant]:
    return [
        BuildVariant(id="default_magic", label="Маг", description="Фокус на AoE урон и контроль"),
        BuildVariant(id="default_right_click", label="Физ. урон", description="Через быстрый урон и криты"),
        BuildVariant(id="default_aura", label="Аура и поддержка", description="Через предметы ауры и командный импакт")
    ]


def fallback_detailed_build(
    hero: str,
    role: str,
    aspect: str,
    enemy_lane_heroes: List[str],
    team_heroes: List[str],
    selected_build_id: str
) -> DetailedBuildResponse:
    return DetailedBuildResponse(
        starting_items=["tango", "mantle_of_intelligence", "circlet"],
        early_game_items=["boots", "null_talisman"],
        mid_game_items=["aether_lens", "kaya"],
        late_game_items=["bkb", "octarine_core"],
        situational_items=["ghost_scepter", "glimmer_cape"],
        skill_build=["Q", "E", "Q", "W", "Q", "R", "Q", "W", "W", "W", "R", "E", "E", "E", "Stats", "R"],
        talents={"10": "+15% spell amp", "15": "+100 cast range"},
        game_plan={
            "early_game": "Держись позади, фарми с безопасной дистанции.",
            "mid_game": "Контроль карты, сплитпуш и поддержка тимфайтов.",
            "late_game": "Максимальный импакт за счёт позиционки и предметов контроля."
        },
        item_explanations={
            "bkb": "Обязателен против магического контроля.",
            "aether_lens": "Повышает дальность применения способностей.",
            "octarine_core": "Снижение КД и выживаемость."
        },
        warnings=["⚠️ Данные сгенерированы fallback-логикой, не основаны на OpenAI."],
        source="fallback"
    )
