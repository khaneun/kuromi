from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Iterable

from src.strategies.base import Strategy


_INTERNAL = {"base", "registry"}


def discover() -> list[type[Strategy]]:
    import src.strategies as pkg

    found: list[type[Strategy]] = []
    for _, name, is_pkg in pkgutil.iter_modules(pkg.__path__):
        if is_pkg or name in _INTERNAL:
            continue
        module = importlib.import_module(f"src.strategies.{name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is Strategy or not issubclass(obj, Strategy):
                continue
            if obj.__module__ != module.__name__ or not obj.name:
                continue
            found.append(obj)
    return found


def load(
    names: Iterable[str] | None = None,
    params: dict[str, dict] | None = None,
) -> list[Strategy]:
    params = params or {}
    classes = discover()
    if names:
        wanted = set(names)
        classes = [c for c in classes if c.name in wanted]
    return [cls(params.get(cls.name)) for cls in classes]
