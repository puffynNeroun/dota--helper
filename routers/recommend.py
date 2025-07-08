from fastapi import APIRouter, HTTPException, Query, Request
from models.types import DraftInput, RecommendationResponse
from services.logic import generate_recommendation
from services.openai_generator import generate_openai_recommendation
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter

import logging

router = APIRouter(
    prefix="/api",
    tags=["recommendation"]
)

limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="🎯 Рекомендация героя и билда для текущего драфта",
    response_description="Предложение героев, стартовых предметов и билдов с учётом линии"
)
@limiter.limit("5/minute")  # Ограничение: 5 запросов в минуту с одного IP
async def recommend_team(
    request: Request,
    draft: DraftInput,
    use_openai: bool = Query(
        default=True,
        description="Использовать ли AI (OpenAI) для генерации рекомендаций"
    )
):

    client_ip = get_remote_address(request)
    logging.info(f"Запрос от IP {client_ip} | use_openai: {use_openai}")

    try:
        logging.info("Получен драфт: %s", draft.dict())

        if use_openai:
            logging.info("Генерация через OpenAI")
            try:
                result = generate_openai_recommendation(draft)
            except Exception as ai_error:
                logging.warning("Ошибка OpenAI: %s", ai_error)
                logging.info("Переход на мета-логику")
                result = generate_recommendation(draft)
        else:
            logging.info("Генерация через мета-логику")
            result = generate_recommendation(draft)

        logging.info("Рекомендация сформирована")
        return result

    except ValueError as ve:
        logging.warning("Ошибка валидации: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))

    except FileNotFoundError as fnf:
        logging.error("Файл не найден: %s", fnf)
        raise HTTPException(status_code=500, detail="Файл с мета-данными не найден.")

    except Exception as e:
        logging.critical("Критическая ошибка: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера.")
