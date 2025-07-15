from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field, validator

# ===== Constants =====

VALID_ROLES = {"mid", "safelane", "offlane", "support", "hard support"}
SOURCE_ENUM = Literal["openai", "fallback", "meta"]

# ===== Draft Input =====

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
                "user_hero": "ember_spirit",
                "aspect": "fire"
            }
        }

# ===== Hero Suggestion =====

class HeroSuggestion(BaseModel):
    name: str
    score: float
    reason: Optional[str] = None

# ===== Build Plan (for /recommend) =====

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

# ===== Recommendation Response (/recommend) =====

class RecommendationResponse(BaseModel):
    recommended_aspect: str
    suggested_heroes: List[HeroSuggestion] = Field(default_factory=list)
    lane_opponents: List[str] = Field(default_factory=list)
    starting_items: List[str] = Field(default_factory=list)
    build_easy: List[str] = Field(default_factory=list)
    build_even: List[str] = Field(default_factory=list)
    build_hard: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    builds: Optional[List[BuildPlan]] = Field(default_factory=list)
    source: SOURCE_ENUM

# ===== Build Options (/builds/options) =====

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

# ===== Detailed Build (/builds/detailed) =====

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
    talents: Dict[str, str]
    game_plan: Dict[str, str]
    item_explanations: Dict[str, str]
    builds: List[BuildPlan] = Field(default_factory=list)
    warnings: List[str]
    source: SOURCE_ENUM
