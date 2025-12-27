import utils
from group import Group


class Heat(Group):
    """
    Represents a heat or time slot in the event.

    Attributes:
        event (Event): The parent event.
        number (int): Heat identifier.
    """

    def __init__(self, event):
        self.event = event
        self.assigned_categories = []

    def __repr__(self):
        return f"{self.number}"

    @property
    def number(self):

        return self.event.heats.index(self) + 1

    @property
    def categories(self):
        """
        Returns a list of all categories assigned to this heat.

        Returns:
            list[Category]: Matching categories from the event.
        """
        return [
            c for c in self.event.categories.values() if c.heat.number == self.number
        ]

    @property
    def participants(self):
        """
        List of participants in this heat.

        Returns:
            list[Participant]: All participants in this heat.
        """
        return sum([c.participants for c in self.categories], [])

    @property
    def valid_size(self):

        heat_size = len(self.participants)

        is_valid = (
            abs(self.event.mean_heat_size - heat_size) <= self.event.max_heat_size_delta
        )

        if self.event.verbose and not is_valid:
            print(f"\n    Heat {self} violation: participant count of {heat_size}")

        return is_valid

    @property
    def valid_novice_count(self):

        novice_count = len(self.get_participants_by_attribute("novice"))

        is_valid = (
            abs(self.event.mean_heat_novice_count - novice_count)
            <= self.event.max_heat_novice_delta
        )

        if not is_valid:
            print(f"    Heat {self} violation: novice count of {novice_count}")

        return is_valid

    @property
    def valid_role_fulfillment(self):

        is_valid = True

        for role, minimum in utils.roles_and_minima(
            number_of_stations=self.event.number_of_stations,
            number_of_novices=len(
                self.compliment.get_participants_by_attribute("novice")
            ),
            novice_denominator=self.event.novice_denominator,
        ).items():

            # exact matches are specified to ensure enough course workers
            # with the exception of instructors, who may exceed the minimum
            fulfilled = len(self.get_participants_by_attribute("assignment", role))
            if (
                fulfilled != minimum and not role == "instructor"
            ) or fulfilled < minimum:
                print(
                    f"    Heat {self} violation: {fulfilled} assignments for {role} ({minimum} expected)"
                )
                is_valid = False

        for p in self.participants:

            valid_roles = list(utils.roles_and_minima().keys())
            valid_roles += ["worker", "special"]

            if not p.assignment in valid_roles:
                print(
                    f"    Heat {self} violation: {p} assignment of {p.assignment} is not not valid (one of {valid_roles} expected)"
                )
                is_valid = False

        return is_valid

    @property
    def running(self):
        # somewhat redundant, but provides an explicit method for when the heat is running
        return self.number

    @property
    def working(self):

        work_offset = 5 if self.event.number_of_heats >= 4 else 3
        return (self.running + work_offset) % self.event.number_of_heats + 1

    @property
    def compliment(self):
        # heat that is running while self is working
        for h in self.event.heats:
            if h.running == self.working:
                return h

        raise ValueError(f"Heat {self} has no compliment")
