"""Handsome Dan's line when he offers a shopper a discount.

The only model call in the perks features, and it runs on the light model
(``tools.FAST_MODEL``) rather than the shop assistant's: one warm sentence from
a bulldog does not need the larger model.

If the model is slow or unavailable the shopper still gets their discount —
:func:`greeting` falls back to a written line rather than failing, because the
offer is a database fact and the sentence is only its wrapping.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import tools

INSTRUCTIONS = """
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


def _fallback(first_name: str | None, percent: int) -> str:
    who = f"{first_name}, " if first_name else ""
    return (
        f"Good to see you, {who}and because you are one of ours, "
        f"here is {percent}% off whatever you choose today."
    )


async def greeting(first_name: str | None, percent: int) -> str:
    """One line from Handsome Dan offering `percent`% off."""
    try:
        model = OpenAIResponsesModel(
            tools.FAST_MODEL, provider=OpenAIProvider(openai_client=tools.build_client())
        )
        agent = Agent(model, output_type=DanLine, instructions=INSTRUCTIONS)
        who = first_name or "a Yale shopper"
        result = await agent.run(
            f"The shopper is {who}. The discount is {percent} percent off.",
            usage_limits=UsageLimits(request_limit=2),
        )
        line = result.output.line.strip()
        # Trust nothing: if the model named a different number, use our words.
        if str(percent) not in line:
            logging.warning("Handsome Dan's line omitted the discount percentage; using the written one")
            return _fallback(first_name, percent)
        return line
    except Exception:
        logging.warning("Handsome Dan's line fell back to the written one", exc_info=False)
        return _fallback(first_name, percent)
