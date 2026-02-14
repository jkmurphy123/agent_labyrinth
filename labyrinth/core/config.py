from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class PluginSpec:
    id: str
    path: str
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
    master_path = Path(path).resolve()
    raw = load_yaml(master_path)
    db_path = raw.get("db", {}).get("path", "./labyrinth.db")
    if not Path(db_path).is_absolute():
        db_path = str((master_path.parent / db_path).resolve())

    plugins_raw = raw.get("plugins", [])
    plugins: list[PluginSpec] = []
    for item in plugins_raw:
        plugin_path = item["path"]
        if not Path(plugin_path).is_absolute():
            plugin_path = str((master_path.parent / plugin_path).resolve())
        config_path = item["config_path"]
        if not Path(config_path).is_absolute():
            config_path = str((master_path.parent / config_path).resolve())
        plugins.append(
            PluginSpec(
                id=item["id"],
                path=plugin_path,
                enabled=bool(item.get("enabled", True)),
                config_path=config_path,
            )
        )

    return LabyrinthConfig(db_path=db_path, plugins=plugins)
