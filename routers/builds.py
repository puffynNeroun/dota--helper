from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal
from services.openai_generator import generate_build_options, generate_detailed_build

router = APIRouter(
    prefix="/builds",
    tags=["Builds"]
)

# === Модели запроса и ответа ===

class BuildOptionsRequest(BaseModel):
    user_hero: str
    user_role: Literal["mid", "safelane", "offlane", "support", "hard support"]
    aspect: str
    enemy_lane_heroes: List[str]

class BuildVariant(BaseModel):
    id: str
    label: str
    description: str

class BuildOptionsResponse(BaseModel):
    builds: List[BuildVariant]

class DetailedBuildRequest(BaseModel):
    user_hero: str
    user_role: Literal["mid", "safelane", "offlane", "support", "hard support"]
    aspect: str
    selected_build_id: str
    enemy_heroes: List[str]
    ally_heroes: List[str]

class DetailedBuildResponse(BaseModel):
    starting_items: List[str]
    early_game_items: List[str]
    mid_game_items: List[str]
    late_game_items: List[str]
    situational_items: List[str]
    skill_build: List[str]
    talents: dict
    game_plan: dict
    item_explanations: dict
    warnings: List[str]
    source: str

# === Роуты ===

@router.post("/options", response_model=BuildOptionsResponse)
async def get_build_options(request: BuildOptionsRequest):
    """
    Генерирует список билдов (коротких вариантов) после выбора героя и аспекта.
    """
    try:
        builds = generate_build_options(
            hero=request.user_hero,
            role=request.user_role,
            aspect=request.aspect,
            enemy_lane_heroes=request.enemy_lane_heroes
        )
        return BuildOptionsResponse(builds=[BuildVariant(**b) for b in builds])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации билдов: {e}")

@router.post("/detailed", response_model=DetailedBuildResponse)
async def get_detailed_build(request: DetailedBuildRequest):
    """
    Генерирует подробный билд на основе выбранного BuildVariant и текущего драфта.
    """
    try:
        build = generate_detailed_build(
            hero=request.user_hero,
            role=request.user_role,
            aspect=request.aspect,
            selected_build_id=request.selected_build_id,
            enemy_heroes=request.enemy_heroes,
            ally_heroes=request.ally_heroes,
        )
        return build
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации подробного билда: {e}")
