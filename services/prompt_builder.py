import os
from pathlib import Path
from typing import Dict

from models.types import DraftInput

PROMPT_DIR = Path(__file__).parent.parent / "prompts"

class PromptBuilder:
    def __init__(self):
        self.templates = {
            "base": self._load_template("prompt_base.txt"),
            "lane": self._load_template("prompt_lane.txt"),
            "items": self._load_template("prompt_items.txt"),
            "skills": self._load_template("prompt_skills.txt"),
            "strategy": self._load_template("prompt_strategy.txt"),
        }

    def _load_template(self, filename: str) -> str:
        path = PROMPT_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"❌ Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def build_recommend_prompt(self, draft: DraftInput) -> str:
        """
        Формирует промпт на основе DraftInput для генерации рекомендованных героев.
        """
        enemy = ", ".join(draft.enemy_heroes)
        allies = ", ".join(draft.ally_heroes)
        role = draft.user_role
        aspect = draft.aspect or "universal"

        return (
            f"Ты — опытный аналитик по Dota 2.\n"
            f"Выбери сильных героев против: {enemy}\n"
            f"Учитывай союзников: {allies}\n"
            f"Роль: {role}\n"
            f"Аспект: {aspect}\n\n"
            f"Верни JSON с:\n"
            f"- recommended_aspect (string)\n"
            f"- suggested_heroes (array из name, score, reason)\n"
            f"- lane_opponents (array)\n"
            f"- source: 'openai'\n"
        )

    def build_items_prompt(self, hero: str, aspect: str) -> str:
        return self.templates["items"].format(hero=hero, aspect=aspect)

    def build_lane_prompt(self, hero: str, enemies: list) -> str:
        enemy_list = ", ".join(enemies)
        return self.templates["lane"].format(hero=hero, enemies=enemy_list)

    def build_skills_prompt(self, hero: str) -> str:
        return self.templates["skills"].format(hero=hero)

    def build_strategy_prompt(self, hero: str, allies: list, enemies: list) -> str:
        allies_str = ", ".join(allies)
        enemies_str = ", ".join(enemies)
        return self.templates["strategy"].format(hero=hero, allies=allies_str, enemies=enemies_str)

