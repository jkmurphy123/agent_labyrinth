from __future__ import annotations

from labyrinth.core.db import fetch_all


def leaderboard(conn) -> list[dict]:
    rows = fetch_all(
        conn,
        """
        SELECT a.name as agent_name, COALESCE(SUM(r.points), 0) AS total_points
        FROM agents a
        LEFT JOIN runs r ON r.agent_id = a.id
        GROUP BY a.id
        ORDER BY total_points DESC, a.created_at ASC
        """,
    )
    return [{"agent": r["agent_name"], "points": int(r["total_points"])} for r in rows]
