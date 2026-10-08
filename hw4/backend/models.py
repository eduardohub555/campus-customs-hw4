"""Structured types for the Campus Customs shop assistant.

Everything the agent returns, and everything the website renders, is one of
these. Keeping them here means the shapes are declared once and validated on
the way out of the API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SizeStock(BaseModel):
    """One size of one product, and how many are on the shelf."""

    size: str
    quantity: int


class ProductCard(BaseModel):
    """A product as the website draws it.

    Built from the database *after* the agent has answered, never from text the
    model produced, so the price, sizes and colours on a card are always the
    real ones.
    """

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    short_description: str
    colors: list[str] = Field(default_factory=list)
    price: float
    image_url: str
    inventory: list[SizeStock] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(default_factory=list)
    total_stock: int


class ProductSummary(BaseModel):
    """What a search tool hands back to the agent.

    Deliberately smaller than a ProductCard. Every field here is one the agent
    may need to *say*; anything the website alone uses is left out, so the model
    is never holding data it has no business repeating.
    """

    product_id: str = Field(description="Quote this exactly when showing the product.")
    name: str
    category: str = Field(description="Hoodies, Sweatshirts, T-Shirts, Quarter-Zips or Jackets.")
    garment_type: str = Field(description="The specific cut, e.g. 'pullover hoodie'.")
    description: str
    colors: list[str] = Field(
        default_factory=list,
        description="The only colours this garment comes in. Empty means none are recorded.",
    )
    price: float = Field(description="US dollars.")
    sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes with at least one unit on the shelf."
    )
    total_stock: int = Field(description="Units across all sizes. Zero means sold out.")


class ProductDetail(ProductSummary):
    """One product in full, including the count for every size."""

    inventory: list[SizeStock] = Field(
        default_factory=list,
        description="All six sizes XS to XXL, including those at zero.",
    )


class SizeAvailability(BaseModel):
    """The answer to 'do you have this in a medium?'

    Carries the fallback in the same result as the answer, so a disappointing
    reply can still be a useful one without a second tool call.
    """

    product_id: str
    product_name: str
    size: str
    available: bool = Field(description="True only when quantity is above zero.")
    quantity: int = Field(description="Units of this size. Zero means sold out in this size.")
    other_sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes of this same product still available."
    )


class SizeOption(BaseModel):
    """A product that is genuinely available in one particular size.

    Used when a shopper's size is gone and the shop should offer something
    else. The count is for *that* size, because that is the number the answer
    turns on — a product with plenty of stock overall is no use if the large is
    the only size left.
    """

    product_id: str
    name: str
    category: str
    garment_type: str
    colors: list[str] = Field(default_factory=list)
    price: float
    size: str
    quantity_in_size: int = Field(description="Units of this size. Always above zero here.")


class ProductRating(BaseModel):
    """What buyers thought of a garment, out of five stars."""

    product_id: str
    ratings: int = Field(description="How many people have rated it. Zero means nobody yet.")
    average: float | None = Field(
        default=None, description="Mean stars, one decimal. None when there are no ratings."
    )


class DiscountOffer(BaseModel):
    """A discount Handsome Dan has given a signed-in shopper."""

    code: str
    percent: int
    offered_at: str | None = None
    interested_at: str | None = None
    expired: bool = False


class PurchaseRequest(BaseModel):
    """Buying one garment, with the star rating the shopper gave on the way."""

    product_id: str
    size: str
    stars: int | None = Field(default=None, ge=1, le=5)
    use_discount: bool = False


class PurchaseReceipt(BaseModel):
    purchase_id: int
    product_id: str
    product_name: str
    size: str
    price_paid: float
    list_price: float
    discount_code: str | None = None
    stars: int | None = None


class AgentReply(BaseModel):
    """What the model is required to produce.

    The model writes the prose and nominates which products to show by id. It
    never supplies the figures on a card — those are looked up afterwards, so a
    price or a stock count cannot be invented.
    """

    reply: str = Field(description="The answer to the shopper, in the shop's voice.")
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "product_id values to display as cards on the page, taken verbatim "
            "from tool results. Empty when no particular product is being shown."
        ),
    )
    result_title: str | None = Field(
        default=None,
        description=(
            "A short heading for the cards, two to four words, in the shop's "
            "voice: 'Hoodies', 'Grey Quarter-Zips', 'Available in XS'. Null "
            "when no products are being shown."
        ),
    )


class PageContext(BaseModel):
    """Where the shopper is standing when they ask.

    Sent by the front end with every message so that "do you have this in
    pink?" has a referent. The product is identified by id only; the agent
    looks the garment up itself, so the context cannot carry a stale price.
    """

    path: str | None = Field(default=None, description="The route being viewed, e.g. /products/....")
    product_id: str | None = Field(
        default=None, description="The product whose page they are on, when they are on one."
    )
    category: str | None = Field(
        default=None, description="The category being filtered, when browsing the catalogue."
    )


class ChatRequest(BaseModel):
    message: str
    page: PageContext | None = None


class StoredTurn(BaseModel):
    """One turn of a returning shopper's conversation."""

    role: str
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatHistory(BaseModel):
    """What the panel reloads when a signed-in shopper comes back."""

    turns: list[StoredTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """The payload the chat panel receives.

    ``products`` is the search result the page renders as cards. Each entry is
    built from the database after the agent has answered, so the website can
    draw a full product card — and link to that product's page — from the reply
    alone.
    """

    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    result_title: str | None = None
