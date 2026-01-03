import importlib
import pkgutil
from importlib import resources
from typing import Dict, Iterable, Type

from autologic import algorithms
from autologic.algorithms._base import HeatGenerator

_registry: Dict[str, Type[HeatGenerator]] = {}


def register(cls: Type[HeatGenerator]) -> Type[HeatGenerator]:
    """Register a HeatGenerator under its module name.

    Args:
        cls: HeatGenerator subclass to register.

    Returns:
        Type[HeatGenerator]: The registered class.
    """
    # module_name = filename without “.py”
    module_name = cls.__module__.rsplit(".", 1)[-1]
    _registry[module_name] = cls
    return cls


def _iter_algorithm_module_names() -> Iterable[str]:
    """Yield algorithm module names within the algorithms package.

    Returns:
        Iterable[str]: Module names without package prefixes.
    """
    module_names: set[str] = set()
    pkg = algorithms

    # use importlib.resources first because pkgutil can miss modules in frozen apps
    try:
        for entry in resources.files(pkg).iterdir():
            if entry.name.startswith("_"):
                continue
            if entry.is_file() and entry.name.endswith(".py"):
                module_names.add(entry.name[:-3])
    except Exception:
        module_names = set()

    if not module_names:
        try:
            for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
                module_names.add(module_name)
        except Exception:
            module_names = set()

    return sorted(module_names)


def _discover_algorithms() -> None:
    """Import algorithm modules so that @register runs."""
    pkg = algorithms
    for module_name in _iter_algorithm_module_names():
        if module_name in ("_base", "_registry", "__init__"):
            continue
        importlib.import_module(f"{pkg.__name__}.{module_name}")


def get_algorithms() -> Dict[str, Type[HeatGenerator]]:
    _discover_algorithms()
    return dict(_registry)


def get_generator(name: str) -> Type[HeatGenerator]:
    _discover_algorithms()
    try:
        return _registry[name]
    except KeyError:
        raise ValueError(f"No algorithm named {name!r}")
