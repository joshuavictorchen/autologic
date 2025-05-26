class Group:
    """
    A base class representing a collection of participants.
    Provides methods for querying and filtering based on roles and attributes.
    """

    def __init__(self):
        self.participants = []

    @property
    def total(self):
        """Returns the total number of participants in the group."""
        return len(self.participants)

    def get_participants_by_attribute(self, attribute, value=True):
        """
        Returns all participants with a specific attribute value.

        Args:
            attribute (str): The attribute to check.
            value (any): The expected value of the attribute.

        Returns:
            list: Matching participants.
        """
        return [p for p in self.participants if getattr(p, attribute, None) == value]

    def get_participant_by_id(self, id):
        """
        Returns the participant with the specified ID.

        Raises:
            ValueError if no participant with the given ID is found.
        """
        for p in self.participants:
            if p.id == id:
                return p
        raise ValueError(f"Participant ID {id} not found")

    def get_available(self, role, has_sole_role=False):
        """
        Returns participants who are eligible for a role and not yet assigned.

        Args:
            role (str): The role to check. If set to None, then returns all unassigned participants.
            has_sole_role (bool): If True, filters to participants with exactly one role.

        Returns:
            list: Available and qualified participants.
        """
        if not role:
            return [p for p in self.participants if not p.assignment]
        if has_sole_role:
            return [
                p
                for p in self.participants
                if getattr(p, role, False) and p.has_sole_role and not p.assignment
            ]
        return [
            p for p in self.participants if getattr(p, role, False) and not p.assignment
        ]

    def has_role(self, role):
        """
        Checks whether any participant is available for the given role.

        Args:
            role (str): The role to check.

        Returns:
            bool: True if at least one participant is eligible.
        """
        return len(self.get_available(role)) > 0
