# Labyrinth (Phase 0)

## Architecture
- `labyrinth/core/` contains the framework: config loading, sqlite persistence, plugin registry, leaderboard.
- `labyrinth/plugins/` contains challenge plugins. Each plugin has:
  - `plugin.py` implementing `get_instructions()` and `submit()`
  - `config.yaml` defining points and prompt text

## Config
- `labyrinth.yaml` is the master config listing enabled plugins and their config paths.

## Data
SQLite tables:
- `agents` (unique name)
- `runs` (agent_id, challenge_id, status, points, evidence_json)

## Phase 0 Goal
- Prove plugin mechanism works end-to-end with a single plugin (`registration`) and a functioning leaderboard.

## How to add a plugin
1. Create folder `labyrinth/plugins/<id>/`
2. Add `plugin.py` + `config.yaml`
3. Add plugin entry to `labyrinth.yaml`
4. Implement `submit(agent_name, submission, cfg)` returning a `ChallengeResult`