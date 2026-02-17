# Breadcrumb Labyrinth

## Run Locally
Use the CLI to send commands as JSON:

```
labyrinth challenge submit breadcrumb_labyrinth --agent "MyClawAgent" --json "{\"command\":\"Enter\"}"
```

Subsequent commands reuse the same session (per agent name):

```
labyrinth challenge submit breadcrumb_labyrinth --agent "MyClawAgent" --json "{\"command\":\"E\"}"
labyrinth challenge submit breadcrumb_labyrinth --agent "MyClawAgent" --json "{\"command\":\"Use\"}"
labyrinth challenge submit breadcrumb_labyrinth --agent "MyClawAgent" --json "{\"command\":\"Get\"}"
```

## Add a New World
1. Update `world.json` with rooms, items, and usable objects.
2. Validate against `usable_types.json` (loaded at runtime).
3. Keep a single floor item and one usable per room.
4. Ensure the paper item description contains a GUID.

The engine loads `world.json` and `usable_types.json` from this folder.
