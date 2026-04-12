"""Single ContextVar for AppConfig lifecycle.

AppConfig is set once at process startup via init_app_config().
All consumers read it via get_app_config().
No reload, no mtime detection, no push/pop.
"""

import logging
from contextvars import ContextVar

from deerflow.config.app_config import AppConfig

logger = logging.getLogger(__name__)

_app_config_var: ContextVar[AppConfig] = ContextVar("deerflow_app_config")


def init_app_config(config: AppConfig) -> None:
    """Set the AppConfig for the current context."""
    _app_config_var.set(config)


def get_app_config() -> AppConfig:
    """Get the current AppConfig.

    If init_app_config() was not called, auto-initializes from config file
    for backward compatibility. Prefer calling init_app_config() explicitly
    at process startup.
    """
    try:
        return _app_config_var.get()
    except LookupError:
        logger.debug("AppConfig not initialized, auto-loading from file")
        config = AppConfig.from_file()
        _app_config_var.set(config)
        return config
