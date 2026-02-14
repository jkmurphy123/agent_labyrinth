from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from labyrinth.core.config import load_master_config
from labyrinth.core.db import connect, fetch_all, fetch_one
from labyrinth.core.models import ChallengeResult
from labyrinth.core.registry import BaseChallengePlugin, load_plugins


def _resolve_master_config(submission: dict[str, Any]) -> Path | None:
    explicit = submission.get("config_path")
    if isinstance(explicit, str) and explicit:
        p = Path(explicit)
        if p.exists():
            return p.resolve()

    env_path = os.getenv("LABYRINTH_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p.resolve()

    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "labyrinth.yaml"
        if candidate.exists():
            return candidate.resolve()

    return None


def _build_table(rows: list[dict[str, Any]]) -> str:
    headers = ["ID", "Name", "Max", "Agent"]
    widths = {
        "ID": len(headers[0]),
        "Name": len(headers[1]),
        "Max": len(headers[2]),
        "Agent": len(headers[3]),
    }
    for r in rows:
        widths["ID"] = max(widths["ID"], len(str(r["id"])))
        widths["Name"] = max(widths["Name"], len(str(r["name"])))
        widths["Max"] = max(widths["Max"], len(str(r["max_points"])))
        widths["Agent"] = max(widths["Agent"], len(str(r["agent_points"])))

    def fmt(values: list[str]) -> str:
        return " | ".join(
            [
                values[0].ljust(widths["ID"]),
                values[1].ljust(widths["Name"]),
                values[2].rjust(widths["Max"]),
                values[3].rjust(widths["Agent"]),
            ]
        )

    sep = "-+-".join(
        [
            "-" * widths["ID"],
            "-" * widths["Name"],
            "-" * widths["Max"],
            "-" * widths["Agent"],
        ]
    )

    lines = [fmt(headers), sep]
    for r in rows:
        lines.append(
            fmt(
                [
                    str(r["id"]),
                    str(r["name"]),
                    str(r["max_points"]),
                    str(r["agent_points"]),
                ]
            )
        )
    return "\n".join(lines)


class Plugin(BaseChallengePlugin):
    id = "scorecard"
    name = "Scorecard"

    def get_instructions(self, cfg: dict[str, Any]) -> str:
        return cfg.get("prompts", {}).get("instructions", "").strip()

    def submit(self, agent_name: str, submission: dict[str, Any], cfg: dict[str, Any]) -> ChallengeResult:
        master_path = _resolve_master_config(submission)
        if master_path is None:
            return ChallengeResult(
                status="fail",
                points=0,
                message=(
                    "Could not locate labyrinth.yaml. "
                    "Set LABYRINTH_CONFIG or pass config_path in submission."
                ),
            )

        master_cfg = load_master_config(master_path)
        plugins = load_plugins(master_cfg.plugins)
        conn = connect(master_cfg.db_path)

        agent_row = fetch_one(conn, "SELECT id FROM agents WHERE name = ?", (agent_name,))
        if not agent_row:
            return ChallengeResult(
                status="fail",
                points=0,
                message=f"Unknown agent '{agent_name}'. Register first.",
            )

        scored = fetch_all(
            conn,
            """
            SELECT r.challenge_id, COALESCE(SUM(r.points), 0) AS points
            FROM runs r
            WHERE r.agent_id = ?
            GROUP BY r.challenge_id
            """,
            (int(agent_row["id"]),),
        )
        points_by_challenge = {r["challenge_id"]: int(r["points"]) for r in scored}

        rows: list[dict[str, Any]] = []
        for pid, p in plugins.items():
            points_cfg = p.cfg.get("challenge", {}).get("points", {})
            max_points = int(points_cfg.get("on_success", 0))
            name = p.cfg.get("challenge", {}).get("name", getattr(p.instance, "name", pid))
            rows.append(
                {
                    "id": pid,
                    "name": name,
                    "max_points": max_points,
                    "agent_points": points_by_challenge.get(pid, 0),
                }
            )

        rows.sort(key=lambda r: (r["max_points"], r["id"]))
        table = _build_table(rows)
        return ChallengeResult(
            status="success",
            points=0,
            message=table,
            evidence={"scorecard": rows},
        )
