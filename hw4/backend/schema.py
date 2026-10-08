"""Tables added for the Problem 9 usability features.

Run directly to apply:  python schema.py

Every statement is ``IF NOT EXISTS``, so running it twice is harmless and it
never touches the seeded ``catalogue``, ``inventory``, ``users`` or
``chat_messages`` tables.
"""

from __future__ import annotations

import db

STATEMENTS = [
    # Discounts Handsome Dan has offered, and whether the shopper took an
    # interest. `interested_at` is what makes this a record of interest rather
    # than just a log of offers.
    """
    CREATE TABLE IF NOT EXISTS discount_offers (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER NOT NULL REFERENCES users(id),
        code          TEXT    NOT NULL,
        percent       INTEGER NOT NULL,
        offered_at    TEXT    NOT NULL DEFAULT (datetime('now')),
        interested_at TEXT,
        interest_note TEXT,
        redeemed_at   TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_discount_offers_user ON discount_offers(user_id)",
    # A purchase, so a rating has something real to hang on.
    """
    CREATE TABLE IF NOT EXISTS purchases (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER NOT NULL REFERENCES users(id),
        product_id    TEXT    NOT NULL REFERENCES catalogue(product_id),
        size          TEXT    NOT NULL,
        price         REAL    NOT NULL,
        discount_code TEXT,
        created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id)",
    # One rating per purchase. CHECK keeps the 1-5 range a property of the
    # database, not just of the form.
    """
    CREATE TABLE IF NOT EXISTS product_ratings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id),
        product_id  TEXT    NOT NULL REFERENCES catalogue(product_id),
        purchase_id INTEGER REFERENCES purchases(id),
        stars       INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        UNIQUE (purchase_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_product_ratings_product ON product_ratings(product_id)",
]


def apply() -> None:
    with db.connect_rw() as conn:
        for statement in STATEMENTS:
            conn.execute(statement)
    print(f"Schema applied to {db.DB_PATH}")


if __name__ == "__main__":
    apply()
