"""Campus Customs API — the file to run with uvicorn.

    cd backend
    uvicorn main:app --reload --reload-include "*.md" --port 8000

Holds the HTTP surface and the shop's own machinery: accounts and password
hashing, the chat history of signed-in shoppers, Handsome Dan's discount line,
and the two one-off setup commands.

Setup commands, run from this directory:

    python main.py --init-db     create the discount, purchase and rating tables
    python main.py --cutouts     lift the product photos off their backgrounds
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import sqlite3
import sys
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageFilter
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import agent as shop_agent
import tools
from models import (
    ChatHistory,
    ChatRequest,
    ChatResponse,
    DiscountOffer,
    ProductCard,
    ProductRating,
    PurchaseReceipt,
    PurchaseRequest,
    StoredTurn,
)

# ===========================================================================
# accounts and passwords
# ===========================================================================

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 8  # 16 hex characters, matching the seeded rows
MIN_PASSWORD_LENGTH = 8

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DIGIT_PATTERN = re.compile(r"\d")
# "Special" means anything that is not a letter, a digit or a space: . - ! # and so on.
SPECIAL_PATTERN = re.compile(r"[^A-Za-z0-9\s]")

# Sessions live in memory: a restart signs everybody out. Good enough for the
# course project, and it keeps tokens out of the database entirely.
_SESSIONS: dict[str, int] = {}


class AuthError(Exception):
    """Raised with a message that is safe to show the person signing in."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------
# passwords
# --------------------------------------------------------------------------

def _derive(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()


def hash_password(password: str) -> str:
    """Derive a storable hash with a fresh random salt."""
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_derive(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash.

    Comparison is constant-time so a wrong password cannot be narrowed down by
    timing, and case-sensitive because the derivation is over the exact bytes.
    """
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(_derive(password, salt), expected)


# A hash of a value nobody can log in with. Verifying against it when an email
# is unknown keeps the failed-login timing the same either way, so the response
# time cannot be used to discover which emails have accounts.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def _clean_email(email: str) -> str:
    """Emails are matched case-insensitively; passwords never are."""
    value = email.strip().lower()
    if not EMAIL_PATTERN.match(value):
        raise AuthError("That does not look like an email address.")
    return value


def _clean_name(value: str, field: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise AuthError(f"{field} is required.")
    return cleaned


def _check_password(password: str, confirmation: str) -> None:
    if password != confirmation:
        # Exact string comparison, so "Password" and "password" do not match.
        raise AuthError("The two passwords do not match.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not DIGIT_PATTERN.search(password):
        raise AuthError("Password must include at least one number.")
    if not SPECIAL_PATTERN.search(password):
        raise AuthError("Password must include at least one special character, such as a period.")


# --------------------------------------------------------------------------
# users
# --------------------------------------------------------------------------

def _public(row: sqlite3.Row) -> dict[str, Any]:
    """The user fields the browser is allowed to see. Never the hash."""
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "first_name": row["first_name"] or row["name"].split(" ")[0],
        "last_name": row["last_name"] or "",
        "created_at": row["created_at"],
    }


def register_user(
    first_name: str, last_name: str, email: str, password: str, confirm_password: str
) -> tuple[str, dict[str, Any]]:
    first = _clean_name(first_name, "First name")
    last = _clean_name(last_name, "Last name")
    address = _clean_email(email)
    _check_password(password, confirm_password)

    with tools.connect_rw() as conn:
        taken = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = ?", (address,)
        ).fetchone()
        if taken:
            raise AuthError("An account already uses that email address.", status=409)

        cursor = conn.execute(
            """INSERT INTO users (name, email, password_hash, first_name, last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (f"{first} {last}", address, hash_password(password), first, last),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()

    return _open_session(row["id"]), _public(row)


def sign_in(email: str, password: str) -> tuple[str, dict[str, Any]]:
    address = email.strip().lower()
    with tools.connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (address,)
        ).fetchone()

    if row is None:
        verify_password(password, _DUMMY_HASH)  # keep the timing even
        raise AuthError("Email or password is incorrect.", status=401)
    if not verify_password(password, row["password_hash"]):
        raise AuthError("Email or password is incorrect.", status=401)

    return _open_session(row["id"]), _public(row)


# --------------------------------------------------------------------------
# sessions
# --------------------------------------------------------------------------

def _open_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = user_id
    return token


def current_user(token: str | None) -> dict[str, Any] | None:
    """Resolve a bearer token to a user, or None if it is not a live session."""
    if not token:
        return None
    user_id = _SESSIONS.get(token)
    if user_id is None:
        return None
    with tools.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        _SESSIONS.pop(token, None)
        return None
    return _public(row)


def end_session(token: str | None) -> None:
    if token:
        _SESSIONS.pop(token, None)

# ===========================================================================
# chat history for signed-in shoppers
# ===========================================================================

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
    with tools.connect_rw() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, shown),
        )


