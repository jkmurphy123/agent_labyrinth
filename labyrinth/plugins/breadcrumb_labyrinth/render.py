from __future__ import annotations

from labyrinth.plugins.breadcrumb_labyrinth.models import State, World


def render_room(world: World, state: State) -> str:
    room = world.rooms[state.current_room]
    lines: list[str] = []
    lines.append(f"== {room.title} ==")
    lines.append("")
    lines.append(room.description)
    lines.append("")

    exits = set(room.exits.keys())
    if state.dynamic_exits.get(room.room_id):
        exits.update(state.dynamic_exits[room.room_id].keys())
    if exits:
        lines.append("Exits: " + ", ".join(sorted(exits)))
    else:
        lines.append("Exits: none")

    if room.floor_item:
        item_id = room.floor_item
        if state.item_visibility.get(item_id, True) and not state.room_item_taken.get(room.room_id, False):
            item = world.items[item_id]
            lines.append(f"You see: {item.name}")

    if room.usable:
        u = room.usable
        ustate = state.usable_state.get(u.usable_id, {"locked": u.locked, "used": False})
        status = "open"
        if ustate.get("locked"):
            status = "locked"
        elif ustate.get("used"):
            status = "used"
        elif u.type == "Button":
            status = "unused"
        lines.append(f"Interactable: {u.name} ({status})")

    return "\n".join(lines)
