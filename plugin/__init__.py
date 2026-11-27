"""hexpi — the Pi coding agent as one Hermes tool, installed into a profile."""

from __future__ import annotations

import logging
from typing import Any

from . import pi_process, pi_rpc, pi_stream, pi_tool

try:
    from tools.interrupt import is_interrupted as _host_interrupted
except ImportError:
    _host_interrupted = None

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT_S = 3600


def register(ctx: Any) -> None:
    """Register the one `pi` tool; a plugin that fails here must not cost the profile."""

    def turn(prompt: str, cwd: Any) -> Any:
        timeout_s = float(ctx.get_config("timeout_s", DEFAULT_TIMEOUT_S) or DEFAULT_TIMEOUT_S)
        return pi_rpc.run_turn(
            prompt,
            cwd,
            timeout_s,
            io=pi_process,
            stream=pi_stream,
            stop=_host_interrupted,
        )

    def handle(arguments: dict[str, Any], **_kwargs: Any) -> str:
        return pi_tool.handler(turn)(arguments)

    try:
        ctx.register_tool(
            name="pi",
            toolset="hexpi",
            schema=pi_tool.SCHEMA,
            handler=handle,
            description="Run the Pi coding agent on a task in the working directory.",
            emoji="🥧",
        )
    except Exception:
        logger.exception("hexpi: could not register the pi tool")
