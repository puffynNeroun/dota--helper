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
    description: Optional[str] = None
    winrate_score: float
    highlight: Optional[bool] = False
    build: List[str]
    starting_items: List[str]
    skill_build: Optional[List[str]] = []
    talents: Optional[Dict[str, str]] = {}  # e.g., {"10": "+15 damage"}
    game_plan: Optional[Dict[str, str]] = {}  # e.g., {"early_game": "..."}
    item_notes: Optional[Dict[str, str]] = {}  # e.g., {"black_king_bar": "Против сильных дизейблов"}

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
