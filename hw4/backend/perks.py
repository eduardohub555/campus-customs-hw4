"""Discounts and ratings.

Two things worth saying about speed, because Problem 9 asks for it:

* Every function here is a plain SQLite read or write. Issuing a discount,
  recording interest in one, and saving a rating involve **no model call at
  all** — which is faster and cheaper than any model, however small.
* The one place a model genuinely helps is writing Handsome Dan's line when he
  offers the discount. That runs on the light model (``tools.FAST_MODEL``),
  not the shop assistant's.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import db

DISCOUNT_PERCENT = 10

# How long an offer stands, and how long before Handsome Dan offers again. A
# fresh offer on every visit would make the gesture worthless; this is the
# "every now and then" the feature asks for.
OFFER_VALID_HOURS = 72
OFFER_COOLDOWN_HOURS = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# discounts
# --------------------------------------------------------------------------


def _row_to_offer(row: Any) -> dict[str, Any]:
    offered = _parse(row["offered_at"])
    expires = offered + timedelta(hours=OFFER_VALID_HOURS) if offered else None
    return {
        "id": row["id"],
        "code": row["code"],
        "percent": row["percent"],
        "offered_at": row["offered_at"],
        "interested_at": row["interested_at"],
        "redeemed_at": row["redeemed_at"],
        "expired": bool(expires and expires < _now()),
    }


def latest_offer(user_id: int) -> dict[str, Any] | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM discount_offers WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return _row_to_offer(row) if row else None


def active_offer(user_id: int) -> dict[str, Any] | None:
    """The shopper's usable discount, if they have one."""
    offer = latest_offer(user_id)
    if offer and not offer["expired"] and not offer["redeemed_at"]:
        return offer
    return None


def offer_due(user_id: int) -> bool:
    """Is Handsome Dan due to offer this shopper a discount?

    True when they have no usable offer and enough time has passed since the
    last one, so the gesture stays occasional rather than constant.
    """
    offer = latest_offer(user_id)
    if offer is None:
        return True
    if active_offer(user_id):
        return False
    offered = _parse(offer["offered_at"])
    if offered is None:
        return True
    return _now() - offered > timedelta(hours=OFFER_COOLDOWN_HOURS)


def issue_offer(user_id: int) -> dict[str, Any]:
    """Create a discount for this shopper, or return the one they already have."""
    existing = active_offer(user_id)
    if existing:
        return existing

    code = f"DAN{DISCOUNT_PERCENT}-{secrets.token_hex(3).upper()}"
    with db.connect_rw() as conn:
        conn.execute(
            "INSERT INTO discount_offers (user_id, code, percent) VALUES (?, ?, ?)",
            (user_id, code, DISCOUNT_PERCENT),
        )
    return active_offer(user_id) or {"code": code, "percent": DISCOUNT_PERCENT}


def record_interest(user_id: int, note: str | None = None) -> bool:
    """Note that this shopper took an interest in their discount.

    Called when they ask the assistant about it or press "Tell me more". This
    is the record the agent is asked to keep in mind for future offers.
    """
    offer = latest_offer(user_id)
    if offer is None:
        return False
    with db.connect_rw() as conn:
        conn.execute(
            """UPDATE discount_offers
                  SET interested_at = COALESCE(interested_at, datetime('now')),
                      interest_note = COALESCE(?, interest_note)
                WHERE id = ?""",
            (note, offer["id"]),
        )
    return True


def interest_summary(user_id: int) -> str | None:
    """What the agent is told about this shopper's history with discounts."""
    with db.connect() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS offered,
                      SUM(interested_at IS NOT NULL) AS interested,
                      SUM(redeemed_at IS NOT NULL)   AS redeemed
                 FROM discount_offers WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

    if not row or not row["offered"]:
        return None

    parts = [f"offered {row['offered']}"]
    if row["interested"]:
        parts.append(f"asked about {row['interested']}")
    if row["redeemed"]:
        parts.append(f"used {row['redeemed']}")

    active = active_offer(user_id)
    parts.append(
        f"currently holds {active['percent']}% code {active['code']}"
        if active
        else "holds no usable code"
    )
    return "; ".join(parts)


# --------------------------------------------------------------------------
# purchases and ratings
# --------------------------------------------------------------------------


def record_purchase(
    user_id: int,
    product_id: str,
    size: str,
    stars: int | None = None,
    use_discount: bool = False,
) -> dict[str, Any]:
    """Record a purchase and, when given, the rating that came with it.

    The star rating is saved against the purchase, so a rating in the database
    is always traceable to the moment someone actually bought the garment.
    """
    product = db.get_product(product_id)
    if product is None:
        raise ValueError(f"no product named {product_id!r}")

    wanted = size.strip().upper()
    if wanted not in product["sizes_in_stock"]:
        raise ValueError(f"{product['name']} is not available in {wanted}")

    if stars is not None and not 1 <= stars <= 5:
        raise ValueError("A rating must be between 1 and 5 stars.")

    offer = active_offer(user_id) if use_discount else None
    price = product["price"]
    if offer:
        price = round(price * (100 - offer["percent"]) / 100, 2)

    with db.connect_rw() as conn:
        cursor = conn.execute(
            """INSERT INTO purchases (user_id, product_id, size, price, discount_code)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, product_id, wanted, price, offer["code"] if offer else None),
        )
        purchase_id = cursor.lastrowid

        if offer:
            conn.execute(
                "UPDATE discount_offers SET redeemed_at = datetime('now') WHERE id = ?",
                (offer["id"],),
            )
        if stars is not None:
            conn.execute(
                """INSERT INTO product_ratings (user_id, product_id, purchase_id, stars)
                   VALUES (?, ?, ?, ?)""",
                (user_id, product_id, purchase_id, stars),
            )

    return {
        "purchase_id": purchase_id,
        "product_id": product_id,
        "product_name": product["name"],
        "size": wanted,
        "price_paid": price,
        "list_price": product["price"],
        "discount_code": offer["code"] if offer else None,
        "stars": stars,
    }


def rating_for_product(product_id: str) -> dict[str, Any]:
    """The average rating a garment has earned, for the agent and the page."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, AVG(stars) AS avg FROM product_ratings WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    count = row["n"] or 0
    return {
        "product_id": product_id,
        "ratings": count,
        "average": round(row["avg"], 1) if count else None,
    }


def ratings_by_user(user_id: int) -> list[dict[str, Any]]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT r.product_id, c.name, r.stars, r.created_at
                 FROM product_ratings r
                 JOIN catalogue c USING(product_id)
                WHERE r.user_id = ?
             ORDER BY r.id DESC""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]
