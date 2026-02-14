from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Agent:
    id: int
    name: str


@dataclass(frozen=True)
class ChallengeResult:
    status: str  # "success" | "fail"
    points: int
    message: str
    evidence: dict[str, Any] | None = None
