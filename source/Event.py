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
        axware_export_csv: str,
        member_attributes_csv: str,
        number_of_heats: int,
        number_of_stations: int,
    ):
        self.number_of_stations = number_of_stations
        self.participants = self.load_participants(
            axware_export_csv, member_attributes_csv
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

    def load_participants(self, axware_export_csv: str, member_attributes_csv: str):
        """
        Loads participants from `axware_export_csv`, then gets their possible work assignments from `member_attributes_csv`.

        TODO: currently requires the CSVs to match the samples exactly, with case sensitivity; loosen these shackles.
        TODO: Also, unjumble this function. Right now it just gets things to work with the sample files on hand.

        Returns:
            list[Participant]: All parsed participants.
        """
        member_attributes_dict = {}
        with open(member_attributes_csv, newline="", encoding="utf-8-sig") as file:
            member_data = csv.DictReader(file)
            for member_row in member_data:
                member_attributes_dict[member_row["name"]] = member_row

        participants = []
        no_shows = []
        with open(axware_export_csv, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, delimiter="\t")
            for axware_row in reader:

                # use full name as "id" for now to account for non-members
                this_fullname = f"{axware_row['First Name']} {axware_row['Last Name']}"
                member_attributes = member_attributes_dict.get(this_fullname)

                # skip if not checked in
                # TODO: save these to a file
                if axware_row["Checkin"].upper() != "YES":
                    no_shows.append(this_fullname)
                    continue

                # scrappy implementation to pivot toward using axware export for now
                is_novice = False
                if axware_row["Class"].upper().startswith("NOV"):
                    is_novice = True
                    category_string = axware_row["Class"][3:]
                elif axware_row["Class"].upper().startswith("SR"):
                    category_string = axware_row["Class"][2:]
                elif axware_row["Class"].upper().startswith("P"):
                    category_string = axware_row["Class"][1:]
                else:
                    category_string = axware_row["Class"]

                participant = Participant(
                    event=self,
                    id=this_fullname,
                    name=this_fullname,
                    category_string=category_string,
                    number=axware_row["Number"],
                    novice=is_novice,
                    **{
                        role: bool(
                            member_attributes.get(role) if member_attributes else False
                        )
                        for role in utils.roles_and_minima(
                            number_of_stations=self.number_of_stations
                        )
                    },
                )
                participants.append(participant)

        if no_shows:
            print(
                f"\n  The following individuals have not checked in and will be omitted:\n"
            )
            [print(f"  - {i}") for i in no_shows]

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
