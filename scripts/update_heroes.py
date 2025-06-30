import json
import requests
from pathlib import Path
import argparse
import sys

# === Константы ===
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "heroes.json"
API_URL = "https://api.opendota.com/api/heroes"


# === Загрузка данных с OpenDota ===
def fetch_heroes():
    print("📥 Загружаем список героев с OpenDota...")
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Ошибка при получении данных: {e}")
        sys.exit(1)

    data = response.json()
    return [
        {
            "name": hero["name"].lower().removeprefix("npc_dota_hero_"),
            "localized_name": hero["localized_name"]
        }
        for hero in data
    ]


# === Сохранение в файл ===
def save_heroes(data, force: bool):
    if OUTPUT_FILE.exists() and not force:
        print(f"⚠️  Файл уже существует: {OUTPUT_FILE}. Используй --force для перезаписи.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Герои успешно сохранены в {OUTPUT_FILE}")


# === Точка входа ===
def main():
    parser = argparse.ArgumentParser(description="Обновить heroes.json из OpenDota API")
    parser.add_argument("--force", action="store_true", help="Перезаписать heroes.json даже если он уже существует")
    args = parser.parse_args()

    heroes = fetch_heroes()
    save_heroes(heroes, args.force)


if __name__ == "__main__":
    main()
