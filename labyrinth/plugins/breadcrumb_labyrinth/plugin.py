from __future__ import annotations

import json
from pathlib import Path

from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin
from labyrinth.plugins.breadcrumb_labyrinth.engine import Engine, state_from_dict, state_to_dict


class Plugin(BaseChallengePlugin):
    id = "breadcrumb_labyrinth"
    name = "Breadcrumb Labyrinth"

    def _session_path(self, agent_name: str) -> Path:
        safe = "".join(c for c in agent_name if c.isalnum() or c in ("-", "_")).strip()
        if not safe:
            safe = "agent"
        sessions = Path(__file__).parent / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        return sessions / f"{safe}.json"

    def get_instructions(self, cfg: dict) -> str:
        return cfg.get("prompts", {}).get("instructions", "").strip()

    def submit(self, agent_name: str, submission: dict, cfg: dict) -> ChallengeResult:
        command = submission.get("command")
        if not isinstance(command, str):
            return ChallengeResult(status="fail", points=0, message="Missing command.")

        engine = Engine(Path(__file__).parent)
        session_path = self._session_path(agent_name)
        state = None
        if session_path.exists():
            state = state_from_dict(json.loads(session_path.read_text(encoding="utf-8")))

        output, new_state, changed, passed = engine.handle(state, command)
        if changed and new_state is not None:
            session_path.write_text(json.dumps(state_to_dict(new_state), indent=2), encoding="utf-8")

        if command.strip().upper().startswith("SUBMIT"):
            status = "success" if passed else "fail"
            points = int(cfg.get("challenge", {}).get("points", {}).get("on_success", 0)) if passed else 0
            return ChallengeResult(status=status, points=points, message=output)

        return ChallengeResult(status="success", points=0, message=output)
