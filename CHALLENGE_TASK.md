# CHALLENGE_TASK

## Purpose
Create your own detailed plan to solve a Labyrinth challenge by querying the manifest, instructions, and challenge GUID tables, then executing the required commands.

## Required Environment Variables
- `CHALLENGE_ID`
- `AGENT_NAME`

## Required Steps
1. Fetch the challenge manifest.
   - Command:
     `labyrinth challenge manifest "$CHALLENGE_ID"`
   - Extract:
     - goal
     - rules
     - inputs
     - scoring
     - capabilities

2. Fetch human instructions.
   - Command:
     `labyrinth challenge info "$CHALLENGE_ID"`

3. Locate the challenge GUID.
   - Option A (recommended): Scorecard table:
     `labyrinth challenge submit scorecard --agent "$AGENT_NAME" --json "{}"`
   - Option B: Challenge list table:
     `labyrinth challenge list`
   - Extract the GUID for `CHALLENGE_ID`.

4. Build your plan.
   - Identify success criteria from `scoring`.
   - Convert `inputs` into a concrete JSON payload schema.
   - Include `challenge_guid` from the tables in your payload.
   - List any required setup (e.g., register agent).
   - Select the exact CLI commands from `capabilities`.

5. Execute the plan.
   - Run setup commands first (if any).
   - Submit the challenge using the required payload.

6. Verify outcome.
   - Ensure submission returns success.
   - If failure, re-check rules and inputs and retry.

## Command Reference
- Manifest:
  `labyrinth challenge manifest "$CHALLENGE_ID"`
- Instructions:
  `labyrinth challenge info "$CHALLENGE_ID"`
- Submit:
  `labyrinth challenge submit "$CHALLENGE_ID" --agent "$AGENT_NAME" --json "PAYLOAD_JSON"`
  - Include `"challenge_guid":"<GUID_FROM_TABLE>"` in the payload.

## Notes
- If running from another directory, set `LABYRINTH_CONFIG` or pass `config_path` in the payload.
