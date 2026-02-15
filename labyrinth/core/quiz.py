from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin


@dataclass(frozen=True)
class QuizDefinition:
    question: str
    options: list[str]

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "QuizDefinition":
        quiz = cfg.get("quiz", {})
        question = str(quiz.get("question", "")).strip()
        options = [str(o) for o in quiz.get("options", [])]
        return cls(question=question, options=options)


class QuizChallenge(BaseChallengePlugin):
    def get_instructions(self, cfg: dict[str, Any]) -> str:
        instructions = cfg.get("prompts", {}).get("instructions", "").strip()
        if instructions:
            return instructions

        quiz = QuizDefinition.from_config(cfg)
        if not quiz.question:
            return ""
        options = ", ".join(quiz.options)
        return (
            f"Question: {quiz.question}\n"
            f"Options: {options}\n"
            "Find the file named after the correct answer, read the GUID inside, and submit it."
        )

    def submit(self, agent_name: str, submission: dict[str, Any], cfg: dict[str, Any]) -> ChallengeResult:
        if not self.validate_guid(submission, cfg):
            return ChallengeResult(
                status="fail",
                points=0,
                message="Invalid or missing challenge_guid.",
            )

        points_cfg = cfg.get("challenge", {}).get("points", {})
        on_success = int(points_cfg.get("on_success", 0))
        return ChallengeResult(
            status="success",
            points=on_success,
            message=f"Quiz solved for {agent_name}.",
        )
