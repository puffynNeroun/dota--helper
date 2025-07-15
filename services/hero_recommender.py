import logging
from models.types import DraftInput, RecommendationResponse
from services.logic import generate_recommendation
from services.openai_generator import generate_openai_recommendation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def recommend_hero_and_build(draft: DraftInput, use_openai: bool = True) -> RecommendationResponse:


    logger.info("📥 Новый запрос: %s", draft.model_dump())
    logger.info("🧠 OpenAI режим: %s", use_openai)

    try:
        if use_openai:
            try:
                logger.info("🔗 Генерация через OpenAI...")
                response = generate_openai_recommendation(draft)
                logger.info("✅ Успешный ответ от OpenAI.")
                return response

            except Exception as e:
                logger.warning("⚠️ OpenAI недоступен или дал ошибку: %s", e)
                logger.info("↩️ Переход на fallback-логику.")

        logger.info("🛠️ Генерация через fallback-логику...")
        response = generate_recommendation(draft)
        logger.info("✅ Успешная генерация через fallback.")
        return response

    except Exception as critical_error:
        logger.critical("🔥 Критическая ошибка генерации рекомендации: %s", critical_error, exc_info=True)
        raise
