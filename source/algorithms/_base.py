from abc import ABC, abstractmethod
from Event import Event


class HeatGenerator(ABC):
    """
    Interface for all heat generation algorithms.
    """

    @abstractmethod
    def generate(self, event: Event, max_iterations: int) -> None:
        """
        Mutate `event` by assigning heats & roles.
        """
        raise NotImplementedError
