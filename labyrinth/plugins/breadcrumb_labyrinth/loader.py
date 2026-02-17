from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from labyrinth.plugins.breadcrumb_labyrinth.models import Item, Room, Usable, World


VALID_DIRECTIONS = {"N", "E", "S", "W"}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_usable_types(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    return data.get("types", {})


def validate_world(world_data: dict[str, Any], usable_types: dict[str, Any]) -> None:
    rooms = world_data.get("rooms", {})
    items = world_data.get("items", {})

    start_room = world_data.get("start_room")
    if start_room not in rooms:
        raise ValueError("start_room does not exist")

    usable_ids: set[str] = set()

    for room_id, room in rooms.items():
        # exits
        for direction, target in room.get("exits", {}).items():
            if direction not in VALID_DIRECTIONS:
                raise ValueError(f"invalid exit direction {direction} in {room_id}")
            if target not in rooms:
                raise ValueError(f"exit {direction} in {room_id} points to unknown room {target}")

        # floor_item
        floor_item = room.get("floor_item")
        if floor_item is not None and floor_item not in items:
            raise ValueError(f"unknown floor_item {floor_item} in {room_id}")

        usable = room.get("usable")
        if usable is None:
            continue

        utype = usable.get("type")
        if utype not in usable_types:
            raise ValueError(f"unknown usable type {utype} in {room_id}")

        uid = usable.get("id")
        if uid in usable_ids:
            raise ValueError(f"duplicate usable id {uid}")
        usable_ids.add(uid)

        locked = bool(usable.get("locked", False))
        requires_item = usable.get("requires_item")
        if requires_item and requires_item not in items:
            raise ValueError(f"unknown requires_item {requires_item} in {room_id}")
        if requires_item and not locked:
            raise ValueError(f"requires_item set but locked=false in {room_id}")

        if utype == "Door":
            reveals = usable.get("reveals_exit", {})
            direction = reveals.get("direction")
            to_room = reveals.get("to_room")
            if direction not in VALID_DIRECTIONS:
                raise ValueError(f"invalid door direction in {room_id}")
            if to_room not in rooms:
                raise ValueError(f"door in {room_id} points to unknown room {to_room}")


def load_world(path: Path, usable_types: dict[str, Any]) -> World:
    data = _load_json(path)
    validate_world(data, usable_types)

    items: dict[str, Item] = {}
    for item_id, item in data.get("items", {}).items():
        items[item_id] = Item(
            item_id=item_id,
            name=item.get("name", item_id),
            description=item.get("description", ""),
            initially_visible=bool(item.get("initially_visible", True)),
        )

    rooms: dict[str, Room] = {}
    for room_id, room in data.get("rooms", {}).items():
        usable = None
        if room.get("usable") is not None:
            u = room["usable"]
            usable = Usable(
                usable_id=u.get("id"),
                type=u.get("type"),
                name=u.get("name", u.get("type", "Usable")),
                locked=bool(u.get("locked", False)),
                requires_item=u.get("requires_item"),
                config=u,
            )
        rooms[room_id] = Room(
            room_id=room_id,
            title=room.get("title", room_id),
            description=room.get("description", ""),
            exits=room.get("exits", {}),
            floor_item=room.get("floor_item"),
            usable=usable,
        )

    return World(
        world_id=data.get("world_id", "world"),
        start_room=data.get("start_room"),
        fairness=data.get("fairness", {}),
        items=items,
        rooms=rooms,
        win=data.get("win", {}),
    )
