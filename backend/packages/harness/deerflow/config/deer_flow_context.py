"""Per-invocation context for DeerFlow agent execution.

Injected via LangGraph Runtime. Middleware and tools access this
via Runtime[DeerFlowContext] parameters, through resolve_context().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeerFlowContext:
    """Typed, immutable, per-invocation context injected via LangGraph Runtime.

    Fields are all known at run start and never change during execution.
    Mutable runtime state (e.g. sandbox_id) flows through ThreadState, not here.
    """

    app_config: Any  # AppConfig — typed as Any to avoid circular import at module level
    thread_id: str
    agent_name: str | None = None


def resolve_context(runtime: Any) -> DeerFlowContext:
    """Extract or construct DeerFlowContext from runtime.

    Gateway/Client paths: runtime.context is already DeerFlowContext → return directly.
    LangGraph Server path: runtime.context is None or dict → fallback to ContextVar + configurable.
    """
    if isinstance(runtime.context, DeerFlowContext):
        return runtime.context

    from langgraph.config import get_config

    from deerflow.config import get_app_config

    cfg = get_config().get("configurable", {})
    return DeerFlowContext(
        app_config=get_app_config(),
        thread_id=cfg.get("thread_id", ""),
        agent_name=cfg.get("agent_name"),
    )
