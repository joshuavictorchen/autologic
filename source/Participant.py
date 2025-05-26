import utils

WORKER_ASSIGNMENT = "worker"


class Participant:
    """
    Represents a single participant in the event.

    Attributes:
        event (Event): Parent event object.
        id (int): Unique numeric identifier.
        name (str): Name of the participant.
        category_string (str): Key to the participant's category.
        novice (bool): Whether the participant is a novice.
        assignment (str or None): Currently assigned role.
        Other attributes (like 'instructor', 'timing', etc.) are added dynamically.
    """

    def __init__(
        self,
        event,
        id: int,
        name: str,
        category_string: str,
        novice: bool,
        **kwargs,
    ):
        self.event = event
        self.id = id
        self.name = name
        self.category_string = category_string
        self.novice = novice

        # dynamically assign additional role flags (e.g., instructor=True)
        [setattr(self, key, value) for key, value in kwargs.items()]

        # if participant is marked special, assign them immediately
        self.assignment = "special" if kwargs.get("special") else None

    def __repr__(self):
        return f"{self.name}"

    @property
    def category(self):
        """Returns the full Category object corresponding to this participant."""
        return self.event.categories[self.category_string]

    @property
    def heat(self):
        """Returns the heat associated with this participant's category."""
        return self.category.heat

    @property
    def has_sole_role(self):
        """
        Returns True if the participant has exactly one role (excluding special).
        Useful for filtering unambiguous assignments.
        """
        role_found = False
        for role in utils.roles_and_minima(
            number_of_stations=self.event.number_of_stations
        ):
            if getattr(self, role, False):
                if role_found:
                    return False
                role_found = True
        return role_found

    def set_assignment(self, assignment, verbose=True):
        """
        Assigns a role to this participant if they are qualified for it.

        Args:
            assignment (str): The role to assign.
        """
        # reject unqualified assignments (everyone is qualified to be a worker)
        if not getattr(self, assignment, False) and not assignment.lower().startswith(
            WORKER_ASSIGNMENT
        ):
            (
                print(f"    {self} is not qualified for {assignment.upper()}")
                if verbose
                else None
            )
        else:
            (
                print(
                    f"    {self.name.ljust(self.event.max_name_length)} assigned to {assignment.upper().ljust(utils.get_max_role_str_length())}"
                    # uncomment if interactive mode is implemented
                    # f" (previously: {self.assignment.upper() if self.assignment else None})"
                )
                if verbose
                else None
            )
            self.assignment = assignment
