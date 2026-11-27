"""hexpi — the Pi coding agent as one Hermes tool, installed into a profile."""

from __future__ import annotations

import logging
from typing import Any

from . import pi_tool

logger = logging.getLogger(__name__)


def register(ctx: Any) -> None:
    """Register the one `pi` tool; a plugin that fails here must not cost the profile."""

    def handler(arguments: dict[str, Any], **_kwargs: Any) -> str:
        return pi_tool.run(arguments or {})

    try:
        ctx.register_tool(
            name="pi",
            toolset="hexpi",
            schema=pi_tool.SCHEMA,
            handler=handler,
            description="Run the Pi coding agent on a task in the working directory.",
            emoji="🥧",
        )
    except Exception:
        logger.exception("hexpi: could not register the pi tool")
