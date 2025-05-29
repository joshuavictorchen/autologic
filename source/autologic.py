import click
import csv
import math
import pandas as pd
import random
import yaml

from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

import utils
from Event import Event

# =============================================================================
# TODO: refactor for sanity and flexibility
#       this should be split out into separate functions and perhaps even modules
#       left as-is for quick prototype development ahead of a pilot event
# =============================================================================


def randomize_heats(event, number_of_heats):
    """
    Randomly assign categories (car classes) to heats.

    TODO: This is overly restrictive! It works for now but should be updated in the future.
          Categories are EVENLY DISTRIBUTED across heats even though category size may vary significantly.
    """
    categories = list(event.categories.values())
    random.shuffle(categories)
    for i, c in enumerate(categories):
        c.set_heat(i % number_of_heats)


class Config(BaseModel):
    axware_export_tsv: Path = Field(..., description="Path to AXWare export TSV file.")
    member_attributes_csv: Path = Field(
        ..., description="Path to member attribute CSV file."
    )
    number_of_heats: int = Field(
        3, description="Number of heats to divide participants into."
    )
    number_of_stations: int = Field(
        5, description="Number of worker stations for the course."
    )
    custom_assignments: dict[str | int, str] = Field(
        default_factory=dict,
        description="A dictionary of member IDs to their fixed role assignments.",
    )
    heat_size_parity: int = Field(
        25, description="Smaller values enforce tighter heat size balance."
    )
    novice_size_parity: int = Field(
        10, description="Smaller values enforce tighter novice balance across heats."
    )
    novice_denominator: int = Field(
        3, description="Min instructors in heat = novices / denominator."
    )
    max_iterations: int = Field(
        10000, description="Max number of attempts before giving up."
    )

    def validate_paths(self):
        """Ensure all paths exist and are files."""
        for path_attr in ["axware_export_tsv", "member_attributes_csv"]:
            p = getattr(self, path_attr)
            if not p.exists():
                raise FileNotFoundError(f"{path_attr} does not exist: {p}")
            if not p.is_file():
                raise ValueError(f"{path_attr} is not a file: {p}")


def load_config(ctx, param, value: Path) -> Config:
    try:
        with open(value, "r") as f:
            data = yaml.safe_load(f)
        config = Config(**data)
        config.validate_paths()
        return config
    except (ValidationError, FileNotFoundError, ValueError) as e:
        raise click.BadParameter(f"Invalid config: {e}")
    except Exception as e:
        raise click.BadParameter(f"Failed to load config: {e}")


@click.command(context_settings={"max_content_width": 120})
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    callback=load_config,
    required=True,
    help="Path to event configuration file.",
)
def cli(config: Config):
    # Unpack fields to local variables
    main(**config.model_dump())


