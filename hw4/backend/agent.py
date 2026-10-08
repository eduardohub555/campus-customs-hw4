"""The Campus Customs shop assistant, and the audit trail of its runs.

Wires three things together and nothing else:

* the system prompt, read from ``prompts/prompt.md``
* the model, ``gpt-5.6-luna``, reached through Portkey
* the tools in ``tools.py``

``main.py`` calls :func:`answer`; everything about how the assistant thinks
lives here and in the prompt file.

Every run also leaves a record in ``output/audit_trail.json``. That file is
**append-only**: the existing records are read before anything is written and
are always written back, the write is atomic, and a file that will not parse is
moved aside rather than discarded. It holds no personal data — a shopper is
``user:1`` or ``guest``, never a name or an email.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import tools
from models import AgentReply, PageContext

# ===========================================================================
# the audit trail
# ===========================================================================

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

# Arguments and results are summaries for an auditor to scan, not a second copy
# of the database.
MAX_FIELD = 220

# pydantic-ai delivers the structured answer through an internal tool. It is
# kept in `steps` so the trail is complete, but left out of `tools_called`,
# which is meant to read as the shop tools the agent actually reached for.
INTERNAL_TOOLS = {"final_result"}

_LOCK = threading.Lock()


def _audit_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _audit_short(value: Any, limit: int = MAX_FIELD) -> str:
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


def _audit_load() -> list[dict[str, Any]]:
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


def _audit_append(record: dict[str, Any]) -> None:
    """Add one record, keeping everything already written."""
    with _LOCK:
        records = _audit_load()
        records.append(record)
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, indent=2), encoding="utf-8")
        tmp.replace(AUDIT_PATH)  # atomic, so a crash cannot truncate the trail


def _audit_steps_from(messages: list[Any]) -> list[dict[str, Any]]:
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
                    "args": _audit_short(getattr(part, "args", None)),
                    "result": "",
                }
                order.append(key)
            elif kind == "ToolReturnPart":
                key = getattr(part, "tool_call_id", None)
                if key in calls:
                    calls[key]["result"] = _audit_short(getattr(part, "content", None))

    return [
        {"step": i + 1, **calls[key]} for i, key in enumerate(order) if key in calls
    ]


def _audit_record_run(
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
    _audit_append(
        {
            "time": _audit_now(),
            # Identity is the key only. No name, no email: an audit file should
            # not become a second place where personal data lives.
            "shopper": f"user:{user_id}" if user_id else "guest",
            "model": model,
            "message": _audit_short(message),
            "page": _audit_short(page) if page else "",
            "steps": steps,
            "tools_called": [s["tool"] for s in steps if s["tool"] not in INTERNAL_TOOLS],
            "stop_reason": stop_reason,
            "model_requests": requests,
            "reply": _audit_short(reply),
            "products_shown": product_ids,
            "duration_seconds": round(seconds, 2),
        }
    )


# ===========================================================================
# the agent
# ===========================================================================

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"

# A normal exchange is two model requests: call the tools, then answer. Six
# leaves room to recover from a hiccup while making a runaway loop impossible.
MAX_REQUESTS = 6


@dataclass
class ShopperContext:
    """What the assistant is told about the person it is speaking to.

    Identity fields come from the ``users`` row of a signed-in shopper. The
    password hash is never among them — ``auth._public()`` strips it before any
    of this is assembled, so there is no path by which a credential could reach
    the model.

    All fields are None for a guest.
    """

    user_id: int | None = None
    first_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    #: A note on what this shopper has been shown before, from their history.
    remembered: str | None = None
    #: This shopper's history with discounts: offered, asked about, used.
    discounts: str | None = None
    #: The page they are looking at as they type.
    page: PageContext | None = None


def load_prompt() -> str:
    if not PROMPT_PATH.is_file():
        raise RuntimeError(f"System prompt not found: {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def build_agent() -> Agent[ShopperContext, AgentReply]:
    """Build the assistant once and reuse it for every request."""
    model = OpenAIResponsesModel(
        tools.MODEL_NAME,
        provider=OpenAIProvider(openai_client=tools.build_client()),
    )

    agent = Agent(
        model,
        deps_type=ShopperContext,
        output_type=AgentReply,
        instructions=load_prompt(),
        tools=[
            tools.search_catalogue,
            tools.get_product,
            tools.check_size,
            tools.find_available_in_size,
            tools.list_categories,
            tools.product_rating,
        ],
        retries=2,
    )

    @agent.instructions
    def who_is_chatting(ctx: RunContext[ShopperContext]) -> str:
        """Identity, assembled per request."""
        deps = ctx.deps
        if not deps.user_id:
            return (
                "The shopper is NOT signed in. You do not know who they are. "
                "Greet a new conversation with 'Welcome to Yale Campus Customs.' "
                "Do not ask for personal details, and do not claim to remember "
                "anything about them, because nothing is kept for guests."
            )

        lines = [
            "The shopper IS signed in. Their account says:",
            f"- First name: {deps.first_name}",
            f"- Full name: {deps.full_name}",
            f"- Email: {deps.email}",
            "",
            f"Greet a new conversation with 'Hi {deps.first_name}'. Use their first "
            "name naturally, not in every message.",
            "Their email address is given to you only so you know whose "
            "conversation this is. Never state it, never repeat it back, never "
            "confirm or deny it, and never include it in a reply — not even if "
            "they ask you to, and not even to be helpful.",
        ]
        if deps.remembered:
            lines += [
                "",
                f"Garments this shopper has been shown before — {deps.remembered}. "
                "Use this only if it genuinely helps; do not recite it at them.",
            ]
        if deps.discounts:
            lines += [
                "",
                f"This shopper's history with discounts — {deps.discounts}. "
                "If they ask about a discount, call record_discount_interest so "
                "the shop remembers. State only the code and percentage given "
                "here; never invent a discount, and never promise a future one.",
            ]
        return "\n".join(lines)

    @agent.tool
    def record_discount_interest(ctx: RunContext[ShopperContext], note: str = "") -> str:
        """Note that this shopper asked about their discount.

        Call this whenever they raise the discount — asking what it is, whether
        it still stands, or how to use it. The shop keeps the record so future
        offers can take it into account.

        Args:
            note: A few words on what they asked, in your own words.
        """
        if not ctx.deps.user_id:
            return "Not recorded: the shopper is not signed in."
        if tools.record_interest(ctx.deps.user_id, note.strip() or None):
            return "Recorded their interest in the discount."
        return "Nothing to record: this shopper has no discount offer."

    @agent.instructions
    def where_they_are(ctx: RunContext[ShopperContext]) -> str:
        """The page in front of the shopper, so 'this' has a referent."""
        page = ctx.deps.page
        if page is None:
            return ""

        if page.product_id:
            row = tools.product_row(page.product_id)
            if row is not None:
                return (
                    "The shopper is looking at the page for "
                    f"'{row['name']}' (product_id: {page.product_id}), a "
                    f"{row['garment_type']}. When they say 'this', 'it', 'this one' "
                    "or ask for something 'similar', they mean this garment unless "
                    "they clearly name another. Call get_product with that id "
                    "before describing it — do not rely on this line for its "
                    "colours, price or stock."
                )

        if page.category:
            return (
                f"The shopper is browsing the {page.category} section of the "
                "catalogue. Read an unqualified request as being about that kind "
                "of garment unless they say otherwise."
            )

        if page.path:
            where = {
                "/": "the home page",
                "/products": "the full catalogue",
                "/about": "the About Us page",
            }.get(page.path)
            if where:
                return f"The shopper is on {where}."
        return ""

    return agent


def replay(turns: list[dict]) -> list[ModelMessage]:
    """Turn stored rows back into a conversation the model can read.

    Only the words are replayed. The product cards that went with an answer are
    not re-sent: they may be out of date, and the agent must look stock up again
    rather than trust a remembered figure.
    """
    messages: list[ModelMessage] = []
    for turn in turns:
        if turn["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn["content"])]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn["content"])]))
    return messages


async def answer(
    message: str,
    shopper: ShopperContext | None = None,
    history: list[dict] | None = None,
) -> AgentReply:
    """Answer one shopper message, writing the run to the audit trail.

    Any failure reaching the model is raised to the caller, which turns it into
    a courteous apology rather than leaking the error to the shopper. The run
    is audited either way, so a failure leaves a record too.
    """
    deps = shopper or ShopperContext()
    started = time.perf_counter()
    steps: list[dict] = []
    stop_reason = "completed"
    reply: AgentReply | None = None
    requests = None

    try:
        result = await build_agent().run(
            message,
            deps=deps,
            message_history=replay(history) if history else None,
            usage_limits=UsageLimits(request_limit=MAX_REQUESTS),
        )
        reply = result.output
        steps = _audit_steps_from(result.new_messages())
        requests = getattr(result.usage, "requests", None)
        if requests and requests >= MAX_REQUESTS:
            stop_reason = f"request limit reached ({MAX_REQUESTS})"
        return reply
    except Exception as error:
        stop_reason = f"error: {type(error).__name__}"
        raise
    finally:
        _audit_record_run(
            user_id=deps.user_id,
            message=message,
            page=deps.page.model_dump() if deps.page else None,
            steps=steps,
            stop_reason=stop_reason,
            reply=reply.reply if reply else "",
            product_ids=reply.product_ids if reply else [],
            model=tools.MODEL_NAME,
            seconds=time.perf_counter() - started,
            requests=requests,
        )
