# Design: Eliminate Global Mutable State in Configuration System

> Implements [#1811](https://github.com/bytedance/deer-flow/issues/1811) · Tracked in [#2151](https://github.com/bytedance/deer-flow/issues/2151)

## Problem

`deerflow/config/` has three structural issues:

1. **Dual source of truth** — each sub-config exists both as an `AppConfig` field and a module-level global (e.g. `_memory_config`). Consumers don't know which to trust.
2. **Side-effect coupling** — `AppConfig.from_file()` silently mutates 8 sub-module globals via `load_*_from_dict()` calls.
3. **Incomplete isolation** — `ContextVar` only scopes `AppConfig`, not the 8 sub-config globals.

## Design Principle

**Config is a value object, not live shared state.** Constructed once, immutable, no reload. New config = new object + rebuild agent.

## Solution

### 1. Frozen AppConfig (full tree)

All config models set `frozen=True`. No mutation after construction.

```python
class MemoryConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    memory: MemoryConfig
    title: TitleConfig
    ...
```

Changes use copy-on-write: `config.model_copy(update={...})`.

### 2. Pure `from_file()`

`AppConfig.from_file()` becomes a pure function — returns a frozen object, no side effects. All `load_*_from_dict()` calls removed.

### 3. Delete sub-module globals

Every sub-config module's global state is deleted:

| Delete | Files |
|--------|-------|
| `_memory_config`, `get_memory_config()`, `set_memory_config()`, `load_memory_config_from_dict()` | `memory_config.py` |
| `_title_config`, `get_title_config()`, `set_title_config()`, `load_title_config_from_dict()` | `title_config.py` |
| Same pattern | `summarization_config.py`, `subagents_config.py`, `guardrails_config.py`, `tool_search_config.py`, `checkpointer_config.py`, `stream_bridge_config.py`, `acp_config.py` |
| `_extensions_config`, `reload_extensions_config()`, `reset_extensions_config()`, `set_extensions_config()` | `extensions_config.py` |
| `reload_app_config()`, `reset_app_config()`, `set_app_config()`, mtime detection, `push/pop_current_app_config()` | `app_config.py` |

Consumers migrate from `get_memory_config()` → `get_app_config().memory`.

### 4. Propagation

#### Agent path: `Runtime[DeerFlowContext]`

LangGraph's official DI mechanism. Config is injected per-invocation, type-safe.

```python
@dataclass(frozen=True)
class DeerFlowContext:
    app_config: AppConfig

agent = create_agent(model="...", tools=[...], context_schema=DeerFlowContext)
agent.invoke(messages, context=DeerFlowContext(app_config=config))
```

Middleware and tools access config through typed parameters:

```python
# Tool
@tool
def my_tool(runtime: ToolRuntime[DeerFlowContext]) -> str:
    runtime.context.app_config.memory  # typed

# Middleware
@before_model
def hook(state, runtime: Runtime[DeerFlowContext]):
    runtime.context.app_config.title  # typed
```

Why `Runtime` over `RunnableConfig.configurable`:
- `Runtime` is LangGraph's official DI, not a private dict hack
- Generic type parameter (`Runtime[DeerFlowContext]`) gives type safety
- `RunnableConfig` is for framework internals (tags, callbacks), not user dependencies

#### Non-agent path: ContextVar

Gateway API routers use `get_app_config()` backed by a single ContextVar. This is appropriate — Gateway doesn't run through the LangGraph execution graph.

### 5. No reload

Config lifecycle is simple:

```
Process start → from_file() → set ContextVar → run
                                                 ↓
                               Gateway API changed file?
                                                 ↓
                               from_file() → new frozen config
                               → set ContextVar → rebuild agent
```

- Edit `config.yaml` → restart process
- Gateway updates MCP/Skills → construct new config + rebuild agent
- No mtime detection, no `reload_*()`, no auto-refresh

### 6. Structure vs runtime config

| Type | Example | Reload behavior |
|------|---------|----------------|
| Structural (agent composition) | model, tools, middleware chain | Requires agent rebuild |
| Runtime (execution behavior) | `memory.enabled`, `title.max_words` | Next invocation picks up new config automatically via `Runtime` |

Middleware reads config from `Runtime` at execution time (not `__init__` capture), so runtime config changes take effect without agent rebuild.

## What doesn't change

- `config.yaml` schema
- `extensions_config.json` loading
- External API behavior (Gateway, DeerFlowClient)

## Migration scope

- 50+ call sites: `get_*_config()` → `get_app_config().xxx`
- Middleware: `__init__` capture → `Runtime[DeerFlowContext]` read
- Tools: global getters → `ToolRuntime[DeerFlowContext]`
- Tests: `reset_*_config()` → construct frozen config directly
- Gateway update flow: reload → construct new config + rebuild agent
- Dependency: upgrade langgraph >= 1.1.5 for `Runtime` support
