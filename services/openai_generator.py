# services/openai_generator.py

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List
from functools import lru_cache

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
    fallback_detailed_build,
)
from services.prompt_builder import PromptBuilder
from services.cache import load_build_from_cache, save_build_to_cache

SCHEMA_PATH = Path(__file__).parent.parent / "models" / "openai_response_schema.json"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
TEMPERATURE = float(os.getenv("OPENAI_TEMP", "0.7"))
MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))

logger = logging.getLogger(__name__)

# ---------------------------- Helpers ----------------------------

def extract_json_block(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text.strip(), re.DOTALL)
    return match.group(1) if match else text.strip()


@lru_cache()
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.startswith("sk-"):
        raise ValueError("❌ OPENAI_API_KEY is missing or invalid.")
    logger.info(f"🔑 OpenAI key detected: {api_key[:10]}... (length: {len(api_key)})")
    return OpenAI(api_key=api_key)


def validate_openai_json(data: Dict) -> bool:
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        validate(instance=data, schema=schema)
        return True
    except ValidationError as ve:
        logger.warning(f"⚠️ OpenAI response schema validation failed: {ve.message}")
        logger.debug(json.dumps(data, indent=2, ensure_ascii=False))
        return False


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
        return response.choices[0].message if response.choices else None
    except Exception as e:
        logger.exception(f"💥 OpenAI error: {e}")
        return None

# ---------------------------- Recommendation ----------------------------

def generate_openai_recommendation(draft: DraftInput) -> RecommendationResponse:
    builder = PromptBuilder()
    prompt = builder.build_recommend_prompt(draft)

    response = chat_completion(system_msg=builder.templates["base"], user_msg=prompt)
    if not response:
        return generate_recommendation(draft)

    content = extract_json_block(response.content)
    if content.lower() in ("null", "none", ""):
        return generate_recommendation(draft)

    try:
        parsed = json.loads(content)
        if validate_openai_json(parsed):
            return RecommendationResponse(**parsed)
    except Exception as e:
        logger.exception(f"💀 Recommendation JSON parsing failed: {e}")

    return generate_recommendation(draft)

# ---------------------------- Build Options ----------------------------

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
        "Сгенерируй 3-5 билдов (BuildVariant) с полями: id, label, description.\n"
        "Ответ строго в JSON-массиве."
    )

    response = chat_completion(
        system_msg="Ты помощник Dota 2. Твоя задача — предлагать билд-опции.",
        user_msg=user_prompt,
        max_tokens=1000
    )

    if not response:
        return fallback_build_options(None)

    try:
        builds = json.loads(extract_json_block(response.content))
        return [BuildVariant(**b) for b in builds]
    except Exception as e:
        logger.exception(f"❌ Build options parse error: {e}")
        return fallback_build_options(None)

# ---------------------------- Detailed Build ----------------------------

def normalize_openai_detailed_response(parsed: Dict) -> Dict:
    if isinstance(parsed.get("builds"), list) and parsed["builds"]:
        first = parsed["builds"][0]
        for key in [
            "starting_items", "early_game_items", "mid_game_items", "late_game_items", "situational_items",
            "skill_build", "talents", "game_plan", "item_explanations"
        ]:
            parsed.setdefault(key, first.get(key))
    return parsed


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
        logger.info(f"✅ Cache hit for build_id={selected_build_id}")
        return DetailedBuildResponse(**cached)

    user_prompt = (
        f"Герой: {hero}, Роль: {role}, Аспект: {aspect}\n"
        f"Билд: {selected_build_id}\n"
        f"Враги: {enemy_heroes}\n"
        f"Союзники: {ally_heroes}\n\n"
        "Сгенерируй DetailedBuildResponse с полями:\n"
        "- starting_items, early_game_items, mid_game_items, late_game_items, situational_items\n"
        "- skill_build, talents, game_plan, item_explanations\n"
        "- warnings, source='openai', builds=[]\n"
        "Ответ строго в JSON."
    )

    response = chat_completion(
        system_msg="Ты стратег в Dota 2. Возвращай подробный билд.",
        user_msg=user_prompt,
        max_tokens=1500
    )

    if not response:
        return fallback_detailed_build(hero, role, aspect, selected_build_id, enemy_heroes, ally_heroes)

    try:
        parsed = json.loads(extract_json_block(response.content))
        parsed = normalize_openai_detailed_response(parsed)
        parsed.setdefault("warnings", [])
        parsed.setdefault("source", "openai")
        parsed.setdefault("builds", [])

        if validate_openai_json(parsed):
            save_build_to_cache(selected_build_id, parsed)

        return DetailedBuildResponse(**parsed)

    except Exception as e:
        logger.exception(f"❌ Detailed build parsing failed: {e}")
        return fallback_detailed_build(hero, role, aspect, selected_build_id, enemy_heroes, ally_heroes)
