"""Single ContextVar for AppConfig lifecycle.

AppConfig is set once at process startup via init_app_config().
All consumers read it via get_app_config().
No reload, no mtime detection, no push/pop.
"""

from contextvars import ContextVar

from deerflow.config.app_config import AppConfig


class ConfigNotInitializedError(RuntimeError):
    """Raised when get_app_config() is called before init_app_config()."""

    def __init__(self):
        super().__init__("AppConfig not initialized. Call init_app_config() at process startup.")


_app_config_var: ContextVar[AppConfig] = ContextVar("deerflow_app_config")


def init_app_config(config: AppConfig) -> None:
    """Set the AppConfig for the current context. Call once at process startup."""
    _app_config_var.set(config)


def get_app_config() -> AppConfig:
    """Get the current AppConfig. Raises ConfigNotInitializedError if not initialized."""
    try:
        return _app_config_var.get()
    except LookupError:
        raise ConfigNotInitializedError()
