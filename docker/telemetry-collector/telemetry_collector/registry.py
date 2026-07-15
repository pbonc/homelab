from __future__ import annotations

from telemetry_collector.sources.base import SourceHandler
from telemetry_collector.sources.ecowitt import EcowittHandler


class SourceRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, SourceHandler] = {}

    def register(self, handler: SourceHandler) -> None:
        if handler.handler_name in self._handlers:
            raise ValueError(f"source handler already registered: {handler.handler_name}")
        self._handlers[handler.handler_name] = handler

    def get(self, name: str) -> SourceHandler:
        try:
            return self._handlers[name]
        except KeyError as exc:
            raise KeyError(f"unknown source handler: {name}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))


registry = SourceRegistry()
registry.register(EcowittHandler())
