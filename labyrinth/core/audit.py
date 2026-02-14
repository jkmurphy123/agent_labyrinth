from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime


def append_audit(event: dict[str, Any], path: str = "./labyrinth_audit.jsonl") -> None:
    event = dict(event)
    event["ts"] = datetime.utcnow().isoformat() + "Z"
    p = Path(path)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
