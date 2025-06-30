from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal

VALID_ROLES = {"mid", "safelane", "offlane", "support", "hard support"}

class DraftInput(BaseModel):
    enemy_heroes: List[str] = Field(default_factory=list)
    ally_heroes: List[str] = Field(default_factory=list)  # союзники без учёта себя
    user_role: Literal["mid", "safelane", "offlane", "support", "hard support"]
    user_hero: Optional[str] = None  # Может быть null — если не пикнул

    @validator("enemy_heroes", "ally_heroes", pre=True)
    def remove_duplicates(cls, v):
        return list(dict.fromkeys(v or []))[:5]  # max 5 врагов, max 4 союзника в logic

    class Config:
        schema_extra = {
            "example": {
                "enemy_heroes": ["phantom_assassin", "zeus"],
                "ally_heroes": ["juggernaut", "crystal_maiden"],
                "user_role": "mid",
                "user_hero": None
            }
        }


class HeroSuggestion(BaseModel):
    name: str
    score: float
    reason: Optional[str] = None


class RecommendationResponse(BaseModel):
    suggested_heroes: List[HeroSuggestion]
    lane_opponents: List[str]
    starting_items: List[str]
    build_easy: List[str]
    build_even: List[str]
    build_hard: List[str]
    warnings: Optional[List[str]] = []
