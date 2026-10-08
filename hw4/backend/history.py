"""Chat history for signed-in shoppers.

Writes to the ``chat_messages`` table that was already in the seeded database:
one row per turn, filed under ``user_id``.

Guests are never written. Every function here takes a ``user_id``; there is no
code path that stores a turn without one, so an anonymous conversation leaves
nothing behind by construction rather than by remembering to check.
"""

from __future__ import annotations

import json
from typing import Any

import db

# How much of a returning conversation to replay to the model. Twelve rows is
# six exchanges — enough to remember a stated preference or the garment someone
# was looking at, without the prompt growing without limit.
REPLAY_LIMIT = 12

# How much to show the shopper when the panel reopens.
DISPLAY_LIMIT = 40


def record_turn(
    user_id: int,
    message: str,
    reply: str,
    products: list[dict[str, Any]] | None = None,
) -> None:
    """Store one exchange: what the shopper asked, and what we answered.

    ``products_json`` holds the cards that went with the answer, matching how
    the seeded rows use that column. It is what lets a later conversation know
    which garments were already shown.
    """
    shown = json.dumps(products or [])
    with db.connect_rw() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, shown),
        )


def _rows(user_id: int, limit: int) -> list[dict[str, Any]]:
    """The most recent `limit` turns, returned oldest-first."""
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT role, content, products_json, created_at
                 FROM chat_messages
                WHERE user_id = ?
             ORDER BY id DESC
                LIMIT ?""",
            (user_id, limit),
        ).fetchall()

    turns: list[dict[str, Any]] = []
    for row in reversed(rows):
        try:
            products = json.loads(row["products_json"]) if row["products_json"] else []
        except json.JSONDecodeError:
            products = []
        turns.append(
            {
                "role": row["role"],
                "content": row["content"],
                "products": products if isinstance(products, list) else [],
                "created_at": row["created_at"],
            }
        )
    return turns


def for_display(user_id: int) -> list[dict[str, Any]]:
    """The conversation to put back in the panel when the shopper returns."""
    return _rows(user_id, DISPLAY_LIMIT)


def for_replay(user_id: int) -> list[dict[str, Any]]:
    """The recent turns to give the model as context for the next answer."""
    return _rows(user_id, REPLAY_LIMIT)


def summarise(user_id: int) -> str | None:
    """A short note on what this shopper has looked at before.

    Read out of the stored `products_json` rather than guessed at, so it is a
    record of what was actually shown: the garment types, the colours and the
    sizes that were on those cards. The model turns this into memory such as
    "you were looking at crewnecks last time".
    """
    categories: list[str] = []
    colors: list[str] = []
    for turn in _rows(user_id, DISPLAY_LIMIT):
        for product in turn["products"]:
            if isinstance(product, dict):
                if product.get("category"):
                    categories.append(str(product["category"]))
                for color in product.get("colors") or []:
                    colors.append(str(color))

    if not categories and not colors:
        return None

    def top(values: list[str], count: int) -> list[str]:
        seen: dict[str, int] = {}
        for value in values:
            seen[value] = seen.get(value, 0) + 1
        return [v for v, _ in sorted(seen.items(), key=lambda p: -p[1])][:count]

    parts = []
    if categories:
        parts.append("categories: " + ", ".join(top(categories, 3)))
    if colors:
        parts.append("colours: " + ", ".join(top(colors, 4)))
    return "; ".join(parts)


def clear(user_id: int) -> int:
    """Forget a shopper's conversation. Returns how many rows were removed."""
    with db.connect_rw() as conn:
        cursor = conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        return cursor.rowcount
