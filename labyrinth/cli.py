from __future__ import annotations

import json
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from labyrinth.core.config import load_master_config
from labyrinth.core.db import connect, init_db, fetch_one
from labyrinth.core.registry import load_plugins
from labyrinth.core.scoring import leaderboard as lb
from labyrinth.core.audit import append_audit


app = typer.Typer(add_completion=False, help="Labyrinth: plugin-friendly challenges for OpenClaw agents")
console = Console()


def _get_env(config_path: str):
    cfg = load_master_config(config_path)
    conn = connect(cfg.db_path)
    init_db(conn)
    plugins = load_plugins(cfg.plugins)
    return cfg, conn, plugins


agent_app = typer.Typer(help="Agent operations")
challenge_app = typer.Typer(help="Challenge operations")
app.add_typer(agent_app, name="agent")
app.add_typer(challenge_app, name="challenge")


@agent_app.command("register")
def agent_register(
    name: str = typer.Option(..., "--name", "-n", help="Agent display name (unique)"),
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, conn, _ = _get_env(config)
    try:
        conn.execute("INSERT INTO agents(name) VALUES (?)", (name,))
        conn.commit()
        console.print(f"✅ Registered agent: [bold]{name}[/bold]")
        append_audit({"event": "agent_register", "agent": name})
    except Exception as e:
        console.print(f"❌ Could not register agent '{name}': {e}")
        raise typer.Exit(code=1)


@challenge_app.command("list")
def challenge_list(
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, _, plugins = _get_env(config)
    table = Table(title="Labyrinth Challenges")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Enabled")
    for pid, p in plugins.items():
        table.add_row(pid, getattr(p.instance, "name", pid), "yes")
    console.print(table)


@challenge_app.command("info")
def challenge_info(
    challenge_id: str = typer.Argument(..., help="Challenge id"),
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, _, plugins = _get_env(config)
    if challenge_id not in plugins:
        console.print(f"❌ Unknown challenge: {challenge_id}")
        raise typer.Exit(code=2)
    p = plugins[challenge_id]
    instructions = p.instance.get_instructions(p.cfg)
    console.print(f"[bold]{challenge_id}[/bold]: {getattr(p.instance, 'name', challenge_id)}\n")
    console.print(instructions)


@challenge_app.command("submit")
def challenge_submit(
    challenge_id: str = typer.Argument(..., help="Challenge id"),
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
    json_payload: str = typer.Option(..., "--json", help="Submission JSON string"),
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, conn, plugins = _get_env(config)
    if challenge_id not in plugins:
        console.print(f"❌ Unknown challenge: {challenge_id}")
        raise typer.Exit(code=2)

    agent_row = fetch_one(conn, "SELECT id, name FROM agents WHERE name = ?", (agent,))
    if not agent_row:
        console.print(f"❌ Unknown agent '{agent}'. Register first: labyrinth agent register --name \"{agent}\"")
        raise typer.Exit(code=3)

    try:
        submission = json.loads(json_payload)
        if not isinstance(submission, dict):
            raise ValueError("submission must be a JSON object")
    except Exception as e:
        console.print(f"❌ Invalid JSON payload: {e}")
        raise typer.Exit(code=4)

    # Repeat detection (Phase 0: only award points once per agent+challenge if plugin config says on_repeat=0)
    p = plugins[challenge_id]
    points_cfg = p.cfg.get("challenge", {}).get("points", {})
    on_repeat = int(points_cfg.get("on_repeat", 0))

    prior = fetch_one(
        conn,
        "SELECT id FROM runs WHERE agent_id = ? AND challenge_id = ? AND status = 'success' LIMIT 1",
        (int(agent_row["id"]), challenge_id),
    )

    result = p.instance.submit(agent, submission, p.cfg)

    points_awarded = result.points
    if prior and on_repeat == 0 and result.status == "success":
        points_awarded = 0

    conn.execute(
        "INSERT INTO runs(agent_id, challenge_id, status, points, evidence_json) VALUES (?,?,?,?,?)",
        (
            int(agent_row["id"]),
            challenge_id,
            result.status,
            int(points_awarded),
            json.dumps(result.evidence or {}, ensure_ascii=False),
        ),
    )
    conn.commit()

    append_audit(
        {
            "event": "challenge_submit",
            "agent": agent,
            "challenge_id": challenge_id,
            "status": result.status,
            "points": points_awarded,
            "message": result.message,
        }
    )

    if result.status == "success":
        console.print(f"🏁 [bold green]SUCCESS[/bold green] +{points_awarded} points: {result.message}")
    else:
        console.print(f"🧱 [bold red]FAIL[/bold red] +{points_awarded} points: {result.message}")
        raise typer.Exit(code=5)


@app.command("leaderboard")
def show_leaderboard(
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, conn, _ = _get_env(config)
    rows = lb(conn)

    table = Table(title="Labyrinth Leaderboard")
    table.add_column("Rank", justify="right")
    table.add_column("Agent", style="bold")
    table.add_column("Points", justify="right")

    for i, r in enumerate(rows, start=1):
        table.add_row(str(i), r["agent"], str(r["points"]))

    console.print(table)
