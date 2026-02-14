from __future__ import annotations

from typing import Any

from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin


def _shift_char(ch: str, delta: int) -> str:
    if "0" <= ch <= "9":
        return str((int(ch) + delta) % 10)
    if "a" <= ch <= "z":
        return chr(((ord(ch) - 97 + delta) % 26) + 97)
    if "A" <= ch <= "Z":
        return chr(((ord(ch) - 65 + delta) % 26) + 65)
    return ch


def _decrypt_caesar(text: str) -> str:
    return "".join(_shift_char(ch, -1) for ch in text)


def _encrypt_caesar(text: str) -> str:
    return "".join(_shift_char(ch, 1) for ch in text)


class Plugin(BaseChallengePlugin):
    id = "cypher"
    name = "Cypher"

    def get_instructions(self, cfg: dict[str, Any]) -> str:
        return cfg.get("prompts", {}).get("instructions", "").strip()

    def get_secret_guid(self, cfg: dict[str, Any]) -> str:
        return str(cfg.get("challenge", {}).get("guid", "")).strip()

    def get_display_guid(self, cfg: dict[str, Any]) -> str:
        encrypted = str(cfg.get("challenge", {}).get("guid_display", "")).strip()
        if encrypted:
            return encrypted
        return _encrypt_caesar(self.get_secret_guid(cfg))

    def submit(self, agent_name: str, submission: dict[str, Any], cfg: dict[str, Any]) -> ChallengeResult:
        if not self.validate_guid(submission, cfg):
            return ChallengeResult(
                status="fail",
                points=0,
                message="Invalid or missing challenge_guid.",
                evidence={"hint": "Decrypt the encrypted GUID from the challenge goal."},
            )

        points_cfg = cfg.get("challenge", {}).get("points", {})
        on_success = int(points_cfg.get("on_success", 0))
        return ChallengeResult(
            status="success",
            points=on_success,
            message=f"Cypher challenge solved for {agent_name}.",
        )
