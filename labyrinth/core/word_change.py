from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wordfreq import zipf_frequency

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
        if not self._validate_chain(submission, cfg):
            return ChallengeResult(
                status="fail",
                points=0,
                message="Invalid chain. Ensure valid words, one-letter changes, and correct steps.",
            )

        points_cfg = cfg.get("challenge", {}).get("points", {})
        on_success = int(points_cfg.get("on_success", 0))
        return ChallengeResult(
            status="success",
            points=on_success,
            message=f"Word change solved for {agent_name}.",
        )

    def _validate_chain(self, submission: dict[str, Any], cfg: dict[str, Any]) -> bool:
        raw = submission.get("challenge_guid")
        if not isinstance(raw, str) or not raw.strip():
            return False

        wc = WordChangeDefinition.from_config(cfg)
        if not wc.start or not wc.end or wc.steps <= 0:
            return False

        words = [w.strip().upper() for w in raw.split("-") if w.strip()]
        if len(words) != wc.steps + 1:
            return False
        if words[0] != wc.start or words[-1] != wc.end:
            return False

        length = len(wc.start)
        if any(len(w) != length for w in words):
            return False

        # Validate each word is a real word (wordfreq, non-zero Zipf)
        for w in words:
            if zipf_frequency(w.lower(), "en") <= 0:
                return False

        # Validate one-letter change per step
        for a, b in zip(words, words[1:]):
            diffs = sum(1 for x, y in zip(a, b) if x != y)
            if diffs != 1:
                return False

        return True
