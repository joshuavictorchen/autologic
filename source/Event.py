import csv
import random
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
        axware_export_tsv: str,
        member_attributes_csv: str,
        custom_assignments: dict[str, str | list[str]],
        number_of_heats: int,
        number_of_stations: int,
    ):
        self.number_of_stations = number_of_stations
        self.participants, self.no_shows = self.load_participants(
            axware_export_tsv, member_attributes_csv, custom_assignments
        )
        self.categories = self.load_categories()
        self.heats = self.load_heats(number_of_heats)
        self.number_of_heats = number_of_heats

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

    def load_participants(
        self,
        axware_export_tsv: str,
        member_attributes_csv: str,
        custom_assignments: dict[str, str | list[str]],
    ):
        """
        Loads participants from `axware_export_tsv`, then gets their possible work assignments from `member_attributes_csv`.

        Checks custom_assignments dictionary from `sample_event_config.yaml` for static, special assignments.

        TODO: Currently requires the CSVs to match the samples exactly, with case sensitivity; loosen these shackles.
        TODO: Also, unjumble this function. Right now it just gets things to work with the sample files on hand.

        Returns:
            list[Participant]: All participants that have checked into the event.
            list[Participant]: All participants that have NOT checked into the event.
        """
        member_attributes_dict = {}
        with open(member_attributes_csv, newline="", encoding="utf-8-sig") as file:
            member_data = csv.DictReader(file)
            for member_row in member_data:
                member_attributes_dict[member_row["id"]] = member_row

        participants = []
        no_shows = []
        with open(axware_export_tsv, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, delimiter="\t")
            for axware_row in reader:

                this_firstname = f"{axware_row['First Name']}"
                this_lastname = f"{axware_row['Last Name']}"
                this_fullname = f"{axware_row['First Name']} {axware_row['Last Name']}"
                # use full name as the ID instead of member number if no member number found
                this_id = (
                    axware_row["Member #"] if axware_row["Member #"] else this_fullname
                )
                member_attributes = member_attributes_dict.get(axware_row["Member #"])
                special_assignment = custom_assignments.get(axware_row["Member #"])
                # special assignment may be a str or a list of strings
                # if the latter, then randomly choose one
                special_assignment = (
                    random.choice(special_assignment)
                    if type(special_assignment) == list
                    else special_assignment
                )

                # scrappy implementation to pivot toward using axware export for now
                is_novice = False
                axware_category = axware_row["Class"].upper()
                if axware_category.startswith("NOV"):
                    is_novice = True
                    category_string = axware_category[3:]
                elif axware_category.startswith("SR"):
                    category_string = "SR"
                elif axware_category.startswith("P"):
                    category_string = "P"
                else:
                    category_string = axware_row["Class"]

                no_show = True if axware_row["Checkin"].upper() != "YES" else False

                participant = Participant(
                    event=self if not no_show else None,
                    id=this_id,
                    name=f"{this_lastname}, {this_firstname}",
                    category_string=category_string,
                    axware_category=axware_category,
                    number=axware_row["Number"],
                    novice=is_novice,
                    special_assignment=special_assignment,
                    **{
                        role: bool(
                            member_attributes.get(role) if member_attributes else False
                        )
                        for role in utils.roles_and_minima(
                            number_of_stations=self.number_of_stations
                        )
                    },
                )

                if no_show:
                    no_shows.append(participant)
                else:
                    participants.append(participant)

        return participants, no_shows

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
            dict[int, Heat]: Mapping of 1-indexed heat number to Heat objects.
        """
        return {i + 1: Heat(self, i + 1) for i in range(number_of_heats)}

    def get_work_assignments(self):
        """
        Returns a list of dicts that describe each participant in the event, and their assignments.

        TODO: flesh out docs
        """

        if self.no_shows:
            print(
                f"\n  The following individuals have not checked in and are therefore excluded:\n"
            )
            [print(f"  - {i}") for i in self.no_shows]

        work_assignments = []
        for h in self.heats.values():
            captain_count = 0
            worker_count = 0
            for p in sorted(h.participants, key=lambda p: p.name):
                # TODO: we're reaching elongated levels of code spaghettification here
                #       append station number to corner captain assignments in the printout
                #       same with workers
                string_modifier = ""
                if p.assignment == "captain":
                    string_modifier = f"-{captain_count + 1}"
                    captain_count += 1
                elif p.assignment == "worker":
                    string_modifier = f"-{(worker_count % self.number_of_stations) + 1}"
                    worker_count += 1
                work_assignments.append(
                    {
                        "heat": h.number,
                        "name": p.name,
                        "class": p.axware_category,
                        "number": p.number,
                        "assignment": f"{p.assignment}{string_modifier}",
                        "checked_in": "",
                    }
                )

        return work_assignments

    def get_heat_assignments(self):
        """
        Returns a list of lists that describe each heat in the event, and their categories.

        TODO: flesh out docs
        """

        work_offset = 2 if self.number_of_heats > 4 else 1

        heat_assignments = []
        for i, h in enumerate(self.heats.values()):

            running_heat = (i % self.number_of_heats) + 1
            working_heat = (running_heat + work_offset) % self.number_of_heats + 1

            this_heat = f"Running {running_heat} | Working {working_heat}"
            these_classes = ", ".join([i.name for i in h.categories])

            heat_assignments.append([this_heat, these_classes])

        return heat_assignments
