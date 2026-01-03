from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FONT_NAME = "Courier"
FONT_NAME_BOLD = "Courier-Bold"
FONT_SIZE = 9
CELL_PADDING = 12
# reportlab table sizing is based on absolute widths; keep these constants together for consistency


def generate_event_pdf(event, output_path=None):
    """
    Build the worker/run assignment PDF for an event.

    Args:
        event: Event instance to render (must supply assignment/run data helpers).
        output_path (str|None): Optional path override; defaults to f"{event.name}.pdf".

    Returns:
        str: Path to the generated PDF.
    """

    pdf_path = output_path or f"{event.name}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.75 * inch)
    # usable horizontal space after subtracting margins; reused across tables for consistent sizing
    available_width = letter[0] - doc.leftMargin - doc.rightMargin

    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        name="CenteredHeading",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
    )

    # each section/table is built separately to keep layout concerns isolated
    worker_table = _build_worker_table(event, available_width)
    heat_class_table = _build_heat_class_table(event, available_width)
    summary_table = _build_summary_table(event, available_width)
    grid_worker_table = _build_grid_worker_table(event, available_width)

    elements = [
        Paragraph(f"{event.name}", styles["Title"]),
        heat_class_table,
        Spacer(1, 6),
        summary_table,
        Spacer(1, 6),
        Paragraph("Worker Tracking", heading_style),
        worker_table,
        PageBreak(),
        Paragraph("Grid Tracking", heading_style),
        grid_worker_table,
    ]

    # custom canvas prints "Page X of Y" in the footer
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"\n  Worker assignment printout saved to {event.name}.pdf")
    return pdf_path


def _build_worker_table(event, available_width):
    """Build the worker assignment table (working group, name, class, number, assignment)."""

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
        [str(row[h]).upper() for h in headers] for row in event.get_work_assignments()
    ]

    col_widths = _compute_scaled_col_widths(
        data=table_data,
        font_name=FONT_NAME,
        font_size=FONT_SIZE,
        padding=CELL_PADDING,
        total_width=available_width,
    )
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    name_idx = headers.index("name")
    assignment_idx = headers.index("assignment")

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (name_idx, 1), (name_idx, -1), "LEFT"),
                ("ALIGN", (assignment_idx, 1), (assignment_idx, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE),
            ]
        )
    )
    return table


def _build_heat_class_table(event, available_width):
    """Build the heat/class summary table (run/work pairing + class list per heat)."""

    heat_class_rows = [["Heat", "Classes"]] + event.get_heat_assignments()
    col_widths = _compute_scaled_col_widths(
        data=heat_class_rows,
        font_name=FONT_NAME,
        font_size=FONT_SIZE,
        padding=CELL_PADDING,
        total_width=available_width,
    )
    heat_class_table = Table(heat_class_rows, colWidths=col_widths, repeatRows=1)
    heat_class_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE),
            ]
        )
    )
    return heat_class_table


def _build_summary_table(event, available_width):
    """Build the per-heat role fulfillment summary table (counts by role + total/novices)."""

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

    for idx, heat in enumerate(event.heats, start=1):
        novices = sum(1 for participant in heat.participants if participant.novice)
        counts = {role: 0 for role in roles}
        for participant in heat.participants:
            if participant.assignment in counts:
                counts[participant.assignment] += 1

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

    col_widths = _compute_scaled_col_widths(
        data=summary_data,
        font_name=FONT_NAME,
        font_size=FONT_SIZE,
        padding=CELL_PADDING,
        total_width=available_width,
    )
    summary_table = Table(summary_data, colWidths=col_widths, repeatRows=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE),
            ]
        )
    )
    return summary_table


def _build_grid_worker_table(event, available_width):
    """Build the run-group grid table sorted by class and number (no assignment column)."""

    grid_worker_headers = ["heat", "name", "class", "number", "tally"]
    display_grid_worker_headers = ["Running", "Name", "Class", "Number", "Run Tally"]

    sorted_assignments = sorted(
        event.get_run_assignments(),
        key=lambda row: (row["heat"], row["class"], row["number"]),
    )

    table_data = [display_grid_worker_headers] + [
        [str(row[h]).upper() for h in grid_worker_headers] for row in sorted_assignments
    ]
    col_widths = _compute_scaled_col_widths(
        data=table_data,
        font_name=FONT_NAME,
        font_size=FONT_SIZE,
        padding=CELL_PADDING,
        total_width=available_width,
    )

    grid_worker_table = Table(
        table_data,
        colWidths=col_widths,
        repeatRows=1,
    )
    name_idx = grid_worker_headers.index("name")

    grid_worker_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (name_idx, 1), (name_idx, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE),
            ]
        )
    )
    return grid_worker_table


def _compute_scaled_col_widths(data, font_name, font_size, padding, total_width):
    """Compute column widths scaled to fit the available page width to avoid overflow or truncation."""

    num_cols = len(data[0])
    max_widths = [0] * num_cols
    for row in data:
        for idx, cell in enumerate(row):
            text = str(cell)
            width = stringWidth(text, font_name, font_size)
            max_widths[idx] = max(max_widths[idx], width)
    raw_widths = [width + padding for width in max_widths]
    raw_total = sum(raw_widths)
    return [width * total_width / raw_total for width in raw_widths]


class NumberedCanvas(canvas.Canvas):
    """Canvas subclass that prints 'Page X of Y' in the footer."""

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
        self.setFont(FONT_NAME, FONT_SIZE)
        text = f"Page {self.getPageNumber()} of {total}"
        self.drawCentredString(self._pagesize[0] / 2, 0.5 * inch, text)
