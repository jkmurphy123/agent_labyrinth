from __future__ import annotations

from typing import Any

from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin


class Plugin(BaseChallengePlugin):
    id = "registration"
    name = "Register Your Agent"

    def get_instructions(self, cfg: dict[str, Any]) -> str:
        return cfg.get("prompts", {}).get("instructions", "").strip()

    def submit(self, agent_name: str, submission: dict[str, Any], cfg: dict[str, Any]) -> ChallengeResult:
        proof_phrase = submission.get("proof_phrase")
        required = "LABYRINTH: I REGISTERED"

        if not isinstance(proof_phrase, str) or proof_phrase != required:
            return ChallengeResult(
                status="fail",
                points=0,
                message="Invalid proof_phrase.",
                evidence={"expected": required},
            )

        points_cfg = cfg.get("challenge", {}).get("points", {})
        on_success = int(points_cfg.get("on_success", 0))
        return ChallengeResult(
            status="success",
            points=on_success,
            message=f"Registered agent proof accepted for {agent_name}.",
        )
