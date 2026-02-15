from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin


@dataclass(frozen=True)
class WordChangeDefinition:
    start: str
    end: str
    steps: int

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "WordChangeDefinition":
        wc = cfg.get("word_change", {})
        start = str(wc.get("start", "")).strip().upper()
        end = str(wc.get("end", "")).strip().upper()
        steps = int(wc.get("steps", 0))
        return cls(start=start, end=end, steps=steps)


class WordChangeChallenge(BaseChallengePlugin):
    def get_instructions(self, cfg: dict[str, Any]) -> str:
        instructions = cfg.get("prompts", {}).get("instructions", "").strip()
        if instructions:
            return instructions

        wc = WordChangeDefinition.from_config(cfg)
        if not wc.start or not wc.end or not wc.steps:
            return ""
        return (
            "Can you change the start word into the end word using the number of steps given? "
            "Change only one letter per step and do not change the order of the letters. "
            "Each step should produce a real word. For example, to change BEAD into TRIM in 4 steps "
            "the solution would be BEAD->BEAM->TEAM->TRAM->TRIM. "
            "Generate a GUID from your solution by listing your words with dashes "
            "(for example, \"BEAD-BEAM-TEAM-TRAM-TRIM\") and submitting it for confirmation.\n\n"
            f"For this challenge, use Start: {wc.start}\nEnd: {wc.end}\nSteps: {wc.steps}"
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
            message=f"Word change solved for {agent_name}.",
        )