def main(
    axware_export_tsv,
    member_attributes_csv,
    number_of_heats,
    custom_assignments,
    number_of_stations,
    heat_size_parity,
    novice_size_parity,
    novice_denominator,
    max_iterations,
):
    """Parse event participants and generate heat assignments with role coverage and balanced sizes."""

    event = Event(
        axware_export_tsv=axware_export_tsv,
        member_attributes_csv=member_attributes_csv,
        custom_assignments={
            str(key): value for key, value in custom_assignments.items()
        },  # ensure all keys are str
        number_of_heats=number_of_heats,
        number_of_stations=number_of_stations,
    )

    # check if the event has enough qualified participants to fill each role
    print("\n  Role minimums")
    print("  -------------")
    insufficient = False
    role_ratios = {}
    for role, minimum in utils.roles_and_minima(
        number_of_stations=number_of_stations,
        number_of_novices=len(event.get_participants_by_attribute("novice"))
        / number_of_heats,
        novice_denominator=novice_denominator,
    ).items():
        qualified = len(event.get_participants_by_attribute(role))
        required = minimum * number_of_heats
        role_ratios[role] = (
            qualified / required if required > 0 else 100
        )  # arbitrarily large
        warning = " <-- NOT ENOUGH QUALIFIED WORKERS" if qualified < required else ""
        if qualified < required:
            insufficient = True
        print(f"  {role.rjust(10)}: {str(qualified).rjust(2)} / {required}{warning}")
    if insufficient:
        raise ValueError("Not enough qualified workers for role(s).")

    # calculate heat size restrictions for total participants and novices
    mean_group_size = round(len(event.participants) / number_of_heats)
    max_group_delta = math.ceil(len(event.participants) / heat_size_parity)
    mean_novice_count = round(
        len(event.get_participants_by_attribute("novice")) / number_of_heats
    )
    max_novice_delta = math.ceil(
        len(event.get_participants_by_attribute("novice")) / novice_size_parity
    )

    # keep randomizing heats until all criteria are met (lol)
    rules_satisfied = False
    iteration = -1
    while not rules_satisfied and iteration < max_iterations:

        iteration += 1
        rules_satisfied = True
        skip_iteration = False
        print(
            f"\n  ==================================================\n\n  [Iteration {iteration}]"
        )

        randomize_heats(event, number_of_heats)

        print(f"\n  Heat size must be {mean_group_size} +/- {max_group_delta}")
        print(f"  Novice count must be {mean_novice_count} +/- {max_novice_delta}")

        # clear assignments from the previous iteration
        # TODO: make a p.clear_assignment() function that handles this and other logic trees
        for p in event.participants:
            p.assignment = p.special_assignment if p.special_assignment else None

        # check if heat constraints are satisfied (size, role fulfillments)
        for h in event.heats.values():

            # skip this loop if a prior heat failed checks
            if skip_iteration:
                break

            # check total heat size constraints
            heat_size = len(h.participants)
            if abs(mean_group_size - heat_size) > max_group_delta:
                rules_satisfied = False
                skip_iteration = True
                print(f"\n  Heat {h} rejected: participant count of {heat_size}")
                break

            # check heat novice count constraints
            novice_count = len(h.get_participants_by_attribute("novice"))
            if abs(mean_novice_count - novice_count) > max_novice_delta:
                rules_satisfied = False
                skip_iteration = True
                print(f"\n  Heat {h} rejected: novice count of {novice_count}")
                break

            header = f"Heat {h} ({heat_size} total, {novice_count} novices)"
            print(f"\n  {header}")
            print(f"  {'-' * len(header)}\n")
            print(f"    Car classes: {h.categories}\n")

            # check if number of qualified participants for each role exceed the minima required
            role_extras = {}
            for role, minimum in utils.roles_and_minima(
                number_of_stations=number_of_stations,
                number_of_novices=novice_count,
                novice_denominator=novice_denominator,
            ).items():
                qualified = len(h.get_participants_by_attribute(role))
                role_extras[role] = (
                    qualified - minimum
                )  # used later to assign workers to roles based on need
                print(f"    {qualified} of {minimum} {role}s required")
                if qualified < minimum:
                    rules_satisfied = False
                    skip_iteration = True
                    print(
                        f"\n    Heat {h} rejected: unable to fill {role.upper()} role(s)"
                    )
                    break

            if rules_satisfied:
                # just because qualified >= minimum doesn't mean we're in the clear
                # some participants are qualified for multiple roles, but can only fulfill one for their heat
                # try to assign roles now
                # start with roles that have the smallest delta between qualified participants and minimum requirements
                # TODO: this is another thing that really needs to be split out
                print()

                # assign special assignments - redundant but is helpful for console output
                # TODO: remove this sloppiness
                for p in h.get_participants_by_attribute(
                    attribute="assignment", value="special"
                ):
                    p.set_assignment("special")

                for role in utils.sort_dict_by_value(role_extras):
                    if skip_iteration:
                        break

                    # calculate how many slots need to be filled for this role, accounting for custom pre-assignments
                    pre_assigned_participants = h.get_participants_by_attribute(
                        attribute="assignment", value=role
                    )
                    for p in pre_assigned_participants:
                        p.set_assignment(
                            role
                        )  # redundant but is helpful for console output
                    pre_assigned_count = len(pre_assigned_participants)
                    baseline_required_count = utils.roles_and_minima(
                        number_of_stations=number_of_stations,
                        number_of_novices=novice_count,
                        novice_denominator=novice_denominator,
                    )[role]
                    actual_required_count = baseline_required_count - pre_assigned_count

                    # fill the actual required slots for this role
                    for _ in range(actual_required_count):
                        available = h.get_available(role)
                        if not available:
                            rules_satisfied = False
                            print(
                                f"\n  Heat {h} rejected: unable to fill {role} role(s)"
                            )
                            skip_iteration = True
                            break
                        else:
                            available[0].set_assignment(role)

                # now assign everyone else to worker role
                for worker in h.get_available(role=None):
                    worker.set_assignment("worker")

    if not rules_satisfied:
        print(f"\n\n  Could not create heats in {max_iterations} iterations.\n")
        exit(1)

    print(f"\n  ---\n\n  >>> Iteration {iteration} accepted <<<")

    # print summary statements and export to csv
    # TODO: these should be their own functions (like many items above)
    if event.no_shows:
        print(
            f"\n  The following individuals have not checked in and are therefore excluded:\n"
        )
        [print(f"  - {i}") for i in event.no_shows]

    rows = []
    for h in event.heats.values():
        captain_count = 0
        worker_count = 0
        for p in sorted(h.participants, key=lambda p: p.name):
            # TODO: we're reaching elongated levels of code spaghettification here
            #       append station number to corner captain assignments in the printout
            #       same with workers
            string_modifier = ""
            if p.assignment == "captain":
                string_modifier = f"-{captain_count}"
                captain_count += 1
            elif p.assignment == "worker":
                string_modifier = f"-{worker_count % number_of_stations}"
                worker_count += 1
            rows.append(
                {
                    "heat": h.number,
                    "name": p.name,
                    "class": p.category_string,
                    "number": p.number,
                    "assignment": f"{p.assignment}{string_modifier}",
                    "checked_in": "",
                }
            )

    with open("autologic-export.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["heat", "name", "class", "number", "assignment", "checked_in"],
        )
        writer.writeheader()
        writer.writerows(rows)
        print(f"\n  Worker assignment sheet saved to autologic-export.csv")

    ###########################################################################
    # this code needs to be cleaned and moved
    # it has been shamefully left as-is for the time being
    # but for now it generates a decently nice PDF

    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth

    # define column orders
    headers = ["heat", "name", "class", "number", "assignment", "checked_in"]
    display_headers = ["Heat", "Name", "Class", "Number", "Assignment", "Checked In"]
    table_data = [display_headers] + [
        [str(row[h]).upper() for h in headers] for row in rows
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

    # build document
    doc = SimpleDocTemplate(
        "autologic-export.pdf", pagesize=letter, topMargin=0.75 * inch
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

    # build document
    elements = [
        Paragraph("Autologic Worker Assignments", styles["Title"]),
        Spacer(1, 6),
        table,
    ]

    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"\n  Worker assignment printout saved to autologic-export.pdf\n")

    ###########################################################################


if __name__ == "__main__":
    cli()