def _history_rows(user_id: int, limit: int) -> list[dict[str, Any]]:
    """The most recent `limit` turns, returned oldest-first."""
    with tools.connect() as conn:
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


def history_for_display(user_id: int) -> list[dict[str, Any]]:
    """The conversation to put back in the panel when the shopper returns."""
    return _history_rows(user_id, DISPLAY_LIMIT)


def history_for_replay(user_id: int) -> list[dict[str, Any]]:
    """The recent turns to give the model as context for the next answer."""
    return _history_rows(user_id, REPLAY_LIMIT)


def summarise_history(user_id: int) -> str | None:
    """A short note on what this shopper has looked at before.

    Read out of the stored `products_json` rather than guessed at, so it is a
    record of what was actually shown: the garment types, the colours and the
    sizes that were on those cards. The model turns this into memory such as
    "you were looking at crewnecks last time".
    """
    categories: list[str] = []
    colors: list[str] = []
    for turn in _history_rows(user_id, DISPLAY_LIMIT):
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


def clear_history(user_id: int) -> int:
    """Forget a shopper's conversation. Returns how many rows were removed."""
    with tools.connect_rw() as conn:
        cursor = conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        return cursor.rowcount

# ===========================================================================
# Handsome Dan
# ===========================================================================

DAN_INSTRUCTIONS = """
You are Handsome Dan, the Yale bulldog, greeting a shopper at Campus Customs.

Write one warm, dignified sentence offering them the discount you are given.
You are a bulldog of some standing: pleased to see them, never yappy.

Rules you may not break:
- State the percentage exactly as given. Never any other number.
- Do not mention a product, a price, a size, or anything about stock.
- Do not claim the offer is scarce, expiring soon, or exclusive.
- No emoji, no exclamation marks, no sales language.
- One sentence. Thirty words at most.
""".strip()


class DanLine(BaseModel):
    line: str = Field(description="One warm sentence offering the discount.")


def _dan_fallback(first_name: str | None, percent: int) -> str:
    who = f"{first_name}, " if first_name else ""
    return (
        f"Good to see you, {who}and because you are one of ours, "
        f"here is {percent}% off whatever you choose today."
    )


async def dan_greeting(first_name: str | None, percent: int) -> str:
    """One line from Handsome Dan offering `percent`% off."""
    try:
        model = OpenAIResponsesModel(
            tools.FAST_MODEL, provider=OpenAIProvider(openai_client=tools.build_client())
        )
        agent = Agent(model, output_type=DanLine, instructions=DAN_INSTRUCTIONS)
        who = first_name or "a Yale shopper"
        result = await agent.run(
            f"The shopper is {who}. The discount is {percent} percent off.",
            usage_limits=UsageLimits(request_limit=2),
        )
        line = result.output.line.strip()
        # Trust nothing: if the model named a different number, use our words.
        if str(percent) not in line:
            logging.warning("Handsome Dan's line omitted the discount percentage; using the written one")
            return _dan_fallback(first_name, percent)
        return line
    except Exception:
        logging.warning("Handsome Dan's line fell back to the written one", exc_info=False)
        return _dan_fallback(first_name, percent)

# ===========================================================================
# one-off setup: tables and product cutouts
# ===========================================================================

