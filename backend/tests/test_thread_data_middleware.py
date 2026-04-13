from unittest.mock import patch

import pytest

from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
from deerflow.config.app_config import AppConfig
from deerflow.config.deer_flow_context import DeerFlowContext
from deerflow.config.sandbox_config import SandboxConfig


def _as_posix(path: str) -> str:
    return path.replace("\\", "/")


def _make_context(thread_id: str) -> DeerFlowContext:
    return DeerFlowContext(
        app_config=AppConfig(sandbox=SandboxConfig(use="test")),
        thread_id=thread_id,
    )


class TestThreadDataMiddleware:
    def test_before_agent_returns_paths_when_thread_id_present_in_context(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        from langgraph.runtime import Runtime

        result = middleware.before_agent(state={}, runtime=Runtime(context=_make_context("thread-123")))

        assert result is not None
        assert _as_posix(result["thread_data"]["workspace_path"]).endswith("threads/thread-123/user-data/workspace")
        assert _as_posix(result["thread_data"]["uploads_path"]).endswith("threads/thread-123/user-data/uploads")
        assert _as_posix(result["thread_data"]["outputs_path"]).endswith("threads/thread-123/user-data/outputs")

    def test_before_agent_uses_thread_id_from_configurable_when_context_is_none(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        from langgraph.runtime import Runtime

        runtime = Runtime(context=None)
        config = AppConfig(sandbox=SandboxConfig(use="test"))
        with (
            patch("deerflow.config.get_app_config", return_value=config),
            patch("langgraph.config.get_config", return_value={"configurable": {"thread_id": "thread-from-config"}}),
        ):
            result = middleware.before_agent(state={}, runtime=runtime)

        assert result is not None
        assert _as_posix(result["thread_data"]["workspace_path"]).endswith("threads/thread-from-config/user-data/workspace")

    def test_before_agent_uses_thread_id_from_dict_context(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        from langgraph.runtime import Runtime

        config = AppConfig(sandbox=SandboxConfig(use="test"))
        with patch("deerflow.config.get_app_config", return_value=config):
            result = middleware.before_agent(state={}, runtime=Runtime(context={"thread_id": "thread-from-dict"}))

        assert result is not None
        assert _as_posix(result["thread_data"]["uploads_path"]).endswith("threads/thread-from-dict/user-data/uploads")

    def test_before_agent_raises_clear_error_when_thread_id_missing_everywhere(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        from langgraph.runtime import Runtime

        config = AppConfig(sandbox=SandboxConfig(use="test"))
        with (
            patch("deerflow.config.get_app_config", return_value=config),
            patch("langgraph.config.get_config", return_value={"configurable": {}}),
        ):
            with pytest.raises(ValueError, match="Thread ID is required"):
                middleware.before_agent(state={}, runtime=Runtime(context=None))
