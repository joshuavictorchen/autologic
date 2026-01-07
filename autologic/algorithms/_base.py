from abc import ABC, abstractmethod
from autologic.event import Event


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
        """Register a generation observer callback.

        Observers are optional hooks used by the GUI to detect cancellation while
        an algorithm runs. The callback receives `(event_type, payload)`; the GUI
        currently ignores the payload contents and only uses the call as a
        cancellation checkpoint.

        Args:
            observer: Callable accepting (event_type: str, payload: dict).
        """
        if not hasattr(self, "observers"):
            self.observers = []
        self.observers.append(observer)

    def _notify(self, event_type: str, payload: dict):
        """Notify observers about algorithm progress or checkpoints.

        This is primarily a GUI hook today. The payload schema is intentionally
        flexible and not interpreted yet; observers may raise an exception to
        abort generation, so algorithms should not swallow observer errors.

        Args:
            event_type: Short label describing the notification.
            payload: Arbitrary metadata for future GUI or logging use.
        """
        for observer in getattr(self, "observers", []):
            observer(event_type, payload)
