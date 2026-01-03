import csv
import math
import pickle
from autologic import utils
from autologic.category import Category
from autologic.group import Group
from autologic.heat import Heat
from autologic.participant import Participant
from autologic.pdf import generate_event_pdf


class Event(Group):
    """
    Represents the overall event, composed of participants, categories, and heats.

    Responsible for loading initial state from CSV and organizing the data into
    domain-specific structures.
    """

    def __init__(
        self,
        name: str,
        axware_export_tsv: str,
        member_attributes_csv: str,
        custom_assignments: dict[str, str],
        number_of_heats: int,
        number_of_stations: int,
        heat_size_parity: int,
        novice_size_parity: int,
        novice_denominator: int,
        max_iterations: int,
    ):
        self.name = name
        self.number_of_stations = number_of_stations
        self.participants = []
        self.participants, self.no_shows = self.load_participants(
            axware_export_tsv, member_attributes_csv, custom_assignments
        )
        self.categories = self.load_categories()
        self.heats = self.load_heats(number_of_heats)
        self.number_of_heats = number_of_heats
        self.heat_size_parity = heat_size_parity
        self.novice_size_parity = novice_size_parity
        self.novice_denominator = novice_denominator
        self.max_iterations = max_iterations
        self.verbose = False  # TODO: snuck this in here at the last minute; expose this

        # raise an error if event does not have enough qualified participants to fill each role
        self.check_role_minima()

        # calculate heat size restrictions for total participants and novices
        self.mean_heat_size = round(len(self.participants) / number_of_heats)
        self.max_heat_size_delta = math.ceil(len(self.participants) / heat_size_parity)

        self.mean_heat_novice_count = round(
            len(self.get_participants_by_attribute("novice")) / number_of_heats
        )
        self.max_heat_novice_delta = math.ceil(
            len(self.get_participants_by_attribute("novice")) / novice_size_parity
        )

    def __repr__(self):
        return f"{self.name}"

    @property
    def max_name_length(self):
        """
        Finds the length of the longest name in the event.

        Returns:
            int: Length of the longest name in the event.
        """
        max_length = 0 if self.participants else 20
        for p in self.participants:
            max_length = len(p.name) if len(p.name) > max_length else max_length
        return max_length

    def load_participants(
        self,
        axware_export_tsv: str,
        member_attributes_csv: str,
        custom_assignments: dict[str, str],
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

        print(f"\n  Custom assignments")
        print(f"  ------------------\n")
        has_special_assignments = False
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
                if isinstance(special_assignment, list):
                    raise ValueError("Custom assignments must be a single role string.")

                has_special_assignments = (
                    True if special_assignment else has_special_assignments
                )

                # scrappy implementation to pivot toward using axware export for now
                # TODO: clean and functionalize
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

        if not has_special_assignments:
            print("    No special assignments.")

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
            list[Heat]: Heat objects for this Event.
        """
        return [Heat(self) for i in range(number_of_heats)]

    def get_heat(self, heat_number: int):

        return self.heats[heat_number - 1]

    def check_role_minima(self):

        # check if the event has enough qualified participants to fill each role
        print("\n  Role minimums")
        print("  -------------")
        insufficient = False
        for role, minimum in utils.roles_and_minima(
            number_of_stations=self.number_of_stations,
            number_of_novices=len(self.get_participants_by_attribute("novice"))
            / self.number_of_heats,
            novice_denominator=self.novice_denominator,
        ).items():
            qualified = len(self.get_participants_by_attribute(role))
            required = minimum * self.number_of_heats
            warning = (
                " <-- NOT ENOUGH QUALIFIED WORKERS" if qualified < required else ""
            )
            if qualified < required:
                insufficient = True
            print(
                f"  {role.rjust(10)}: {str(qualified).rjust(2)} / {required}{warning}"
            )
        if insufficient:
            raise ValueError("Not enough qualified workers for role(s).")

    def validate(self):

        print(
            f"\n  =============================================================================="
        )
        print(f"\n  [Event validation checks]")

        is_valid = True

        print(
            f"\n  Heat size must be {self.mean_heat_size} +/- {self.max_heat_size_delta}"
        )
        print(
            f"  Novice count must be {self.mean_heat_novice_count} +/- {self.max_heat_novice_delta}"
        )

        for h in self.heats:

            header = f"Heat {h} ({len(h.participants)} total, {len(h.get_participants_by_attribute('novice'))} novices)"
            print(f"\n  {header}")
            print(f"  {'-' * len(header)}\n")
            print(f"    Car classes: {h.categories}\n")

            for role, minimum in utils.roles_and_minima(
                number_of_stations=self.number_of_stations,
                number_of_novices=len(
                    h.compliment.get_participants_by_attribute("novice")
                ),
                novice_denominator=self.novice_denominator,
            ).items():
                assigned = len(h.get_participants_by_attribute("assignment", role))
                print(f"    {assigned} of {minimum} {role}s assigned")

        print(f"\n  Summary\n  -------\n")
        for h in self.heats:
            is_valid = min(
                is_valid, h.valid_size, h.valid_novice_count, h.valid_role_fulfillment
            )

        specialized_novices = False
        for n in self.get_participants_by_attribute("novice"):
            if n.assignment not in ("worker", "special"):
                # allow novices to have special assignments, but log a warning
                # is_valid = False
                specialized_novices = True
                print(
                    f"    Novice assignment warning: {n.name.ljust(self.max_name_length)} assigned to {n.assignment}"
                )
        print() if specialized_novices else None

        if is_valid:
            print(f"    All checks passed.")

        return is_valid

    def to_pickle(self):

        with open(f"{self.name}.pkl", "wb") as f:
            pickle.dump(self, f)

        print(f"\n  Event state saved to {self.name}.pkl")

    # =========================================================================

    def get_work_assignments(self):
        """
        Returns a list of dicts that describe each participant in the event, and their assignments.

        Return format is for input to to_csv and to_pdf.

        TODO: flesh out docs
        """

        work_assignments = []
        for i in range(self.number_of_heats):
            h = self.get_working_i_heat(i + 1)
            for p in sorted(h.participants, key=lambda p: p.name):
                work_assignments.append(
                    {
                        "heat": h.working,
                        "name": p.name,
                        "class": p.axware_category,
                        "number": p.number,
                        "assignment": f"{p.assignment}",
                        "checked_in": "",
                    }
                )

        return work_assignments

    def get_run_assignments(self):
        """
        Returns a list of dicts that describe each participant in the event, and their run group.

        Return format is for input to to_pdf.

        TODO: flesh out docs
        """

        run_assignments = []
        for h in self.heats:
            for p in sorted(h.participants, key=lambda p: p.name):
                run_assignments.append(
                    {
                        "heat": h.running,
                        "name": p.name,
                        "class": p.axware_category,
                        "number": p.number,
                        "tally": "",
                    }
                )

        return run_assignments

    def get_working_i_heat(self, i):

        for h in self.heats:
            if h.working == i:
                return h

        raise ValueError(f"No heats assigned to work group {i}")

    def get_heat_assignments(self, verbose=False):
        """
        Returns a list of lists that describe each heat in the event, and their categories.

        Return format is for input to to_pdf.

        TODO: flesh out docs
        """

        heat_assignments = []
        for i, h in enumerate(self.heats):

            this_heat_run_work = f"Running {h.running} | Working {h.working}"
            these_classes = ", ".join(
                sorted([i.name for i in h.categories], key=str.lower)
            )

            heat_assignments.append([this_heat_run_work, these_classes])

        if verbose:
            [
                print(f"Heat {i + 1} | {assignment[0]} | {assignment[1]}")
                for i, assignment in enumerate(heat_assignments)
            ]

        return heat_assignments

    def to_csv(self):
        """
        TODO: flesh out docs
        """

        with open(f"{self.name}.csv", "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "heat",
                    "name",
                    "class",
                    "number",
                    "assignment",
                    "checked_in",
                ],
            )
            writer.writeheader()
            writer.writerows(self.get_work_assignments())
            print(f"\n  Worker assignment sheet saved to {self.name}.csv")

    def to_pdf(self):
        """Generate the worker/grid tracking PDF."""

        generate_event_pdf(self)
