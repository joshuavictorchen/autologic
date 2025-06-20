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
        axware_category (str): Category as displayed in AXWare, i.e. NOVCST instead of just CST.
        novice (bool): Whether the participant is a novice.
        special_assignment (str or None): Participant's special assignment if they have one, this will never be reassigned.
        assignment (str or None): Currently assigned role.
        Other attributes (like 'instructor', 'timing', etc.) are added dynamically.
    """

    def __init__(
        self,
        event,
        id: int,
        name: str,
        category_string: str,
        axware_category: str,
        novice: bool,
        special_assignment: str | None,
        **kwargs,
    ):
        self.event = event
        self.id = id
        self.name = name
        self.category_string = category_string
        self.axware_category = axware_category
        self.novice = novice
        self.assignment = None
        self.special_assignment = special_assignment

        # dynamically assign additional role flags (e.g., instructor=True)
        [setattr(self, key, value) for key, value in kwargs.items()]

        # if participant has a special assignment, assign them immediately
        (
            self.set_assignment(special_assignment, verbose=False)
            if special_assignment
            else None
        )

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

    def set_assignment(
        self, assignment, verbose=True, show_previous=False, manual_override=False
    ):
        """
        Assigns a role to this participant if they are qualified for it.

        Args:
            assignment (str): The role to assign.
        """

        assignment_string = f"    {self.name.ljust(self.event.max_name_length)} assigned to {assignment.upper().ljust(utils.get_max_role_str_length())}"
        special_string = "" if assignment == "special" else "(custom assignment)"
        suffix = (
            f" (previously: {self.assignment.upper() if self.assignment else 'NONE'})"
            if show_previous
            else ""
        )

        if manual_override:
            print(f"{assignment_string}{suffix}") if verbose else None
            self.assignment = assignment.lower()
            return

        # special assignments take precedence
        # TODO: eliminate redundancy in this function
        if self.special_assignment:
            if assignment == self.special_assignment:
                self.assignment = assignment
                print(f"{assignment_string} {special_string}") if verbose else None
            else:
                raise ValueError(
                    f"{self} was attempted to be reassigned from their special assignment of {self.special_assignment.upper()}"
                )

        # reject unqualified assignments (everyone is qualified to be a worker)
        elif not getattr(self, assignment, False) and not assignment.lower().startswith(
            WORKER_ASSIGNMENT
        ):
            raise ValueError(
                f"    {self} was attemped to be assigned to {assignment.upper()}, but is not qualified"
            )
        else:
            if verbose:
                print(f"{assignment_string}{suffix}")
            self.assignment = assignment
