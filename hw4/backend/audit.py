"""Append-only audit trail of agent activity.

Every run of the shop assistant leaves one record in ``output/audit_trail.json``:
when it happened, what was asked, which tools were called with what arguments
and what came back, why the loop stopped, and how long it took.

Two properties the file is built to keep:

* **Append-only.** The existing records are read before anything is written and
  are always written back. There is no code path that empties the file. If it
  is ever found corrupt it is moved aside, not discarded.
* **No personal data.** A shopper is recorded as ``user_id`` or ``guest`` —
  never a name, never an email address. Arguments and results are truncated, so
  a long tool result cannot smuggle something unexpected into the file.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

# Arguments and results are summaries for an auditor to scan, not a second copy
# of the database.
MAX_FIELD = 220

# pydantic-ai delivers the structured answer through an internal tool. It is
# kept in `steps` so the trail is complete, but left out of `tools_called`,
# which is meant to read as the shop tools the agent actually reached for.
INTERNAL_TOOLS = {"final_result"}

_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _short(value: Any, limit: int = MAX_FIELD) -> str:
    """One readable line, truncated, whatever was passed in."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            text = json.dumps(value, default=str)
        except (TypeError, ValueError):
            text = str(value)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _load() -> list[dict[str, Any]]:
    """Every record written so far. Never returns an empty list on error."""
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        logging.warning("Audit trail was not a list; keeping it aside")
    except json.JSONDecodeError:
        logging.warning("Audit trail could not be parsed; keeping it aside")

    # Do not discard: move the old file out of the way so it can be recovered.
    spoiled = AUDIT_PATH.with_suffix(f".corrupt-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.json")
    shutil.copy2(AUDIT_PATH, spoiled)
    return []


def append(record: dict[str, Any]) -> None:
    """Add one record, keeping everything already written."""
    with _LOCK:
        records = _load()
        records.append(record)
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, indent=2), encoding="utf-8")
        tmp.replace(AUDIT_PATH)  # atomic, so a crash cannot truncate the trail


def steps_from(messages: list[Any]) -> list[dict[str, Any]]:
    """Read the tool calls and their results out of one agent run.

    Each call is matched to its own return by tool_call_id, so a step records
    what was asked of a tool and what that same call gave back.
    """
    calls: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for message in messages:
        for part in getattr(message, "parts", []):
            kind = type(part).__name__
            if kind == "ToolCallPart":
                key = getattr(part, "tool_call_id", None) or f"{part.tool_name}-{len(order)}"
                calls[key] = {
                    "tool": part.tool_name,
                    "args": _short(getattr(part, "args", None)),
                    "result": "",
                }
                order.append(key)
            elif kind == "ToolReturnPart":
                key = getattr(part, "tool_call_id", None)
                if key in calls:
                    calls[key]["result"] = _short(getattr(part, "content", None))

    return [
        {"step": i + 1, **calls[key]} for i, key in enumerate(order) if key in calls
    ]


def record_run(
    *,
    user_id: int | None,
    message: str,
    page: dict[str, Any] | None,
    steps: list[dict[str, Any]],
    stop_reason: str,
    reply: str,
    product_ids: list[str],
    model: str,
    seconds: float,
    requests: int | None = None,
) -> None:
    """Write one agent run to the trail."""
    append(
        {
            "time": _now(),
            # Identity is the key only. No name, no email: an audit file should
            # not become a second place where personal data lives.
            "shopper": f"user:{user_id}" if user_id else "guest",
            "model": model,
            "message": _short(message),
            "page": _short(page) if page else "",
            "steps": steps,
            "tools_called": [s["tool"] for s in steps if s["tool"] not in INTERNAL_TOOLS],
            "stop_reason": stop_reason,
            "model_requests": requests,
            "reply": _short(reply),
            "products_shown": product_ids,
            "duration_seconds": round(seconds, 2),
        }
    )
