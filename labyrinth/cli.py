from __future__ import annotations

import json
import os
from pathlib import Path
import typer
from importlib import metadata
from rich.console import Console
from rich.table import Table

from labyrinth.core.config import load_master_config
from labyrinth.core.db import connect, init_db, fetch_one, fetch_all
from labyrinth.core.registry import load_plugins
from labyrinth.core.scoring import leaderboard as lb
from labyrinth.core.audit import append_audit


app = typer.Typer(add_completion=False, help="Labyrinth: plugin-friendly challenges for OpenClaw agents")
console = Console()


def _get_version() -> str:
    try:
        return metadata.version("labyrinth")
    except metadata.PackageNotFoundError:
        return "0.0.0+local"


def _resolve_config_path(config_path: str) -> str:
    path = Path(config_path)
    if path.exists():
        return str(path)

    env_path = os.getenv("LABYRINTH_CONFIG")
    if env_path:
        env_candidate = Path(env_path)
        if env_candidate.exists():
            return str(env_candidate)

    if config_path != "labyrinth.yaml":
        return str(path)

    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "labyrinth.yaml"
        if candidate.exists():
            return str(candidate)

    return str(path)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the Labyrinth version and exit.",
        is_eager=True,
    ),
):
    if version:
        console.print(_get_version())
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


def _get_env(config_path: str):
    cfg = load_master_config(_resolve_config_path(config_path))
    conn = connect(cfg.db_path)
    init_db(conn)
    plugins = load_plugins(cfg.plugins)
    return cfg, conn, plugins


agent_app = typer.Typer(help="Agent operations")
challenge_app = typer.Typer(help="Challenge operations")
plugins_app = typer.Typer(help="Plugin operations")
app.add_typer(agent_app, name="agent")
app.add_typer(challenge_app, name="challenge")
app.add_typer(plugins_app, name="plugins")


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


@agent_app.command("list")
def agent_list(
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, conn, _ = _get_env(config)
    rows = fetch_all(conn, "SELECT id, name, created_at FROM agents ORDER BY id ASC")
    if not rows:
        console.print("No agents registered yet.")
        return

    table = Table(title="Labyrinth Agents")
    table.add_column("ID", justify="right")
    table.add_column("Name", style="bold")
    table.add_column("Created", justify="right")

    for r in rows:
        table.add_row(str(r["id"]), r["name"], r["created_at"])

    console.print(table)


@challenge_app.command("list")
def challenge_list(
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, _, plugins = _get_env(config)
    table = Table(title="Labyrinth Challenges")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("GUID")
    table.add_column("Enabled")
    for pid, p in plugins.items():
        guid = str(p.cfg.get("challenge", {}).get("guid", "")).strip()
        table.add_row(pid, getattr(p.instance, "name", pid), guid, "yes")
    console.print(table)


@plugins_app.command("list")
def plugins_list(
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, _, plugins = _get_env(config)
    table = Table(title="Labyrinth Plugins")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("GUID")
    table.add_column("Path")
    for pid, p in plugins.items():
        guid = str(p.cfg.get("challenge", {}).get("guid", "")).strip()
        table.add_row(pid, getattr(p.instance, "name", pid), guid, p.spec.path)
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


@challenge_app.command("manifest")
def challenge_manifest(
    challenge_id: str = typer.Argument(..., help="Challenge id"),
    config: str = typer.Option("labyrinth.yaml", "--config", help="Path to master config"),
):
    _, _, plugins = _get_env(config)
    if challenge_id not in plugins:
        console.print(f"âŒ Unknown challenge: {challenge_id}")
        raise typer.Exit(code=2)
    p = plugins[challenge_id]
    manifest = p.instance.get_manifest(p.cfg)
    console.print_json(data=manifest)


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