SCHEMA_STATEMENTS = [
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


def apply_schema() -> None:
    with tools.connect_rw() as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
    print(f"Schema applied to {tools.DB_PATH}")



SOURCE_DIR = tools.PRODUCT_IMAGE_DIR
OUTPUT_DIR = tools.DATA_DIR / "products_cutout"

# How far a pixel may drift from the corner colour and still count as
# background. Studio backdrops are not perfectly flat, so some tolerance is
# needed; too much and the garment's own shadows start to dissolve.
TOLERANCE = 42

# Tolerances to try, loosest first. A photo with a glow or a textured edge
# bleeding off the garment lets a loose flood run inward and eat part of the
# garment; tightening the tolerance stops the leak at the cost of leaving a
# little backdrop behind, which is the better trade.
TOLERANCE_LADDER = (42, 30, 20, 12)


def _is_flat_backdrop(image: Image.Image) -> tuple[bool, tuple[int, int, int]]:
    """Do the four corners agree on a colour? If so, that is the backdrop."""
    w, h = image.size
    corners = [
        image.getpixel((2, 2)),
        image.getpixel((w - 3, 2)),
        image.getpixel((2, h - 3)),
        image.getpixel((w - 3, h - 3)),
    ]
    corners = [c[:3] for c in corners]
    first = corners[0]
    agree = all(
        max(abs(a - b) for a, b in zip(first, other)) <= TOLERANCE for other in corners[1:]
    )
    return agree, first


def _cut_out(path: Path) -> Image.Image | None:
    """Return the garment on a transparent background, or None to leave it be."""
    image = Image.open(path).convert("RGB")
    flat, backdrop = _is_flat_backdrop(image)
    if not flat:
        return None

    for tolerance in TOLERANCE_LADDER:
        cut = _cut_attempt(image, tolerance)
        if cut is not None:
            return cut
    return None


def _cut_attempt(image: Image.Image, tolerance: int) -> Image.Image | None:
    """One pass at the cutout with a given flood tolerance."""

    # Flood from every border pixel on a scratch copy, painting the background
    # a colour that cannot occur naturally, then read that back as the mask.
    MARKER = (255, 0, 255)
    scratch = image.copy()
    w, h = scratch.size
    from PIL import ImageDraw

    seeds = (
        [(x, 0) for x in range(0, w, 8)]
        + [(x, h - 1) for x in range(0, w, 8)]
        + [(0, y) for y in range(0, h, 8)]
        + [(w - 1, y) for y in range(0, h, 8)]
    )
    for seed in seeds:
        if scratch.getpixel(seed) == MARKER:
            continue
        ImageDraw.floodfill(scratch, seed, MARKER, thresh=tolerance)

    # Opaque everywhere except where the flood reached.
    mask = Image.new("L", image.size, 255)
    mask.putdata([0 if pixel == MARKER else 255 for pixel in scratch.convert("RGB").getdata()])

    # Pull the mask in by a pixel. A photo shot against black has a faint light
    # rim where the garment meets the backdrop; left in, it reads as a white
    # halo once the black behind it is gone. Eroding trims that fringe.
    mask = mask.filter(ImageFilter.MinFilter(3))

    # Then an opening — erode, dilate — to drop small islands of leftover
    # backdrop that the flood could not reach, without shrinking the garment.
    mask = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))

    # Then soften the alpha only, to take the staircase off the edge.
    mask = mask.filter(ImageFilter.GaussianBlur(0.7))

    # Quality gate. Some photos have a glow or texture bleeding off the garment
    # into the backdrop; the flood follows it inward and eats part of the
    # garment itself. Backdrop belongs at the edges, so the test is simple:
    # look at the middle of the frame, where the garment is. If much of that
    # went transparent, the flood leaked and the original photo is better than
    # a damaged cutout.
    w, h = image.size
    centre = mask.crop((int(w * 0.32), int(h * 0.32), int(w * 0.68), int(h * 0.68)))
    centre_pixels = list(centre.getdata())
    removed = sum(1 for a in centre_pixels if a < 128) / max(len(centre_pixels), 1)
    if removed > 0.12:
        return None

    cut = image.convert("RGBA")
    cut.putalpha(mask)
    return cut


def build_cutouts(force: bool = False) -> dict[str, int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    made = skipped = left_alone = 0

    for source in sorted(SOURCE_DIR.glob("*.jpg")):
        target = OUTPUT_DIR / f"{source.stem}.png"
        if target.exists() and not force:
            skipped += 1
            continue
        cut = _cut_out(source)
        if cut is None:
            # No flat backdrop, or the cutout came out damaged. The site falls
            # back to the original photo for these.
            target.unlink(missing_ok=True)
            left_alone += 1
            continue
        cut.save(target, "PNG", optimize=True)
        made += 1

    return {"made": made, "skipped": skipped, "kept_original": left_alone}



# ===========================================================================
# the API
# ===========================================================================

app = FastAPI(title="Campus Customs API", version="0.2.0")

# The Vite dev server runs on its own origin, so it needs CORS to reach us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product photos are served straight off disk. The cutouts are the
# background-free PNGs the site prefers; the originals remain available for the
# few garments that did not yield a clean cutout.
tools.PRODUCT_CUTOUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/cutouts",
    StaticFiles(directory=tools.PRODUCT_CUTOUT_DIR),
    name="product-cutouts",
)
app.mount(
    "/media/products",
    StaticFiles(directory=tools.PRODUCT_IMAGE_DIR),
    name="product-images",
)


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    """Pull the session token out of an ``Authorization: Bearer ...`` header."""
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def signed_in(token: str | None = Depends(bearer_token)) -> dict | None:
    return current_user(token)


