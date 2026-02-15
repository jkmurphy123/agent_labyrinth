from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module, util as import_util
from pathlib import Path
from typing import Any, Protocol

from labyrinth.core.config import PluginSpec, load_yaml


class BaseChallengePlugin:
    id: str
    name: str

    def build_manifest(self, cfg: dict[str, Any]) -> dict[str, Any]:
        challenge = cfg.get("challenge", {})
        points_cfg = challenge.get("points", {})
        return {
            "id": challenge.get("id", self.id),
            "name": challenge.get("name", self.name),
            "version": challenge.get("version", "0.0.0"),
            "description": challenge.get("description", ""),
            "goal": challenge.get("goal", ""),
            "rules": cfg.get("rules", {}),
            "inputs": challenge.get("inputs", {}),
            "scoring": {
                "on_success": int(points_cfg.get("on_success", 0)),
                "on_repeat": int(points_cfg.get("on_repeat", 0)),
            },
            "capabilities": challenge.get("capabilities", []),
            "guid": challenge.get("guid_display", challenge.get("guid", "")),
            "quiz": cfg.get("quiz", {}),
            "image_quiz": cfg.get("image_quiz", {}),
        }

    def get_secret_guid(self, cfg: dict[str, Any]) -> str:
        return str(cfg.get("challenge", {}).get("guid", "")).strip()

    def get_display_guid(self, cfg: dict[str, Any]) -> str:
        return str(cfg.get("challenge", {}).get("guid_display", self.get_secret_guid(cfg))).strip()

    def validate_guid(self, submission: dict[str, Any], cfg: dict[str, Any]) -> bool:
        expected = self.get_secret_guid(cfg)
        provided = submission.get("challenge_guid")
        return bool(expected) and isinstance(provided, str) and provided.strip() == expected

    def get_instructions(self, cfg: dict[str, Any]) -> str:
        raise NotImplementedError

    def get_manifest(self, cfg: dict[str, Any]) -> dict[str, Any]:
        return self.build_manifest(cfg)

    def submit(self, agent_name: str, submission: dict[str, Any], cfg: dict[str, Any]) -> Any:
        raise NotImplementedError


class ChallengePlugin(Protocol):
    id: str
    name: str

    def get_instructions(self, cfg: dict[str, Any]) -> str: ...
    def get_manifest(self, cfg: dict[str, Any]) -> dict[str, Any]: ...
    def submit(self, agent_name: str, submission: dict[str, Any], cfg: dict[str, Any]) -> Any: ...


@dataclass
class LoadedPlugin:
    spec: PluginSpec
    instance: ChallengePlugin
    cfg: dict[str, Any]


def _load_module_from_file(module_name: str, file_path: Path):
    spec = import_util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load plugin module from {file_path}")
    module = import_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugins(specs: list[PluginSpec]) -> dict[str, LoadedPlugin]:
    loaded: dict[str, LoadedPlugin] = {}
    for spec in specs:
        if not spec.enabled:
            continue
        plugin_dir = Path(spec.path)
        plugin_file = plugin_dir / "plugin.py"
        if not plugin_file.exists():
            raise FileNotFoundError(f"Plugin file not found: {plugin_file}")
        module = _load_module_from_file(f"labyrinth.plugins.{spec.id}", plugin_file)
        cls = getattr(module, "Plugin", None)
        if cls is None:
            raise AttributeError(f"Plugin class 'Plugin' not found in {plugin_file}")
        instance = cls()  # type: ignore[call-arg]
        cfg = load_yaml(spec.config_path)
        loaded[spec.id] = LoadedPlugin(spec=spec, instance=instance, cfg=cfg)
    return loaded
