from dotenv import load_dotenv
load_dotenv()

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from openai import OpenAI, OpenAIError, APIError
from jsonschema import validate, ValidationError

from models.types import DraftInput, RecommendationResponse
from services.logic import generate_recommendation

# ==== Константы ====
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "ai_prompt.txt"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "models" / "openai_response_schema.json"

MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
TEMPERATURE = float(os.getenv("OPENAI_TEMP", "0.7"))
MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))
API_KEY = os.getenv("OPENAI_API_KEY")

client: Optional[OpenAI] = None


def is_valid_api_key(key: Optional[str]) -> bool:
    return key and key.startswith("sk-") and len(key) > 20


def init_openai_client() -> Optional[OpenAI]:
    if not is_valid_api_key(API_KEY):
        logging.warning("❌ OPENAI_API_KEY не установлен или некорректен.")
        return None
    return OpenAI(api_key=API_KEY)


def load_base_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Файл промпта не найден: {PROMPT_PATH}")
    with PROMPT_PATH.open("r", encoding="utf-8") as f:
        return f.read().strip()


def format_draft_input(draft: DraftInput) -> Dict:
    return {
        "role": draft.user_role,
        "user_hero": draft.user_hero,
        "allies": draft.ally_heroes or [],
        "enemies": draft.enemy_heroes or [],
    }


def build_user_prompt(draft: DraftInput, input_data: Dict) -> str:
    base = (
        f"Вот входные данные драфта:\n{input_data}\n"
        "Проанализируй выбранного героя и его роль в матче. "
        "Подбери оптимальный стиль игры (например, маг, физический урон, контроль, пуш и т.д.).\n"
        "Сгенерируй от 2 до 4 билдов, каждый из которых должен содержать:\n"
        "- название (name)\n"
        "- краткое описание (description)\n"
        "- оценку шанса победы (winrate_score)\n"
        "- сборку предметов (build)\n"
        "- стартовые предметы (starting_items)\n"
        "- прокачку скиллов (skill_build)\n"
        "- таланты (talents)\n"
        "- план на игру (game_plan)\n"
        "- пояснения к предметам (item_notes)\n"
        "Также добавь ключ 'recommended_aspect' — маг, пуш, инициатор и т.п.\n"
        "Ответ СТРОГО в корректном JSON-формате."
    )
    if draft.user_hero:
        return base + "\nПользователь уже выбрал героя — не предлагай других. Формируй билд только для него."
    else:
        return base + "\nЕсли герой не выбран — предложи наиболее подходящего, но тоже сформируй билд."


def validate_openai_json(data: Dict) -> bool:
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        validate(instance=data, schema=schema)
        return True
    except ValidationError as ve:
        logging.warning("⚠️ Ответ OpenAI не прошёл валидацию схемы: %s", ve.message)
        return False
    except Exception as e:
        logging.error("💥 Ошибка при валидации схемы: %s", e)
        return False


def generate_openai_recommendation(draft: DraftInput) -> RecommendationResponse:
    global client
    if not client:
        client = init_openai_client()

    if not client:
        logging.warning("⚠️ OpenAI client не инициализирован. Используется fallback логика.")
        return generate_recommendation(draft)

    prompt = load_base_prompt()
    input_data = format_draft_input(draft)
    user_prompt = build_user_prompt(draft, input_data)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        content = response.choices[0].message.content.strip()
        logging.info("📩 Ответ OpenAI: %s", content[:500])

        parsed = json.loads(content)

        if not validate_openai_json(parsed):
            logging.warning("❌ Ответ от OpenAI не соответствует схеме. Используется fallback.")
            return generate_recommendation(draft)

        return RecommendationResponse(**parsed)

    except json.JSONDecodeError as je:
        logging.error("❌ JSON ошибка при парсинге: %s", je)
        logging.debug("Сырой ответ OpenAI:\n%s", content)
        return generate_recommendation(draft)

    except APIError as ae:
        logging.exception("🧨 API ошибка OpenAI: %s", ae)
        return generate_recommendation(draft)

    except OpenAIError as oe:
        logging.exception("💥 Общая ошибка OpenAI: %s", oe)
        return generate_recommendation(draft)

    except Exception as e:
        logging.exception("💀 Неизвестная ошибка при генерации через OpenAI.")
        return generate_recommendation(draft)
