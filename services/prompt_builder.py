from pathlib import Path
from typing import Optional
from models.types import DraftInput


class PromptBuilder:
    def __init__(self):
        self.templates = {
            "base": self._read("prompt_base.txt"),
            "skills": self._read("prompt_skills.txt"),
            "items": self._read("prompt_items.txt"),
            "strategy": self._read("prompt_strategy.txt"),
            "lane": self._read("prompt_lane.txt"),
        }

    def _read(self, filename: str) -> str:
        path = Path("prompts") / filename
        if not path.exists():
            return f"# WARNING: {filename} not found."
        return path.read_text(encoding="utf-8").strip()

    def build_recommend_prompt(self, draft: DraftInput) -> str:
        parts = [
            self.templates["base"],
            f"\n---\n🎯 Роль игрока: {draft.user_role}",
            f"🛡️ Союзники: {', '.join(draft.ally_heroes)}",
            f"⚔️ Противники: {', '.join(draft.enemy_heroes)}",
        ]

        if draft.user_hero:
            parts.append(f"🧙 Пользователь уже выбрал героя: {draft.user_hero}. Не предлагай других.")
        else:
            parts.append("🔍 Герой не выбран. Предложи 3 лучших кандидата с кратким объяснением.")

        if draft.aspect:
            parts.append(f"🔮 Аспект предпочтения: {draft.aspect}")

        parts.append("---")
        parts.extend([
            self.templates["skills"],
            self.templates["items"],
            self.templates["strategy"],
            self.templates["lane"]
        ])

        return "\n\n".join(parts)
