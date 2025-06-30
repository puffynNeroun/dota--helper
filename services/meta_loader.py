import json
import requests
from pathlib import Path
from datetime import datetime

# === Пути и константы ===
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "meta.json"
OPENDOTA_HERO_STATS_URL = "https://api.opendota.com/api/heroStats"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MetaCollector/1.0; +https://yourdomain.dev)"
}

# === Получение мета-данных через OpenDota ===
def fetch_meta_from_opendota() -> list[dict]:
    print("📥 Загружаем мета-данные героев с OpenDota...")
    try:
        response = requests.get(OPENDOTA_HERO_STATS_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return data
        print("⚠️ Получены пустые или некорректные данные от OpenDota.")
        return []
    except requests.RequestException as e:
        print(f"❌ Ошибка при получении данных с OpenDota: {e}")
        return []

# === Обработка и форматирование мета-данных ===
def transform_heroes(raw_heroes: list[dict]) -> dict:
    result = {}
    for hero in raw_heroes:
        short = hero["name"].lower().removeprefix("npc_dota_hero_")
        result[short] = {
            "localized_name": hero.get("localized_name", short),
            "roles": hero.get("roles", []),
            "winrate": round(hero["pro_win"] / hero["pro_pick"], 3) if hero.get("pro_pick") else 0,
            "pick_rate": round(hero.get("pro_pick", 0) / 1000, 3),
            "ban_rate": round(hero.get("pro_ban", 0) / 1000, 3),
        }

    result = dict(sorted(result.items(), key=lambda x: -x[1]["winrate"]))
    result["_last_updated"] = datetime.utcnow().isoformat()
    return result

# === Сохранение мета-данных в файл ===
def save_meta(data: dict, force: bool = True):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ meta.json успешно сохранён в {OUTPUT_PATH}")

# === CLI: ручной запуск ===
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Обновить meta.json с мета-данными героев")
    parser.add_argument("--force", action="store_true", help="Перезаписать файл, даже если он уже существует")
    args = parser.parse_args()

    raw = fetch_meta_from_opendota()
    if raw:
        meta = transform_heroes(raw)
        save_meta(meta, force=args.force)
    else:
        print("⚠️ Не удалось обновить meta.json — данные не получены.")

# === Использование по расписанию ===
def fetch_and_save_meta() -> bool:
    raw = fetch_meta_from_opendota()
    if raw:
        meta = transform_heroes(raw)
        save_meta(meta)
        return True
    return False

if __name__ == "__main__":
    main()