def _redact_account_details(reply: str, user: dict | None) -> str:
    """Last line of defence on the signed-in shopper's email address.

    The agent is given the email so it knows whose conversation this is, and
    the prompt forbids it from ever being stated. This is the belt to that
    braces: a reply is checked before it leaves the server, so the address
    cannot reach the browser even if the instruction is talked around.

    Only the **complete** address is matched, never the local part on its own.
    A local part is often an ordinary word — "eduardo@..." against a shopper
    greeted as Eduardo, or "red@..." against a garment described as red — so
    redacting it would censor exactly the first-name greeting the shop is
    supposed to give, and mangle honest product descriptions.
    """
    if not user or not reply:
        return reply

    email = user["email"]
    if len(email) < 5:
        return reply

    lowered = reply.lower()
    target = email.lower()
    if target not in lowered:
        return reply

    # Rebuild case-insensitively, keeping everything either side.
    out, start = [], 0
    while True:
        found = lowered.find(target, start)
        if found == -1:
            out.append(reply[start:])
            break
        out.append(reply[start:found])
        out.append("[withheld]")
        start = found + len(target)

    logging.warning("An account detail was redacted from an assistant reply")
    return "".join(out)


def _cards_for(product_ids: list[str]) -> list[ProductCard]:
    """Turn the ids the agent chose into cards built from the database.

    An id the agent invented simply finds nothing and is dropped, so a
    hallucinated product can never reach the website.
    """
    cards: list[ProductCard] = []
    for product_id in dict.fromkeys(product_ids):  # de-duplicate, keep order
        row = tools.product_row(product_id)
        if row is not None:
            cards.append(ProductCard.model_validate(row))
    return cards


@app.get("/api/health")
def health() -> dict[str, object]:
    products = tools.list_products()
    return {"status": "ok", "products": len(products)}


@app.get("/api/categories")
def categories() -> list[str]:
    """Normalised categories that actually have products behind them."""
    present = {p["category"] for p in tools.list_products()}
    return [c for c in tools.CATEGORY_ORDER if c in present]


@app.get("/api/products")
def products() -> list[dict]:
    return tools.list_products()


@app.get("/api/products/{product_id}")
def product(product_id: str) -> dict:
    found = tools.product_row(product_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"no product named {product_id!r}")
    return found


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, user: dict | None = Depends(signed_in)
) -> ChatResponse:
    """Answer one shopper message with the PydanticAI agent.

    The agent writes the prose and nominates products by id. The cards are then
    built here, from the database, so every price, colour and stock count the
    website shows is the real one even if the model misremembers.

    Only the shopper's first name is passed through. Their email address and
    everything else on the account never reach the model.
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="The message is empty.")

    # Identity and prior conversation exist only for a signed-in shopper. For a
    # guest every one of these stays None/empty, so there is nothing to store
    # and nothing to recall.
    if user:
        shopper = shop_agent.ShopperContext(
            user_id=user["id"],
            first_name=user["first_name"],
            full_name=user["name"],
            email=user["email"],
            remembered=summarise_history(user["id"]),
            discounts=tools.interest_summary(user["id"]),
            page=request.page,
        )
        prior = history_for_replay(user["id"])
    else:
        shopper = shop_agent.ShopperContext(page=request.page)
        prior = None

    try:
        reply = await shop_agent.answer(message, shopper=shopper, history=prior)
    except ModelHTTPError as error:
        # The provider refused the prompt outright — its own safety filter, not
        # a fault. Nothing is broken, so decline in the shop's voice rather than
        # reporting an outage.
        if error.status_code == 400:
            logging.info("The provider declined a message before it reached the model")
            declined = (
                "We would rather not take that one up. We are glad to help with "
                "anything in the Campus Customs catalogue — a garment, a colour, "
                "or a size."
            )
            if user:
                record_turn(user["id"], message, declined, [])
            return ChatResponse(reply=declined)
        logging.exception("The shop assistant failed to answer")
        raise HTTPException(
            status_code=502,
            detail="We are sorry — the shop assistant is unavailable just now. Please try again shortly.",
        ) from None
    except Exception:
        # Never surface the underlying error: it can carry request details, and
        # the shopper can do nothing with it.
        logging.exception("The shop assistant failed to answer")
        raise HTTPException(
            status_code=502,
            detail="We are sorry — the shop assistant is unavailable just now. Please try again shortly.",
        ) from None

    cards = _cards_for(reply.product_ids)
    text = _redact_account_details(reply.reply, user)

    # Only a signed-in shopper's conversation is kept. A guest leaves no trace.
    # The redacted text is what gets stored, so a slip is not kept on disk.
    if user:
        record_turn(
            user["id"], message, text, [card.model_dump() for card in cards]
        )

    return ChatResponse(
        reply=text,
        products=cards,
        # Only label a band that has something in it.
        result_title=reply.result_title if cards else None,
    )


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history_for_user(user: dict | None = Depends(signed_in)) -> ChatHistory:
    """The signed-in shopper's previous conversation. Guests get nothing."""
    if user is None:
        return ChatHistory()

    turns = []
    for turn in history_for_display(user["id"]):
        # Re-validate the stored cards, dropping any that no longer parse.
        cards = []
        for product in turn["products"]:
            try:
                cards.append(ProductCard.model_validate(product))
            except Exception:
                continue
        turns.append(
            StoredTurn(
                role=turn["role"],
                content=turn["content"],
                products=cards,
                created_at=turn["created_at"],
            )
        )
    return ChatHistory(turns=turns)


