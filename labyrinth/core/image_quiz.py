from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin


@dataclass(frozen=True)
class ImageQuizDefinition:
    question: str
    prompt_image: str
    options: list[str]

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "ImageQuizDefinition":
        iq = cfg.get("image_quiz", {})
        question = str(iq.get("question", "")).strip()
        prompt_image = str(iq.get("prompt_image", "")).strip()
        options = [str(o) for o in iq.get("options", [])]
        return cls(question=question, prompt_image=prompt_image, options=options)


class ImageQuizChallenge(BaseChallengePlugin):
    def get_instructions(self, cfg: dict[str, Any]) -> str:
        instructions = cfg.get("prompts", {}).get("instructions", "").strip()
        if instructions:
            return instructions

        iq = ImageQuizDefinition.from_config(cfg)
        if not iq.question:
            return ""
        options = ", ".join(iq.options)
        return (
            f"Question: {iq.question}\n"
            f"Prompt image: {iq.prompt_image}\n"
            f"Option images (by GUID filename): {options}\n"
            "Find the correct answer image, then submit its GUID."
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
            message=f"Image quiz solved for {agent_name}.",
        )
