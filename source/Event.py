import csv
import math
import pickle
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
        name: str,
        axware_export_tsv: str,
        member_attributes_csv: str,
        custom_assignments: dict[str, str | list[str]],
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

                # special assignment may be a str or a list of strings
                # if the latter, then randomly choose one
                # TODO: outsource this to the algorithm (don't do this here)
                special_assignment = (
                    random.choice(special_assignment)
                    if type(special_assignment) == list
                    else special_assignment
                )

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
        """
        TODO: flesh out docs... and untangle this GPT-enabled mess
        """

        # TODO: this last-minute semi-hardcoded function gets the job done but is quite shameful as-is

        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            PageBreak,
            Paragraph,
            Spacer,
        )
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase.pdfmetrics import stringWidth

        # define column orders
        headers = ["heat", "name", "class", "number", "assignment", "checked_in"]
        display_headers = [
            "Working",
            "Name",
            "Class",
            "Number",
            "Assignment",
            "Checked In",
        ]
        table_data = [display_headers] + [
            [str(row[h]).upper() for h in headers]
            for row in self.get_work_assignments()
        ]

        # custom canvas to support "Page X of Y" footer
        class NumberedCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._saved_page_states = []

            def showPage(self):
                self._saved_page_states.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self._saved_page_states)
                for state in self._saved_page_states:
                    self.__dict__.update(state)
                    self.draw_page_number(num_pages)
                    super().showPage()
                super().save()

            def draw_page_number(self, total):
                self.setFont("Courier", 9)
                text = f"Page {self.getPageNumber()} of {total}"
                self.drawCentredString(self._pagesize[0] / 2, 0.5 * inch, text)

        # get styles
        styles = getSampleStyleSheet()
        centered_heading = ParagraphStyle(
            name="CenteredHeading",
            parent=styles["Heading2"],
            alignment=TA_CENTER,
        )

        # build document
        doc = SimpleDocTemplate(
            f"{self.name}.pdf", pagesize=letter, topMargin=0.75 * inch
        )

        # dynamically compute relative column widths
        def compute_scaled_col_widths(data, font_name, font_size, padding, total_width):
            num_cols = len(data[0])
            max_widths = [0] * num_cols
            for row in data:
                for i, cell in enumerate(row):
                    text = str(cell)
                    width = stringWidth(text, font_name, font_size)
                    max_widths[i] = max(max_widths[i], width)
            # Add padding to each column
            raw_widths = [w + padding for w in max_widths]
            raw_total = sum(raw_widths)
            # Scale to fit total available width
            return [w * total_width / raw_total for w in raw_widths]

        # available printable width
        available_width = letter[0] - doc.leftMargin - doc.rightMargin

        # compute dynamic column widths scaled to fit full page width
        col_widths = compute_scaled_col_widths(
            data=table_data,
            font_name="Courier",
            font_size=9,
            padding=12,
            total_width=available_width,
        )

        # create table with scaled widths
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # find column indices for left-aligned columns
        name_idx = headers.index("name")
        assignment_idx = headers.index("assignment")

        # style table
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (name_idx, 1), (name_idx, -1), "LEFT"),
                    ("ALIGN", (assignment_idx, 1), (assignment_idx, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Courier"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )

        # shoved in at the last minute; standardize and refactor

        # heat/class table styling
        heat_class_rows = [["Heat", "Classes"]] + self.get_heat_assignments()

        heat_col_widths = compute_scaled_col_widths(
            data=heat_class_rows,
            font_name="Courier",
            font_size=9,
            padding=12,
            total_width=available_width,
        )

        heat_class_table = Table(
            heat_class_rows, colWidths=heat_col_widths, repeatRows=1
        )

        heat_class_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),  # Left column left
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),  # Right column left
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Courier-Bold",
                    ),  # Only header row bold
                    ("FONTNAME", (0, 1), (-1, -1), "Courier"),  # Body rows normal
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )

        # another shoved-in item - heat summary / role fulfillments

        roles = [
            "instructor",
            "timing",
            "grid",
            "start",
            "captain",
            "worker",
            "special",
        ]
        summary_data = [
            [
                "Group",
                "Instructor",
                "Timing",
                "Grid",
                "Start",
                "Captain",
                "Worker",
                "Special",
                "Total",
            ]
        ]

        for idx, heat in enumerate(self.heats, start=1):
            novices = sum(1 for p in heat.participants if p.novice)
            counts = {role: 0 for role in roles}
            for p in heat.participants:
                if p.assignment in counts:
                    counts[p.assignment] += 1

            summary_data.append(
                [
                    str(idx),
                    str(counts["instructor"]),
                    str(counts["timing"]),
                    str(counts["grid"]),
                    str(counts["start"]),
                    str(counts["captain"]),
                    str(counts["worker"]),
                    str(counts["special"]),
                    f"{str(len(heat.participants))} ({novices} Novices)",
                ]
            )

        summary_col_widths = compute_scaled_col_widths(
            data=summary_data,
            font_name="Courier",
            font_size=9,
            padding=12,
            total_width=available_width,
        )
        summary_table = Table(summary_data, colWidths=summary_col_widths, repeatRows=1)
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Courier"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )

        # grid worker table: sorted by class and number, without assignment

        grid_worker_headers = ["heat", "name", "class", "number", "tally"]
        display_grid_worker_headers = [
            "Running",
            "Name",
            "Class",
            "Number",
            "Run Tally",
        ]

        sorted_assignments = sorted(
            self.get_run_assignments(),
            key=lambda row: (row["heat"], row["class"], row["number"]),
        )

        grid_worker_table_data = [display_grid_worker_headers] + [
            [str(row[h]).upper() for h in grid_worker_headers]
            for row in sorted_assignments
        ]

        grid_worker_col_widths = compute_scaled_col_widths(
            data=grid_worker_table_data,
            font_name="Courier",
            font_size=9,
            padding=12,
            total_width=available_width,
        )

        grid_worker_table = Table(
            grid_worker_table_data,
            colWidths=grid_worker_col_widths,
            repeatRows=1,
        )

        name_idx_cn = grid_worker_headers.index("name")

        grid_worker_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (name_idx_cn, 1), (name_idx_cn, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Courier"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )

        # build document
        elements = [
            Paragraph(f"{self.name}", styles["Title"]),
            heat_class_table,
            Spacer(1, 6),
            summary_table,
            Spacer(1, 6),
            Paragraph("Worker Tracking", centered_heading),
            table,
            PageBreak(),
            Paragraph("Grid Tracking", centered_heading),
            grid_worker_table,
        ]

        doc.build(elements, canvasmaker=NumberedCanvas)
        print(f"\n  Worker assignment printout saved to {self.name}.pdf")
