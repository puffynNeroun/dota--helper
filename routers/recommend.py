from fastapi import APIRouter, HTTPException
from models.types import DraftInput, RecommendationResponse
from services.logic import generate_recommendation
import logging

router = APIRouter(
    prefix="/api",
    tags=["recommendation"]
)

@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="🎯 Рекомендация героя и билда для текущего драфта",
    response_description="Предложение героев, стартовых предметов и билдов с учётом линии"
)
async def recommend_team(draft: DraftInput):
    """
    🧠 Анализирует текущий драфт в Dota 2 и предлагает оптимального героя и билд.

    ### Обязательные поля:
    - **user_role**: Ваша роль (например, Mid, Support, Carry и т.д.)

    ### Необязательные поля:
    - **user_hero**: Герой, за которого вы планируете играть
    - **ally_heroes**: Список героев вашей команды (до 4)
    - **enemy_heroes**: Список героев соперников (до 5)

    ### Что возвращается:
    - Топ-3 героя, рекомендуемых системой (если не выбран пользовательский герой)
    - Противники по линии (2 первых врага)
    - Стартовые предметы
    - Билды для лёгкой, равной и тяжёлой игры
    - Предупреждения по входным данным
    """
    try:
        logging.info("🔍 Получен драфт: %s", draft.dict())
        result = generate_recommendation(draft)
        logging.info("✅ Сформирована рекомендация: %s", result)
        return result

    except ValueError as ve:
        logging.warning("⚠️ Ошибка валидации входных данных: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))

    except FileNotFoundError as fnf:
        logging.error("📁 Отсутствует файл данных: %s", fnf)
        raise HTTPException(status_code=500, detail="Файл с мета-данными не найден. Повторите позже.")

    except Exception as e:
        logging.critical("💥 Неожиданная ошибка при генерации рекомендации: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при генерации рекомендации.")
