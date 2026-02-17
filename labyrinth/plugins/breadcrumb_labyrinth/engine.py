from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from labyrinth.plugins.breadcrumb_labyrinth.loader import load_usable_types, load_world
from labyrinth.plugins.breadcrumb_labyrinth.models import State, World
from labyrinth.plugins.breadcrumb_labyrinth.render import render_room


GUID_RE = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}")


class Engine:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.usable_types = load_usable_types(base_dir / "usable_types.json")
        self.world = load_world(base_dir / "world.json", self.usable_types)

    def initial_state(self) -> State:
        item_visibility = {item_id: item.initially_visible for item_id, item in self.world.items.items()}
        usable_state = {}
        for room in self.world.rooms.values():
            if room.usable:
                usable_state[room.usable.usable_id] = {"locked": room.usable.locked, "used": False}

        return State(
            started=True,
            current_room=self.world.start_room,
            inventory=[],
            room_item_taken={},
            item_visibility=item_visibility,
            usable_state=usable_state,
            dynamic_exits={},
            step_count=0,
        )

    def handle(self, state: State | None, command: str) -> tuple[str, State | None, bool, bool]:
        cmd = command.strip()
        if not cmd:
            return "ERROR: Empty command.", state, False, False

        head, *rest = cmd.split()
        head_upper = head.upper()

        if head_upper == "ENTER":
            state = self.initial_state()
            return render_room(self.world, state), state, True, False

        if state is None or not state.started:
            return "ERROR: You must Enter first.", state, False, False

        if head_upper in {"N", "E", "S", "W"}:
            return self._move(state, head_upper)

        if head_upper == "LOOK":
            return render_room(self.world, state), state, False, False

        if head_upper == "INVENTORY":
            return self._inventory(state), state, False, False

        if head_upper == "GET":
            return self._get(state)

        if head_upper == "USE":
            item = " ".join(rest).strip() if rest else None
            return self._use(state, item)

        if head_upper == "SUBMIT":
            guid = " ".join(rest).strip()
            return self._submit(state, guid)

        return "ERROR: Unknown command.", state, False, False

    def _move(self, state: State, direction: str) -> tuple[str, State, bool, bool]:
        room = self.world.rooms[state.current_room]
        target = room.exits.get(direction)
        if not target and state.dynamic_exits.get(room.room_id):
            target = state.dynamic_exits[room.room_id].get(direction)

        if not target:
            msg = "You cannot go that way."
            if self.world.fairness.get("movement_failure_repeats_room", False):
                return msg + "\n\n" + render_room(self.world, state), state, False, False
            return msg, state, False, False

        state.current_room = target
        state.step_count += 1
        return render_room(self.world, state), state, True, False

    def _inventory(self, state: State) -> str:
        if not state.inventory:
            return "Inventory: (empty)"
        names = [self.world.items[item_id].name for item_id in state.inventory]
        return "Inventory: " + ", ".join(names)

    def _get(self, state: State) -> tuple[str, State, bool, bool]:
        room = self.world.rooms[state.current_room]
        if not room.floor_item:
            return "Nothing to get here.", state, False, False

        item_id = room.floor_item
        if not state.item_visibility.get(item_id, True):
            return "Nothing to get here.", state, False, False
        if state.room_item_taken.get(room.room_id, False):
            return "Nothing to get here.", state, False, False

        state.inventory.append(item_id)
        state.room_item_taken[room.room_id] = True
        state.step_count += 1

        item = self.world.items[item_id]
        if self.world.fairness.get("auto_describe_items_on_acquire", False):
            msg = item.description
        else:
            msg = f"You pick up {item.name}."
        return msg + "\n\n" + render_room(self.world, state), state, True, False

    def _use(self, state: State, item_arg: str | None) -> tuple[str, State, bool, bool]:
        room = self.world.rooms[state.current_room]
        if not room.usable:
            return "Nothing to use here.", state, False, False

        u = room.usable
        ustate = state.usable_state.get(u.usable_id, {"locked": u.locked, "used": False})

        if item_arg:
            item_id = self._resolve_item_id(state, item_arg)
            if not item_id:
                return "You do not have that item.", state, False, False
        else:
            item_id = None

        if u.type == "Chest":
            return self._use_chest(state, u, ustate, item_id)
        if u.type == "Button":
            return self._use_button(state, u, ustate)
        if u.type == "Door":
            return self._use_door(state, u, ustate, item_id)

        return "Nothing happens.", state, False, False

    def _use_chest(self, state: State, u, ustate: dict[str, Any], item_id: str | None):
        if ustate.get("locked"):
            if item_id and item_id == u.requires_item:
                ustate["locked"] = False
                ustate["used"] = True
                state.usable_state[u.usable_id] = ustate
                state.step_count += 1
                msg = u.config.get("on_unlock", {}).get("message", "You open the chest.")
                grant = u.config.get("on_unlock", {}).get("grant_item")
                if grant:
                    state.inventory.append(grant)
                    if self.world.fairness.get("auto_describe_items_on_acquire", False):
                        msg = msg + "\n" + self.world.items[grant].description
                return msg + "\n\n" + render_room(self.world, state), state, True, False
            msg = u.config.get("message_locked", "The chest is locked.")
            if self.world.fairness.get("reveal_required_item_name", False) and u.requires_item:
                msg += f" It seems to need {self.world.items[u.requires_item].name}."
            return msg, state, False, False

        if ustate.get("used"):
            return "The chest is empty.", state, False, False

        ustate["used"] = True
        state.usable_state[u.usable_id] = ustate
        state.step_count += 1
        msg = u.config.get("on_unlock", {}).get("message", "You open the chest.")
        grant = u.config.get("on_unlock", {}).get("grant_item")
        if grant:
            state.inventory.append(grant)
            if self.world.fairness.get("auto_describe_items_on_acquire", False):
                msg = msg + "\n" + self.world.items[grant].description
        return msg + "\n\n" + render_room(self.world, state), state, True, False

    def _use_button(self, state: State, u, ustate: dict[str, Any]):
        if ustate.get("used"):
            return "Nothing else happens.", state, False, False

        ustate["used"] = True
        state.usable_state[u.usable_id] = ustate
        state.step_count += 1

        reveal = u.config.get("reveals_item")
        if reveal:
            state.item_visibility[reveal] = True

        msg = u.config.get("message", "You press the button.")
        return msg + "\n\n" + render_room(self.world, state), state, True, False

    def _use_door(self, state: State, u, ustate: dict[str, Any], item_id: str | None):
        if ustate.get("locked"):
            if item_id and item_id == u.requires_item:
                ustate["locked"] = False
                ustate["used"] = True
                state.usable_state[u.usable_id] = ustate
                state.step_count += 1
                reveals = u.config.get("reveals_exit", {})
                direction = reveals.get("direction")
                to_room = reveals.get("to_room")
                state.dynamic_exits.setdefault(state.current_room, {})[direction] = to_room
                msg = u.config.get("message_unlocked", "The door unlocks.")
                return msg + "\n\n" + render_room(self.world, state), state, True, False
            msg = u.config.get("message_locked", "The door is locked.")
            if self.world.fairness.get("reveal_required_item_name", False) and u.requires_item:
                msg += f" It seems to need {self.world.items[u.requires_item].name}."
            return msg, state, False, False

        return "The door stands open.", state, False, False

    def _resolve_item_id(self, state: State, item_arg: str) -> str | None:
        arg = item_arg.strip().lower()
        for item_id in state.inventory:
            if item_id.lower() == arg:
                return item_id
            if self.world.items[item_id].name.lower() == arg:
                return item_id
        return None

    def _submit(self, state: State, guid: str) -> tuple[str, State, bool, bool]:
        state.step_count += 1
        target_guid = self._extract_guid()
        if not target_guid:
            return "FAIL: GUID not found in world.", state, True, False

        has_paper = "paper_guid" in state.inventory
        if not has_paper:
            return "FAIL: You do not possess the paper.", state, True, False

        if self.world.fairness.get("accept_case_insensitive_submit", False):
            ok = guid.strip().lower() == target_guid.lower()
        else:
            ok = guid.strip() == target_guid

        if ok:
            return "PASS: Correct GUID submitted.", state, True, True
        return "FAIL: Incorrect GUID.", state, True, False

    def _extract_guid(self) -> str | None:
        paper = self.world.items.get("paper_guid")
        if not paper:
            return None
        match = GUID_RE.search(paper.description)
        if not match:
            return None
        return match.group(0)


def state_to_dict(state: State) -> dict[str, Any]:
    return asdict(state)


def state_from_dict(data: dict[str, Any]) -> State:
    return State(
        started=bool(data.get("started", False)),
        current_room=str(data.get("current_room", "")),
        inventory=list(data.get("inventory", [])),
        room_item_taken=dict(data.get("room_item_taken", {})),
        item_visibility=dict(data.get("item_visibility", {})),
        usable_state=dict(data.get("usable_state", {})),
        dynamic_exits=dict(data.get("dynamic_exits", {})),
        step_count=int(data.get("step_count", 0)),
    )
