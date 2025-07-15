import requests
import logging
from functools import lru_cache
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BASE_URL = "https://api.opendota.com/api"

# ======= Hero Mapping =======

@lru_cache(maxsize=1)
def get_hero_id_map() -> Dict[str, int]:
    """
    Получает отображение {normalized_name: id} из OpenDota.
    Пример: 'phantom_assassin' -> 44
    """
    try:
        response = requests.get(f"{BASE_URL}/heroes", timeout=10)
        response.raise_for_status()
        data = response.json()

        hero_map = {
            normalize_hero_name(hero["localized_name"]): hero["id"]
            for hero in data
        }
        logger.info(f"🗺️ Получена карта героев: {len(hero_map)} героев")
        return hero_map

    except Exception as e:
        logger.error(f"❌ Ошибка при получении карты героев: {e}")
        raise


@lru_cache(maxsize=1)
def get_id_to_hero_map() -> Dict[int, str]:
    """
    Инвертированное отображение {id: normalized_name}
    """
    hero_map = get_hero_id_map()
    return {v: k for k, v in hero_map.items()}


def normalize_hero_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("'", "")

# ======= Matchups & Counters =======

def get_counters(hero_id: int, limit: int = 10) -> List[Dict]:
    """
    Получает матчапы героя и возвращает топ-N героев, которых он контрит меньше всего (на которых он проигрывает).
    """
    try:
        response = requests.get(f"{BASE_URL}/heroes/{hero_id}/matchups", timeout=10)
        response.raise_for_status()
        data = response.json()

        # Добавляем win_rate на лету
        for item in data:
            if item["games_played"] > 0:
                item["win_rate"] = item["wins"] / item["games_played"] * 100
            else:
                item["win_rate"] = 0

        sorted_counters = sorted(data, key=lambda x: x["win_rate"])
        top_counters = sorted_counters[:limit]
        logger.info(f"📉 Получены худшие противники для героя ID={hero_id}")
        return top_counters

    except Exception as e:
        logger.error(f"❌ Ошибка при получении матчапов для героя ID={hero_id}: {e}")
        return []  # безопасно возвращаем пустой список

# ======= Utility =======

def get_hero_name_by_id(hero_id: int) -> Optional[str]:
    """
    Получает нормализованное имя героя по ID.
    """
    return get_id_to_hero_map().get(hero_id)


def get_hero_id_by_name(name: str) -> Optional[int]:
    """
    Получает ID героя по его нормализованному имени.
    """
    return get_hero_id_map().get(normalize_hero_name(name))
