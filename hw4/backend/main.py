"""Campus Customs API.

Problem 3 scope: serve the catalogue and the product images to the React front
end. The chat endpoint is a stub here; Problem 5 grows this file into the agent
backend.
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pydantic_ai.exceptions import ModelHTTPError

import agent as shop_agent
import auth
import db
import history as chat_history
import mascot
import perks
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
db.PRODUCT_CUTOUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/cutouts",
    StaticFiles(directory=db.PRODUCT_CUTOUT_DIR),
    name="product-cutouts",
)
app.mount(
    "/media/products",
    StaticFiles(directory=db.PRODUCT_IMAGE_DIR),
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
    return auth.current_user(token)


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
        row = db.get_product(product_id)
        if row is not None:
            cards.append(ProductCard.model_validate(row))
    return cards


@app.get("/api/health")
def health() -> dict[str, object]:
    products = db.list_products()
    return {"status": "ok", "products": len(products)}


@app.get("/api/categories")
def categories() -> list[str]:
    """Normalised categories that actually have products behind them."""
    present = {p["category"] for p in db.list_products()}
    return [c for c in db.CATEGORY_ORDER if c in present]


@app.get("/api/products")
def products() -> list[dict]:
    return db.list_products()


@app.get("/api/products/{product_id}")
def product(product_id: str) -> dict:
    found = db.get_product(product_id)
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
            remembered=chat_history.summarise(user["id"]),
            discounts=perks.interest_summary(user["id"]),
            page=request.page,
        )
        prior = chat_history.for_replay(user["id"])
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
                chat_history.record_turn(user["id"], message, declined, [])
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
        chat_history.record_turn(
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
    for turn in chat_history.for_display(user["id"]):
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
    return {"removed": chat_history.clear(user["id"])}


# ---------------------------------------------------------------------------
# accounts
# ---------------------------------------------------------------------------


@app.post("/api/auth/register", status_code=201)
def register(request: RegisterRequest) -> dict:
    try:
        token, user = auth.register(
            request.first_name,
            request.last_name,
            request.email,
            request.password,
            request.confirm_password,
        )
    except auth.AuthError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    return {"token": token, "user": user}


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict:
    try:
        token, user = auth.login(request.email, request.password)
    except auth.AuthError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    return {"token": token, "user": user}


@app.get("/api/auth/me")
def me(user: dict | None = Depends(signed_in)) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"user": user}


@app.post("/api/auth/logout")
def logout(token: str | None = Depends(bearer_token)) -> dict:
    auth.logout(token)
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

    offer = perks.active_offer(user["id"])
    fresh = False
    if offer is None and perks.offer_due(user["id"]):
        offer = perks.issue_offer(user["id"])
        fresh = True

    if offer is None:
        return {"signed_in": True, "offer": None, "greeting": None}

    line = await mascot.greeting(user["first_name"], offer["percent"]) if fresh else None
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
    return {"recorded": perks.record_interest(user["id"], "pressed Tell me more in the chat panel")}


@app.get("/api/products/{product_id}/rating", response_model=ProductRating)
def product_rating(product_id: str) -> ProductRating:
    """What buyers made of a garment. Public: ratings help everyone choose."""
    if db.get_product(product_id) is None:
        raise HTTPException(status_code=404, detail=f"no product named {product_id!r}")
    return ProductRating(**perks.rating_for_product(product_id))


@app.post("/api/purchases", response_model=PurchaseReceipt, status_code=201)
def buy(request: PurchaseRequest, user: dict | None = Depends(signed_in)) -> PurchaseReceipt:
    """Buy one garment, saving the star rating given at the same moment."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Please sign in to complete an order — members buy with Handsome Dan's discount.",
        )
    try:
        receipt = perks.record_purchase(
            user["id"], request.product_id, request.size, request.stars, request.use_discount
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    return PurchaseReceipt(**receipt)