@app.delete("/api/chat/history")
def forget_chat_history(user: dict | None = Depends(signed_in)) -> dict:
    """Let a shopper erase their own conversation."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"removed": clear_history(user["id"])}


# ---------------------------------------------------------------------------
# accounts
# ---------------------------------------------------------------------------


@app.post("/api/auth/register", status_code=201)
def register(request: RegisterRequest) -> dict:
    try:
        token, user = register_user(
            request.first_name,
            request.last_name,
            request.email,
            request.password,
            request.confirm_password,
        )
    except AuthError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    return {"token": token, "user": user}


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict:
    try:
        token, user = sign_in(request.email, request.password)
    except AuthError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    return {"token": token, "user": user}


@app.get("/api/auth/me")
def me(user: dict | None = Depends(signed_in)) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"user": user}


@app.post("/api/auth/logout")
def logout(token: str | None = Depends(bearer_token)) -> dict:
    end_session(token)
    return {"ok": True}


# ---------------------------------------------------------------------------
# perks: discounts, purchases and ratings
#
# None of these call the shop assistant's model. Issuing a discount, recording
# interest and saving a rating are plain database operations, which is faster
# and cheaper than any model. The one model call is Handsome Dan's sentence,
# and it runs on the light model.
# ---------------------------------------------------------------------------


@app.get("/api/perks/discount")
async def current_discount(user: dict | None = Depends(signed_in)) -> dict:
    """Handsome Dan's standing offer, and whether he has a new one today.

    Guests get nothing: the discount is a benefit of having an account, which
    is what the sign-in prompt on the chat panel tells them.
    """
    if user is None:
        return {"signed_in": False, "offer": None, "greeting": None}

    offer = tools.active_offer(user["id"])
    fresh = False
    if offer is None and tools.offer_due(user["id"]):
        offer = tools.issue_offer(user["id"])
        fresh = True

    if offer is None:
        return {"signed_in": True, "offer": None, "greeting": None}

    line = await dan_greeting(user["first_name"], offer["percent"]) if fresh else None
    return {
        "signed_in": True,
        "fresh": fresh,
        "offer": DiscountOffer(**{k: offer.get(k) for k in DiscountOffer.model_fields}).model_dump(),
        "greeting": line,
    }


@app.post("/api/perks/discount/interest")
def discount_interest(user: dict | None = Depends(signed_in)) -> dict:
    """The shopper pressed 'Tell me more' on the discount."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"recorded": tools.record_interest(user["id"], "pressed Tell me more in the chat panel")}


@app.get("/api/products/{product_id}/rating", response_model=ProductRating)
def product_rating(product_id: str) -> ProductRating:
    """What buyers made of a garment. Public: ratings help everyone choose."""
    if tools.product_row(product_id) is None:
        raise HTTPException(status_code=404, detail=f"no product named {product_id!r}")
    return ProductRating(**tools.rating_for_product(product_id))


@app.post("/api/purchases", response_model=PurchaseReceipt, status_code=201)
def buy(request: PurchaseRequest, user: dict | None = Depends(signed_in)) -> PurchaseReceipt:
    """Buy one garment, saving the star rating given at the same moment."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Please sign in to complete an order — members buy with Handsome Dan's discount.",
        )
    try:
        receipt = tools.record_purchase(
            user["id"], request.product_id, request.size, request.stars, request.use_discount
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    return PurchaseReceipt(**receipt)


# ===========================================================================
# setup commands
# ===========================================================================

if __name__ == "__main__":
    if "--init-db" in sys.argv:
        apply_schema()
    elif "--cutouts" in sys.argv:
        print(build_cutouts(force="--force" in sys.argv))
    else:
        print(__doc__)
