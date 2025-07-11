import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List
from functools import lru_cache

# === Грузим .env ===
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from jsonschema import validate, ValidationError

from models.types import (
    DraftInput,
    RecommendationResponse,
    DetailedBuildResponse,
    BuildVariant,
)
from services.logic import (
    generate_recommendation,
    fallback_build_options,
    fallback_detailed_build,
)
from services.prompt_builder import PromptBuilder
from services.cache import load_build_from_cache, save_build_to_cache

# === Константы ===
SCHEMA_PATH = Path(__file__).parent.parent / "models" / "openai_response_schema.json"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
TEMPERATURE = float(os.getenv("OPENAI_TEMP", "0.7"))
MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))

# === Логирование ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# === Добавь в начало: ===
def extract_json_block(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text.strip(), re.DOTALL)
    return match.group(1) if match else text.strip()


# === Валидация API ключа ===
def is_valid_api_key(key: Optional[str]) -> bool:
    return bool(re.fullmatch(r"sk-\w{10,}|sk-proj-\w{10,}", key or ""))

@lru_cache()
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    def is_flexible_key(key: Optional[str]) -> bool:
        if not key:
            return False
        return (
            key.startswith("sk-") and len(key) > 20
        )

    if not is_flexible_key(api_key):
        logging.error("❌ OPENAI_API_KEY не установлен или некорректен.")
        logging.debug(f"🔍 Полученный ключ: {api_key}")
        raise ValueError("❌ OPENAI_API_KEY не установлен или некорректен.")

    logging.info(f"🔑 OpenAI client initialized with key prefix: {api_key[:10]}... (длина: {len(api_key)})")
    return OpenAI(api_key=api_key)


# === Валидация JSON по схеме ===
def validate_openai_json(data: Dict) -> bool:
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)

        allowed_keys = set(schema["properties"].keys())
        data = {k: v for k, v in data.items() if k in allowed_keys}
        validate(instance=data, schema=schema)
        return True
    except ValidationError as ve:
        logging.warning("⚠️ Ответ OpenAI не прошёл валидацию схемы: %s", ve.message)
        logging.debug("Невалидный JSON: %s", json.dumps(data, indent=2, ensure_ascii=False))
        return False
    except Exception as e:
        logging.error(f"💥 Ошибка при валидации схемы: {e}")
        return False

# === Командный чату ===
def chat_completion(system_msg: str, user_msg: str, max_tokens: int = MAX_TOKENS) -> Optional[ChatCompletionMessage]:
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
        )
        if response.choices:
            return response.choices[0].message
        logging.warning("⚠️ Пустой список choices от OpenAI.")
        return None
    except Exception as e:
        logging.exception(f"💥 Ошибка при обращении к OpenAI: {e}")
        return None

# === /recommend ===
def generate_openai_recommendation(draft: DraftInput) -> RecommendationResponse:
    builder = PromptBuilder()
    prompt_text = builder.build_recommend_prompt(draft)

    response = chat_completion(
        system_msg=builder.templates["base"],
        user_msg=prompt_text
    )

    if not response:
        logging.warning("⚠️ OpenAI не ответил, fallback.")
        return generate_recommendation(draft)

    content = extract_json_block(response.content)
    if not content or content.lower() in ("null", "none"):
        logging.warning("⚠️ Пустой или невалидный ответ от OpenAI. fallback.")
        return generate_recommendation(draft)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as jde:
        logging.error(f"🧨 JSONDecodeError: {jde} | Raw content: {content}")
        return generate_recommendation(draft)

    if not validate_openai_json(parsed):
        logging.warning("❌ Ответ невалиден. fallback.")
        return generate_recommendation(draft)

    try:
        return RecommendationResponse(**parsed)
    except Exception as e:
        logging.exception(f"💀 Ошибка создания RecommendationResponse: {e}")
        return generate_recommendation(draft)


