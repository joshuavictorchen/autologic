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

    def __init__(
        self,
        msr_export_csv: str,
        member_attributes_csv: str,
        number_of_heats: int,
        number_of_stations: int,
    ):
        self.number_of_stations = number_of_stations
        self.participants = self.load_participants(
            msr_export_csv, member_attributes_csv
        )
        self.categories = self.load_categories()
        self.heats = self.load_heats(number_of_heats)

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

    def load_participants(self, msr_export_csv: str, member_attributes_csv: str):
        """
        Loads participants from `msr_export_csv`, then gets their possible work assignments from `member_attributes_csv`.

        TODO: currently requires the CSVs to match the samples exactly, with case sensitivity; loosen these shackles. Also, unjumble this function.

        Returns:
            list[Participant]: All parsed participants.
        """
        member_attributes_dict = {}
        with open(member_attributes_csv, newline="", encoding="utf-8-sig") as file:
            member_data = csv.DictReader(file)
            for row in member_data:
                member_attributes_dict[row["id"]] = row

        participants = []
        with open(msr_export_csv, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                this_id = utils.get_formatted_member_number(row["Member #"])
                member_attributes = member_attributes_dict.get(this_id)
                participant = Participant(
                    event=self,
                    id=this_id,
                    name=row["Name"],
                    category_string=(
                        row["Class"]
                        if row["Modifier"] in ["", "NOV"]
                        else row["Modifier"]
                    ),
                    novice=utils.parse_bool(row["Modifier"] == "NOV"),
                    **{
                        role: utils.parse_bool(
                            member_attributes.get(role) if member_attributes else 0
                        )
                        for role in utils.roles_and_minima(
                            number_of_stations=self.number_of_stations
                        )
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
