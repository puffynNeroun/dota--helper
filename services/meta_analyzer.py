from fastapi import APIRouter, HTTPException, Query, Request
from models.types import DraftInput, RecommendationResponse
from services.logic import generate_recommendation
from services.openai_generator import generate_openai_recommendation
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter

import logging

# === Настройка логгера ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/api",
    tags=["recommendation"]
)

# === Ограничение по IP ===
limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    response_model_exclude_none=True,
    summary="🎯 Рекомендация героя и билда для текущего драфта",
    description=(
        "Анализирует текущий драфт: союзники, противники, роль и аспект. "
        "Возвращает наиболее подходящего героя, билд, стартовые предметы, стратегию по таймингам, таланты и пояснения. "
        "На основе открытых данных (Dotabuff, Pro Tracker и др.), адаптированных под текущую ситуацию."
    ),
    response_description="Подробная рекомендация с билдом и планом игры"
)
@limiter.limit("5/minute")
async def recommend_team(
    request: Request,
    draft: DraftInput,
    use_openai: bool = Query(
        default=True,
        description="Использовать ли OpenAI для интеллектуальной адаптации билдов"
    )
):
    client_ip = get_remote_address(request)
    logger.info(f"[{client_ip}] Запрос на рекомендацию | OpenAI={use_openai}")

    try:
        logger.info("📥 Драфт: %s", draft.model_dump())

        if use_openai:
            logger.info("🧠 Используется OpenAI как адаптер билдов")
            try:
                result = generate_openai_recommendation(draft)
            except Exception as ai_error:
                logger.warning("⚠️ OpenAI упал: %s", ai_error)
                logger.info("⛑️ Переход на fallback-логику")
                result = generate_recommendation(draft)
        else:
            logger.info("🔧 Используется fallback логика без OpenAI")
            result = generate_recommendation(draft)

        logger.info("✅ Рекомендация готова")
        return result

    except ValueError as ve:
        logger.warning("❌ Неверные входные данные: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))

    except FileNotFoundError as fnf:
        logger.error("📂 meta.json не найден: %s", fnf)
        raise HTTPException(status_code=500, detail="Файл с мета-данными не найден.")

    except Exception as e:
        logger.critical("🔥 Необработанная ошибка: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера.")
