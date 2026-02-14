from __future__ import annotations

from typing import Any

from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin


class Plugin(BaseChallengePlugin):
    id = "wargs_logic"
    name = "Wargs Logic Problem"

    def get_instructions(self, cfg: dict[str, Any]) -> str:
        return cfg.get("prompts", {}).get("instructions", "").strip()

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
            message=f"Wargs logic solved for {agent_name}.",
        )
