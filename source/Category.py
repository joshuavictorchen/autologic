from Group import Group
from Participant import Participant


class Category(Group):
    """
    Represents a group of participants in the same competition category.
    Inherits from Group to reuse filtering and availability logic.

    Attributes:
        event (Event): The parent event object.
        name (str): The category name.
        heat (int or None): Assigned heat number (if any).
    """

    def __init__(self, event, name):
        # Initialize cache from parent class
        super().__init__()
        self.event = event
        self.name = name
        self.participants = []
        self.heat = None

    def __repr__(self):
        return f"{self.name}"

    def add_participant(self, participant: Participant):
        """Adds a participant to the category."""
        self.participants.append(participant)

    def set_heat(self, heat):
        """
        Assigns the category to a heat.

        Args:
            heat (int): The heat number.
        """
        self.heat = heat