# === /builds/options ===
def generate_build_options(
    hero: str,
    role: str,
    aspect: str,
    enemy_lane_heroes: List[str]
) -> List[BuildVariant]:
    user_prompt = (
        f"Герой: {hero}\n"
        f"Роль: {role}\n"
        f"Аспект: {aspect}\n"
        f"Враги на линии: {enemy_lane_heroes}\n\n"
        "Сгенерируй 3-5 билдов (BuildVariant), каждый с полями:\n"
        "- id (строка, уникальный идентификатор, например: \"build1\", \"b2\", \"custom-3\")\n"
        "- label (название билда)\n"
        "- description (описание билда)\n"
        "Ответ строго в JSON-массиве."
    )

    response = chat_completion(
        system_msg="Ты помощник Dota 2. Твоя задача — предлагать билд-опции.",
        user_msg=user_prompt,
        max_tokens=1000
    )

    if not response:
        return fallback_build_options(hero, role, aspect, enemy_lane_heroes)

    try:
        parsed = json.loads(extract_json_block(response.content))

        # Приведение id к строке
        for build in parsed:
            if "id" in build:
                build["id"] = str(build["id"])

        # Вернём список словарей, пригодных для сериализации
        return parsed


    except Exception as e:
        logging.exception(f"❌ Ошибка парсинга build options: {e}")
        return fallback_build_options(hero, role, aspect, enemy_lane_heroes)


# === /builds/detailed ===
def generate_detailed_build(
    hero: str,
    role: str,
    aspect: str,
    selected_build_id: str,
    enemy_heroes: List[str],
    ally_heroes: List[str]
) -> DetailedBuildResponse:
    cached = load_build_from_cache(selected_build_id)
    if cached:
        logging.info(f"✅ Используем кеш для build_id={selected_build_id}")
        return DetailedBuildResponse(**cached)

    user_prompt = (
        f"Герой: {hero}, Роль: {role}, Аспект: {aspect}\n"
        f"Выбранный билд: {selected_build_id}\n"
        f"Противники: {enemy_heroes}\n"
        f"Союзники: {ally_heroes}\n\n"
        "Сгенерируй подробный билд с:\n"
        "- starting_items, early_game_items, mid_game_items, late_game_items, situational_items\n"
        "- skill_build (Q/W/E/R/Stats)\n"
        "- talents (10/15/20/25 уровни)\n"
        "- game_plan (early/mid/late)\n"
        "- item_explanations\n"
        "- warnings\n"
        "- source: 'openai'\n"
        "- builds: обязательный массив билдов (может быть пустым)\n"
        "Ответ в JSON, без пояснений."
    )

    response = chat_completion(
        system_msg="Ты ассистент по стратегии Dota 2. Формируй билд-планы.",
        user_msg=user_prompt,
        max_tokens=1500
    )

    if not response:
        return fallback_detailed_build(hero, role, aspect, selected_build_id, enemy_heroes, ally_heroes)

    content = extract_json_block(response.content)
    try:
        parsed = json.loads(content)

        # Если OpenAI вложил всё в один из ключей (build / build1 / и т.п.)
        if isinstance(parsed, dict) and len(parsed) == 1 and isinstance(next(iter(parsed.values())), dict):
            build_data = next(iter(parsed.values()))
            parsed = build_data

        # Удаляем лишние поля, которых нет в схеме:
        for key in ["hero", "role", "aspect"]:
            parsed.pop(key, None)

        # Приводим warnings к List[str]
        if isinstance(parsed.get("warnings"), str):
            parsed["warnings"] = [parsed["warnings"]]
        elif isinstance(parsed.get("warnings"), dict):
            parsed["warnings"] = list(parsed["warnings"].values())

        # Устанавливаем поля по умолчанию
        parsed.setdefault("builds", [])
        parsed["source"] = "openai"

        # Валидация перед кешированием
        if validate_openai_json(parsed):
            save_build_to_cache(selected_build_id, parsed)

        return DetailedBuildResponse(**parsed)

    except Exception as e:
        logging.exception(f"❌ Ошибка detailed build JSON: {e} | Content: {content}")
        return fallback_detailed_build(hero, role, aspect, selected_build_id, enemy_heroes, ally_heroes)
