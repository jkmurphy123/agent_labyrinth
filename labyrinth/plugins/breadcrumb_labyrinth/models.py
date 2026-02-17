from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    description: str
    initially_visible: bool = True


@dataclass(frozen=True)
class Usable:
    usable_id: str
    type: str
    name: str
    locked: bool
    requires_item: str | None
    config: dict[str, Any]


@dataclass(frozen=True)
class Room:
    room_id: str
    title: str
    description: str
    exits: dict[str, str]
    floor_item: str | None
    usable: Usable | None


@dataclass(frozen=True)
class World:
    world_id: str
    start_room: str
    fairness: dict[str, Any]
    items: dict[str, Item]
    rooms: dict[str, Room]
    win: dict[str, Any]


@dataclass
class State:
    started: bool
    current_room: str
    inventory: list[str]
    room_item_taken: dict[str, bool]
    item_visibility: dict[str, bool]
    usable_state: dict[str, dict[str, Any]]
    dynamic_exits: dict[str, dict[str, str]]
    step_count: int
