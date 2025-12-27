from abc import ABC, abstractmethod
from event import Event


class HeatGenerator(ABC):
    """
    Interface for all heat generation algorithms.
    """

    def __init__(self):
        # observers receive progress and status callbacks during generation
        self.observers = []

    @abstractmethod
    def generate(self, event: Event) -> None:
        """
        Mutate `event` by assigning `Categories` to `Heats`, and `Participants` to roles.
        """
        raise NotImplementedError

    def add_observer(self, observer):
        """Register a callable that accepts (event_type: str, payload: dict)."""
        if not hasattr(self, "observers"):
            self.observers = []
        self.observers.append(observer)

    def _notify(self, event_type: str, payload: dict):
        """Notify all observers of a generation event."""
        for observer in getattr(self, "observers", []):
            observer(event_type, payload)
