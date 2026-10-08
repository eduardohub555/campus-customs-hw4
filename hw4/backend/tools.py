"""Tools the shop assistant can call, and the client that reaches the model.

Every tool reads the Campus Customs database through ``db`` and returns a typed
object from ``models``. Nothing here reaches the internet, and nothing here can
see the ``users`` table — the agent has no route to anybody's account.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

import db
import perks
from models import (
    ProductDetail,
    ProductRating,
    ProductSummary,
    SizeAvailability,
    SizeOption,
    SizeStock,
)

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
    rows = db.list_products()

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
    row = db.get_product(product_id)
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
    row = db.get_product(product_id)
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
    rows = db.list_products()

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
    present = {p["category"] for p in db.list_products()}
    return [c for c in db.CATEGORY_ORDER if c in present]


def product_rating(product_id: str) -> ProductRating:
    """How shoppers who bought this garment rated it, out of five stars.

    Only real ratings left after a purchase are counted. When `ratings` is 0
    nobody has rated it yet — say so rather than implying it is unrated because
    it is unpopular.

    Args:
        product_id: The product_id from a previous tool result.
    """
    return ProductRating(**perks.rating_for_product(product_id))
