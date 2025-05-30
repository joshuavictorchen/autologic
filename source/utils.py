import csv

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

MIN_INSTRUCTOR_PER_HEAT = 3  # this is modified in roles_and_minima()
MIN_TIMING_PER_HEAT = 2
MIN_START_PER_HEAT = 1
MIN_GRID_PER_HEAT = 2


def sort_dict_by_value(d: dict, ascending: bool = True) -> dict:
    """
    Sorts a dictionary by its values.

    Args:
        d (dict): Dictionary to sort.
        ascending (bool): Sort direction. True for ascending, False for descending.

    Returns:
        dict: New dictionary sorted by value.
    """
    return dict(sorted(d.items(), key=lambda x: x[1], reverse=not ascending))


def sort_dict_by_nested_value(d: dict, key: str, ascending: bool = True) -> dict:
    """
    Sorts a dictionary by a specific key within each value dictionary.

    Args:
        d (dict): Dictionary to sort. Values must be dicts.
        key (str): Nested key to sort by.
        ascending (bool): Sort direction. True for ascending, False for descending.

    Returns:
        dict: New dictionary sorted by the nested key.
    """
    return dict(sorted(d.items(), key=lambda x: x[1][key], reverse=not ascending))


def sort_dict_by_nested_keys(d, keys_with_order):
    """
    Performs a multi-key sort on a dictionary of nested dictionaries.

    Args:
        d (dict): Dictionary where each value is itself a dictionary.
        keys_with_order (list[tuple[str, bool]]): List of (key, ascending) tuples.

    Returns:
        dict: New dictionary sorted by multiple nested keys.
    """
    items = list(d.items())

    for key, ascending in reversed(keys_with_order):
        items.sort(
            key=lambda item: item[1].get(
                key, float("-inf") if not ascending else float("inf")
            ),
            reverse=not ascending,
        )

    return dict(items)


def get_max_role_str_length():
    """
    Finds the length of the longest role name in the event.

    Returns:
        int: Length of the longest role name in the event.
    """
    max_length = 0
    for r in roles_and_minima("_"):
        max_length = len(r) if len(r) > max_length else max_length
    return max_length


def roles_and_minima(number_of_stations, number_of_novices=1, novice_denominator=3):
    """
    Roles and their minimum required number of individuals per heat.

    The minimum number of corner captains in a heat is equal to `number_of_stations`.

    The minimum number of instructors in a heat is equal to `number_of_novices`
    divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.

    Args:
        number_of_stations (int): Number of worker stations for the course.
        number_of_novices (int): Number of novices in the heat.
        novice_denominator (int): Ratio of novices to instructors.

    Returns:
        dict: Role names and their minimum number of individuals per heat.
    """

    return {
        "instructor": max(
            MIN_INSTRUCTOR_PER_HEAT, round(number_of_novices / novice_denominator)
        ),
        "timing": MIN_TIMING_PER_HEAT,
        "grid": MIN_GRID_PER_HEAT,
        "start": MIN_START_PER_HEAT,
        "captain": number_of_stations,
    }


def autologic_event_to_csv(work_assignments: list[dict]):
    """
    Takes an Event summary list and makes a CSV of it.

    TODO: flesh out docs
    """

    with open("autologic-export.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["heat", "name", "class", "number", "assignment", "checked_in"],
        )
        writer.writeheader()
        writer.writerows(work_assignments)
        print(f"\n  Worker assignment sheet saved to autologic-export.csv")


def autologic_event_to_pdf(work_assignments: list[dict]):
    """
    Takes an Event summary list and makes a PDF of it.

    TODO: flesh out docs
    """

    # define column orders
    headers = ["heat", "name", "class", "number", "assignment", "checked_in"]
    display_headers = ["Heat", "Name", "Class", "Number", "Assignment", "Checked In"]
    table_data = [display_headers] + [
        [str(row[h]).upper() for h in headers] for row in work_assignments
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
    print(f"\n  Worker assignment printout saved to autologic-export.pdf")
