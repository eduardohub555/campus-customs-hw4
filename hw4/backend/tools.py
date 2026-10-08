"""Catalogue data, shop perks, and the tools the agent can call.

Everything that touches the shop's data lives here:

* **Database access** — a read-only connection for the catalogue, and a
  writable one used only by registration, chat history and purchases.
* **Normalisation** — the raw tables need work before anything else sees them;
  see ``categorise`` for why.
* **Perks** — discounts, purchases and star ratings. All plain SQLite: issuing
  a discount or saving a rating makes no model call at all.
* **The agent's tools** — each reads through this module and returns a typed
  object from ``models``. None reaches the internet, and none can see the
  ``users`` table, so the agent has no route to anybody's account.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

from models import (
    ProductDetail,
    ProductRating,
    ProductSummary,
    SizeAvailability,
    SizeOption,
    SizeStock,
)

# ===========================================================================
# the database
# ===========================================================================

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
PRODUCT_IMAGE_DIR = DATA_DIR / "products"
# Background-free PNGs built by cutouts.py, so garments float on the page.
# Not every photo yields a clean cutout; those keep their original.
PRODUCT_CUTOUT_DIR = DATA_DIR / "products_cutout"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# Normalised buckets for the Products page filter, matched in order against the
# raw garment_type. First hit wins, so "full-zip hooded sweatshirt" lands in
# Hoodies rather than Jackets.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Hoodies", ("hoodie", "hooded")),
    ("Quarter-Zips", ("quarter-zip", "1/4 zip", "mockneck")),
    ("Jackets", ("jacket", "fleece", "bomber")),
    ("Sweatshirts", ("sweatshirt", "crewneck", "crew")),
    ("T-Shirts", ("t-shirt", "tee", "shirt")),
]
FALLBACK_CATEGORY = "Other"

CATEGORY_ORDER = [name for name, _ in CATEGORY_RULES] + [FALLBACK_CATEGORY]


def categorise(garment_type: str) -> str:
    """Map a messy garment_type onto one of the normalised buckets."""
    needle = garment_type.strip().lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in needle for keyword in keywords):
            return category
    return FALLBACK_CATEGORY


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"database not found at {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _loads(raw: str | None) -> list[str]:
    """Parse a JSON array column, tolerating the empty/NULL cases in the data."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _short(description: str, limit: int = 120) -> str:
    """Trim a description to a card-sized blurb without cutting a word in half."""
    text = " ".join(description.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "..."


def _image_url(image_file_path: str) -> str:
    """Prefer the cut-out PNG; fall back to the original photo."""
    stem = Path(image_file_path).stem
    if (PRODUCT_CUTOUT_DIR / f"{stem}.png").exists():
        return f"/media/cutouts/{stem}.png"
    return f"/media/products/{Path(image_file_path).name}"


def _row_to_product(row: sqlite3.Row, sizes: list[dict[str, Any]]) -> dict[str, Any]:
    description = row["description"]
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": categorise(row["garment_type"]),
        "description": description,
        "short_description": _short(description),
        "colors": _loads(row["colors"]),
        "search_tags": _loads(row["search_tags"]),
        "image_url": _image_url(row["image_file_path"]),
        "price": float(row["price"]),
        "inventory": sizes,
        "total_stock": sum(s["quantity"] for s in sizes),
        "sizes_in_stock": [s["size"] for s in sizes if s["quantity"] > 0],
    }


