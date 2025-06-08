import pkgutil
import importlib
import algorithms
from typing import Type, Dict
from algorithms import HeatGenerator

_registry: Dict[str, Type[HeatGenerator]] = {}


def register(cls: Type[HeatGenerator]) -> Type[HeatGenerator]:
    """
    Decorator to register a HeatGenerator under its module name.

    Usage:
       @register
       class MyAlgo(HeatGenerator): ...
    """
    # module_name = filename without “.py”
    module_name = cls.__module__.rsplit(".", 1)[-1]
    _registry[module_name] = cls
    return cls


def _discover_algorithms() -> None:
    """
    Import every .py in algorithms/ so that @register runs.
    """
    pkg = algorithms
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        if module_name in ("_base", "_registry"):
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
