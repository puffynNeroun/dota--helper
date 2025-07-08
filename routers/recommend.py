from fastapi import APIRouter, HTTPException, Query, Request
from models.types import DraftInput, RecommendationResponse
from services.logic import generate_recommendation
from services.openai_generator import generate_openai_recommendation
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter

import logging

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/api",
    tags=["recommendation"]
)

# Инициализация лимитера (ограничение по IP)
limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    response_model_exclude_none=True,
    summary="🎯 Рекомендация героя и билда для текущего драфта",
    description=(
        "Анализирует текущий драфт с учётом героев противников, союзников и выбранной роли пользователя. "
        "Возвращает наиболее подходящий билд, героев, стартовые предметы, таланты и стратегию на игру."
    ),
    response_description="Подробная рекомендация по билду, героям и плану игры"
)
@limiter.limit("5/minute")
async def recommend_team(
    request: Request,
    draft: DraftInput,
    use_openai: bool = Query(
        default=True,
        description="Использовать ли OpenAI для генерации рекомендаций"
    )
):
    client_ip = get_remote_address(request)
    logger.info(f"[{client_ip}] Запрос получен | use_openai={use_openai}")

    try:
        logger.info("Получен драфт: %s", draft.model_dump())

        if use_openai:
            logger.info("Генерация рекомендаций через OpenAI")
            try:
                result = generate_openai_recommendation(draft)
            except Exception as ai_error:
                logger.warning("OpenAI ошибка: %s", ai_error)
                logger.info("Переход на fallback-логику")
                result = generate_recommendation(draft)
        else:
            logger.info("Генерация через fallback-логику")
            result = generate_recommendation(draft)

        logger.info("Рекомендация успешно сформирована")
        return result

    except ValueError as ve:
        logger.warning("Ошибка валидации входных данных: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))

    except FileNotFoundError as fnf:
        logger.error("Отсутствует файл с мета-данными: %s", fnf)
        raise HTTPException(status_code=500, detail="Файл с мета-данными не найден.")

    except Exception as e:
        logger.critical("Критическая ошибка: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера.")