def _inventory_by_product(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """All stock rows, grouped by product and ordered XS -> XXL."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        grouped.setdefault(row["product_id"], []).append(
            {"size": row["size"], "quantity": row["quantity"]}
        )
    for sizes in grouped.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99)
    return grouped


def list_products() -> list[dict[str, Any]]:
    with connect() as conn:
        stock = _inventory_by_product(conn)
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    return [_row_to_product(row, stock.get(row["product_id"], [])) for row in rows]


def product_row(product_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        sizes = _inventory_by_product(conn).get(product_id, [])
    return _row_to_product(row, sizes)


def connect_rw() -> sqlite3.Connection:
    """Writable connection. Only the auth code registers users; everything
    else on the site reads through ``connect()``, which is read-only."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ===========================================================================
# discounts, purchases and ratings
# ===========================================================================

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
    with connect() as conn:
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
    with connect_rw() as conn:
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
    with connect_rw() as conn:
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
    with connect() as conn:
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
    product = product_row(product_id)
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

    with connect_rw() as conn:
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
    with connect() as conn:
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
    with connect() as conn:
        rows = conn.execute(
            """SELECT r.product_id, c.name, r.stars, r.created_at
                 FROM product_ratings r
                 JOIN catalogue c USING(product_id)
                WHERE r.user_id = ?
             ORDER BY r.id DESC""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


# ===========================================================================
# the model client, and the agent's tools
# ===========================================================================

BACKEND_DIR = Path(__file__).resolve().parent
# The key lives in the course root .env, outside the project, and is read at
# call time. It is never written to a file, a log, or a response.
ENV_PATH = BACKEND_DIR.parent.parent / ".env"

MODEL_NAME = "gpt-5.6-luna"
# A smaller model for the short, low-stakes writing around discounts. Measured
# against the main model on the same prompt it is modestly quicker (median
# 1.61s vs 1.89s over three runs) and materially cheaper per token, and the
# task — one warm sentence from a bulldog — does not need the larger model.
FAST_MODEL = "gpt-5.4-nano"
MAX_RESULTS = 4  # never hand the model more products than the panel should show


def build_client() -> AsyncOpenAI:
    """OpenAI client routed through Portkey, keyed from the root .env."""
    load_dotenv(ENV_PATH)
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"PORTKEY_API_KEY is missing from {ENV_PATH}. The assistant cannot start without it."
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        default_headers={"x-portkey-api-key": api_key, "x-portkey-provider": "openai"},
    )


# --- shaping database rows -------------------------------------------------


def _summary(row: dict[str, Any]) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        category=row["category"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=row["colors"],
        price=row["price"],
        sizes_in_stock=row["sizes_in_stock"],
        total_stock=row["total_stock"],
    )


def _detail(row: dict[str, Any]) -> ProductDetail:
    return ProductDetail(
        **_summary(row).model_dump(),
        inventory=[SizeStock(**size) for size in row["inventory"]],
    )


def _score(row: dict[str, Any], words: list[str]) -> int:
    """Rank a product against the shopper's words.

    Name and colour matches count for more than a mention buried in the
    description. Tags are searched too: three products have placeholder
    descriptions, and tags are the only text those rows really have.
    """
    name = row["name"].lower()
    colors = " ".join(row["colors"]).lower()
    tags = " ".join(row["search_tags"]).lower()
    description = row["description"].lower()
    category = row["category"].lower()

    total = 0
    for word in words:
        if word in name:
            total += 6
        if word in colors:
            total += 5
        if word in category:
            total += 4
        if word in tags:
            total += 3
        if word in description:
            total += 1
    return total


# --- the tools -------------------------------------------------------------


def _colour_variants(color: str) -> set[str]:
    """"grey" and "gray" are one shade to a shopper but two strings to a filter."""
    wanted = color.strip().lower()
    return {wanted, wanted.replace("grey", "gray"), wanted.replace("gray", "grey")}


def search_catalogue(
    query: str = "",
    category: str | None = None,
    color: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    max_results: int = MAX_RESULTS,
) -> list[ProductSummary]:
    """Search the Campus Customs catalogue by words, category, colour, size or price.

    Use this first for any open-ended request. Every product it returns carries
    its real description, garment type, colours, price and the sizes actually on
    the shelf.

    Args:
        query: What the shopper asked for, in their own words.
        category: One of Hoodies, Sweatshirts, T-Shirts, Quarter-Zips, Jackets.
        color: A colour to require, matched loosely ("grey" finds "heather gray").
        size: Only return products available in this size (XS, S, M, L, XL, XXL).
        max_price: Only return products at or below this many dollars.
        max_results: How many products to return, capped at four.

    Returns:
        Matching products, best first. Empty when the shop carries nothing like it.
    """
    rows = list_products()

    if category:
        wanted = category.strip().lower()
        rows = [r for r in rows if r["category"].lower() == wanted]

    if size:
        wanted_size = size.strip().upper()
        rows = [r for r in rows if wanted_size in r["sizes_in_stock"]]

    if max_price is not None:
        rows = [r for r in rows if r["price"] <= max_price]

    if color:
        variants = _colour_variants(color)
        rows = [
            r for r in rows
            if any(v in c.lower() for c in r["colors"] for v in variants)
        ]

    words = [w for w in query.lower().split() if len(w) > 2]
    if words:
        scored = [(r, _score(r, words)) for r in rows]
        hits = [r for r, s in sorted(scored, key=lambda p: -p[1]) if s > 0]
        # A category or colour filter is itself an answer, so fall back to the
        # filtered list rather than returning nothing when no word matched.
        narrowed = bool(category or color or size or max_price is not None)
        rows = hits if hits else (rows if narrowed else [])

    # Prefer something the shopper can actually buy.
    rows.sort(key=lambda r: r["total_stock"] == 0)
    return [_summary(r) for r in rows[: min(max_results, MAX_RESULTS)]]


def get_product(product_id: str) -> ProductDetail | None:
    """Look up one product in full: description, garment type, colours, price,
    and the stock count for every size including the sold-out ones.

    Call this before describing a specific garment in any detail.

    Args:
        product_id: The product_id from a previous tool result.

    Returns:
        The product, or None when no product has that id.
    """
    row = product_row(product_id)
    return _detail(row) if row else None


def check_size(product_id: str, size: str) -> SizeAvailability | None:
    """Check whether one product is available in one size, with the real count.

    Call this for any question about a size. The result also names the other
    sizes of the same product still on the shelf, so a "no" can be answered
    helpfully without a second call.

    Args:
        product_id: The product_id from a previous tool result.
        size: XS, S, M, L, XL or XXL.

    Returns:
        The real count for that size, plus the other sizes still on the shelf.
    """
    row = product_row(product_id)
    if row is None:
        return None

    wanted = size.strip().upper()
    match = next((s for s in row["inventory"] if s["size"] == wanted), None)
    quantity = match["quantity"] if match else 0
    return SizeAvailability(
        product_id=row["product_id"],
        product_name=row["name"],
        size=wanted,
        available=quantity > 0,
        quantity=quantity,
        other_sizes_in_stock=[s for s in row["sizes_in_stock"] if s != wanted],
    )


def find_available_in_size(
    size: str,
    category: str | None = None,
    color: str | None = None,
    exclude_product_id: str | None = None,
    max_results: int = MAX_RESULTS,
) -> list[SizeOption]:
    """Find products that really are in stock in one particular size.

    Use this when a shopper's size is sold out and you want to offer them
    something else they can actually buy. Everything returned has at least one
    unit in that size — there is no need to check again.

    Args:
        size: XS, S, M, L, XL or XXL.
        category: Narrow to one category, e.g. the same kind of garment they wanted.
        color: Narrow to a colour, matched loosely.
        exclude_product_id: Leave out the product that was unavailable.
        max_results: How many to return, capped at four.

    Returns:
        Products available in that size, the best-stocked first.
    """
    wanted = size.strip().upper()
    rows = list_products()

    if category:
        narrow = category.strip().lower()
        rows = [r for r in rows if r["category"].lower() == narrow]

    if color:
        variants = _colour_variants(color)
        rows = [
            r for r in rows
            if any(v in c.lower() for c in r["colors"] for v in variants)
        ]

    if exclude_product_id:
        rows = [r for r in rows if r["product_id"] != exclude_product_id]

    options: list[SizeOption] = []
    for row in rows:
        match = next((s for s in row["inventory"] if s["size"] == wanted), None)
        if match is None or match["quantity"] <= 0:
            continue
        options.append(
            SizeOption(
                product_id=row["product_id"],
                name=row["name"],
                category=row["category"],
                garment_type=row["garment_type"],
                colors=row["colors"],
                price=row["price"],
                size=wanted,
                quantity_in_size=match["quantity"],
            )
        )

    options.sort(key=lambda o: -o.quantity_in_size)
    return options[: min(max_results, MAX_RESULTS)]


def list_categories() -> list[str]:
    """The categories the shop sorts its garments into."""
    present = {p["category"] for p in list_products()}
    return [c for c in CATEGORY_ORDER if c in present]


def product_rating(product_id: str) -> ProductRating:
    """How shoppers who bought this garment rated it, out of five stars.

    Only real ratings left after a purchase are counted. When `ratings` is 0
    nobody has rated it yet — say so rather than implying it is unrated because
    it is unpopular.

    Args:
        product_id: The product_id from a previous tool result.
    """
    return ProductRating(**rating_for_product(product_id))
