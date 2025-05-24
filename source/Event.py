import csv
import utils
from Category import Category
from Group import Group
from Heat import Heat
from Participant import Participant


class Event(Group):
    """
    Represents the overall event, composed of participants, categories, and heats.

    Responsible for loading initial state from CSV and organizing the data into
    domain-specific structures.
    """

    def __init__(self, csv_file: str, number_of_heats: int):
        self.participants = self.load_participants(csv_file)
        self.categories = self.load_categories()
        self.heats = self.load_heats(number_of_heats)

    def load_participants(self, csv_file: str):
        """
        Loads participants from a CSV file.

        Returns:
            list[Participant]: All parsed participants.
        """
        participants = []
        with open(csv_file, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                participant = Participant(
                    event=self,
                    id=i,
                    name=row["name"],
                    category_string=row["category"],
                    novice=utils.parse_bool(row["novice"]),
                    **{
                        role: utils.parse_bool(row.get(role))
                        for role in utils.roles_and_minima()
                    },
                )
                participants.append(participant)
        return participants

    def load_categories(self):
        """
        Groups participants into categories.

        Returns:
            dict[str, Category]: Mapping of category name to Category objects.
        """
        categories = {}
        for p in self.participants:
            categories.setdefault(
                p.category_string, Category(self, p.category_string)
            ).add_participant(p)
        return categories

    def load_heats(self, number_of_heats: int):
        """
        Creates heat containers for scheduling.

        Returns:
            dict[int, Heat]: Mapping of heat number to Heat objects.
        """
        return {i: Heat(self, i) for i in range(number_of_heats)}

    @property
    def max_name_length(self):
        """
        Finds the length of the longest name in the event.

        Returns:
            int: Length of the longest name in the event.
        """
        max_length = 0
        for p in self.participants:
            max_length = len(p.name) if len(p.name) > max_length else max_length
        return max_length
