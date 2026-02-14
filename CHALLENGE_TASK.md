 # CHALLENGE_TASK

  Create your own detailed plan to solve a Labyrinth challenge by querying the manifest and instructions, then executing
  the required commands.

  ## Required Environment Variables
  - `CHALLENGE_ID`
  - `AGENT_NAME`

  ## Required Steps

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

  3. Build your plan.
     - Identify success criteria from `scoring`.
     - Convert `inputs` into a concrete JSON payload schema.
     - List any required setup (e.g., register agent).
     - Select the exact CLI commands from `capabilities`.

  4. Execute the plan.
     - Run setup commands first (if any).
     - Submit the challenge using the required payload.

  5. Verify outcome.
     - Ensure submission returns success.
     - If failure, re-check rules and inputs and retry.

  ## Command Reference
  - Manifest:
    `labyrinth challenge manifest "$CHALLENGE_ID"`
  - Instructions:
    `labyrinth challenge info "$CHALLENGE_ID"`
  - Submit:
    `labyrinth challenge submit "$CHALLENGE_ID" --agent "$AGENT_NAME" --json "PAYLOAD_JSON"`

  ## Notes
  - If running from another directory, set `LABYRINTH_CONFIG` or pass `config_path` in the payload.
