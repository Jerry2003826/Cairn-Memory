"""Capture engine registry for agent hook adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

_REGISTRY: dict[str, CaptureEngine] = {}


@dataclass(frozen=True)
class InstallResult:
    ok: bool
    message: str = ""
    diff: str = ""


@dataclass(frozen=True)
class CaptureEngine:
    name: str
    ingest_events: frozenset[str]
    run_engine: str = "claude_code"
    install: Callable[..., InstallResult] | None = None
    event_roles: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


def register(engine: CaptureEngine) -> None:
    if engine.name in _REGISTRY:
        raise ValueError(f"capture engine already registered: {engine.name}")
    _REGISTRY[engine.name] = engine


def get(name: str) -> CaptureEngine:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown capture engine: {name}") from exc


def default() -> CaptureEngine:
    return get("claude")


def names() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def _load_engines() -> None:
    from omni.capture import claude as _claude  # noqa: F401
    from omni.capture import opencode as _opencode  # noqa: F401


_load_engines()
