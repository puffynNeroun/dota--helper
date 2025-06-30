from fastapi import APIRouter, HTTPException
from models.types import DraftInput, RecommendationResponse
from services.logic import generate_recommendation

router = APIRouter(
    prefix="/api",
    tags=["recommendation"]
)

@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_team(draft: DraftInput):
    try:
        return generate_recommendation(draft)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации рекомендации: {str(e)}")
