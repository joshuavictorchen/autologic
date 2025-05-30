from Group import Group


class Heat(Group):
    """
    Represents a heat or time slot in the event.

    Attributes:
        event (Event): The parent event.
        number (int): Heat identifier.
    """

    def __init__(self, event, number):
        self.event = event
        self.number = number
        self.assigned_categories = []

    def __repr__(self):
        return f"{self.number}"

    @property
    def categories(self):
        """
        Returns a list of all categories assigned to this heat.

        Returns:
            list[Category]: Matching categories from the event.
        """
        return [c for c in self.event.categories.values() if c.heat == self.number]

    @property
    def participants(self):
        """
        List of participants in this heat.

        Returns:
            list[Participant]: All participants in this heat.
        """
        return sum([c.participants for c in self.categories], [])
