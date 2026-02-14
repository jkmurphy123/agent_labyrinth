from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class PluginSpec:
    id: str
    module: str
    enabled: bool
    config_path: str


@dataclass(frozen=True)
class LabyrinthConfig:
    db_path: str
    plugins: list[PluginSpec]


def load_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_master_config(path: str | Path) -> LabyrinthConfig:
    raw = load_yaml(path)
    db_path = raw.get("db", {}).get("path", "./labyrinth.db")

    plugins_raw = raw.get("plugins", [])
    plugins: list[PluginSpec] = []
    for item in plugins_raw:
        plugins.append(
            PluginSpec(
                id=item["id"],
                module=item["module"],
                enabled=bool(item.get("enabled", True)),
                config_path=item["config_path"],
            )
        )

    return LabyrinthConfig(db_path=db_path, plugins=plugins)
