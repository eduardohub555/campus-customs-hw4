"""Read-only access to the Campus Customs SQLite database.

Problem 2 found three things in the data that this layer smooths over before the
front end ever sees a product:

* ``garment_type`` has 22 spellings for 102 products, so an exact-match filter
  silently drops results. ``category`` is a normalised bucket built from it.
* ``colors`` and ``search_tags`` are JSON stored in TEXT columns.
* 145 of 612 size rows are sold out, so stock has to be reported per size.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

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


def get_product(product_id: str) -> dict[str, Any] | None:
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
