"""Per-invocation context for DeerFlow agent execution.

Injected via LangGraph Runtime. Middleware and tools access this
via Runtime[DeerFlowContext] parameters.
"""

from dataclasses import dataclass

from deerflow.config.app_config import AppConfig


@dataclass(frozen=True)
class DeerFlowContext:
    """Typed, immutable, per-invocation context."""

    app_config: AppConfig
