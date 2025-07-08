from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Dict

VALID_ROLES = {"mid", "safelane", "offlane", "support", "hard support"}


class DraftInput(BaseModel):
    enemy_heroes: List[str] = Field(default_factory=list)
    ally_heroes: List[str] = Field(default_factory=list)
    user_role: Literal["mid", "safelane", "offlane", "support", "hard support"]
    user_hero: Optional[str] = None
    aspect: Optional[str] = None

    @validator("enemy_heroes", "ally_heroes", pre=True)
    def remove_duplicates(cls, v):
        return list(dict.fromkeys(v or []))[:5]

    class Config:
        schema_extra = {
            "example": {
                "enemy_heroes": ["phantom_assassin", "zeus"],
                "ally_heroes": ["juggernaut", "crystal_maiden"],
                "user_role": "mid",
                "user_hero": None,
                "aspect": "маг"
            }
        }


class HeroSuggestion(BaseModel):
    name: str
    score: float
    reason: Optional[str] = None


class BuildPlan(BaseModel):
    name: str
    winrate_score: float
    build: List[str]
    starting_items: List[str]
    skill_build: List[str]

    description: Optional[str] = None
    highlight: Optional[bool] = False
    talents: Dict[str, str] = Field(default_factory=dict)
    game_plan: Dict[str, str] = Field(default_factory=dict)
    item_notes: Dict[str, str] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "name": "Маг билд",
                "description": "Фокус на AoE урон и контроль",
                "winrate_score": 0.78,
                "highlight": True,
                "build": ["kaya", "aether_lens", "black_king_bar"],
                "starting_items": ["tango", "mantle_of_intelligence", "ward"],
                "skill_build": ["Q", "E", "Q", "W", "Q", "R", "Q", "W", "W", "W", "R", "E", "E", "E", "Stats", "R"],
                "talents": {"10": "+15% spell amp", "15": "+100 cast range"},
                "game_plan": {
                    "early_game": "Спамь Q на крипов, контролируй руну",
                    "mid_game": "Инициация с дальнего расстояния через E + BKB",
                    "late_game": "Поддержка команды и сейв через Hex/Sheepstick"
                },
                "item_notes": {
                    "black_king_bar": "Обязателен против Лины, Зевса и других магов",
                    "aether_lens": "Увеличивает дальность Q и контроля"
                }
            }
        }


class RecommendationResponse(BaseModel):
    recommended_aspect: str
    builds: List[BuildPlan]

    suggested_heroes: List[HeroSuggestion] = Field(default_factory=list)
    lane_opponents: List[str] = Field(default_factory=list)
    starting_items: List[str] = Field(default_factory=list)
    build_easy: List[str] = Field(default_factory=list)
    build_even: List[str] = Field(default_factory=list)
    build_hard: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    source: Optional[str] = Field(default=None, description="Источник: 'openai' или 'fallback'")
