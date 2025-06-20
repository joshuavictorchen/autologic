from abc import ABC, abstractmethod
from Event import Event


class HeatGenerator(ABC):
    """
    Interface for all heat generation algorithms.
    """

    @abstractmethod
    def generate(self, event: Event) -> None:
        """
        Mutate `event` by assigning `Categories` to `Heats`, and roles to `Participants`.
        """
        raise NotImplementedError
