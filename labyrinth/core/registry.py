from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol

from labyrinth.core.config import PluginSpec, load_yaml


class ChallengePlugin(Protocol):
    id: str
    name: str

    def get_instructions(self, cfg: dict[str, Any]) -> str: ...
    def submit(self, agent_name: str, submission: dict[str, Any], cfg: dict[str, Any]) -> Any: ...


@dataclass
class LoadedPlugin:
    spec: PluginSpec
    instance: ChallengePlugin
    cfg: dict[str, Any]


def _load_object(dotted: str) -> Any:
    # "pkg.module:ClassName"
    mod_path, obj_name = dotted.split(":", 1)
    mod = import_module(mod_path)
    return getattr(mod, obj_name)


def load_plugins(specs: list[PluginSpec]) -> dict[str, LoadedPlugin]:
    loaded: dict[str, LoadedPlugin] = {}
    for spec in specs:
        if not spec.enabled:
            continue
        cls = _load_object(spec.module)
        instance = cls()  # type: ignore[call-arg]
        cfg = load_yaml(spec.config_path)
        loaded[spec.id] = LoadedPlugin(spec=spec, instance=instance, cfg=cfg)
    return loaded
