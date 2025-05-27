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
        for key, value in kwargs.items():
            setattr(self, key, value)

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
            verbose (bool): Whether to print assignment details.
        """
        # reject unqualified assignments (everyone is qualified to be a worker)
        if not getattr(self, assignment, False) and not assignment.lower().startswith(
            WORKER_ASSIGNMENT
        ):
            if verbose:
                print(f"    {self} is not qualified for {assignment.upper()}")
        else:
            if verbose:
                # Safe string formatting with bounds checking
                name_width = min(self.event.max_name_length, 30)  # Cap name width
                role_width = min(utils.get_max_role_str_length(), 15)  # Cap role width
                print(
                    f"    {self.name[:name_width].ljust(name_width)} assigned to {assignment.upper()[:role_width].ljust(role_width)}"
                )
            self.assignment = assignment
