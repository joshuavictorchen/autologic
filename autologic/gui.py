# -------------------------------------------------------------------------------------------------
# gui code sections
# -------------------------------------------------------------------------------------------------
# constants and defaults
# gui controller
# initialization
# window utilities
# tree helpers
# inline editors
# checkbox rendering
# dialog layout
# layout and panels
# input wiring
# tooltips
# config loading and saving
# generation workflow
# event persistence and config snapshots
# event view refresh
# validation helpers
# worker table rendering and sorting
# heat adjustments
# custom assignments
# assignment interactions
# data loading
# state updates
# run loop
# support classes and entrypoint
# -------------------------------------------------------------------------------------------------

import csv
import os
import pickle
import queue
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, END, LEFT, RIGHT, W, X, Y
import yaml

from autologic import utils
from autologic.algorithms import get_algorithms
from autologic.app import load_event, main
from autologic.config import Config, resolve_config_paths
from autologic.event import Event

# constants and defaults -------------------------------------------------------------------
# centralizes user interface labels, colors, and default values for consistent configuration
ASSIGNMENT_OPTIONS = ["instructor", "timing", "grid", "start", "captain", "special"]
ROLE_OPTIONS = ASSIGNMENT_OPTIONS + ["worker"]
SUMMARY_COLUMNS = [
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
PALETTE = {
    "background": "#EAEFF3",
    "panel": "#EFF1F3",
    "header": "#D4DEE7",
    "field": "#F2F4F7",
    "text": "#111111",
    "accent": "#3F627D",
}
DEFAULT_EVENT_NAME = "Autologic Event"
DEFAULT_NUMBER_OF_HEATS = 3
DEFAULT_NUMBER_OF_STATIONS = 5
DEFAULT_HEAT_SIZE_PARITY = 50
DEFAULT_NOVICE_SIZE_PARITY = 40
DEFAULT_NOVICE_DENOMINATOR = 4
DEFAULT_MAX_ITERATIONS = 8000
PARAMETER_TOOLTIPS = {
    "Event name": "Name of this event.",
    "Algorithm": None,
    "Heats": "Number of heats in this event.",
    "Stations": "Number of worker stations on course.",
    "Heat parity": "Larger values enforce tighter heat size balance.",
    "Novice parity": "Larger values enforce tighter novice balance across heats.",
    "Novice denominator": (
        "Min instructors required per heat = number of novices / novice_denominator."
    ),
    "Max iterations": "Maximum number of attempts to be made by the program.",
}


# gui controller ---------------------------------------------------------------------------
# encapsulates the tkinter application state, widgets, and event workflows so user interface logic stays central
class AutologicGUI:
    """GUI controller for configuring and visualizing Autologic events."""

    # initialization ---------------------------------------------------------------------------
    # establishes window state, defaults, and styles so startup is predictable
    def __init__(self):
        """Initialize GUI state, resources, and layout."""
        self.root = ttk.Window(themename="flatly")
        self.root.title("Autologic")
        self.root.geometry("1800x1200")
        self.root.minsize(1200, 800)

        # keep algorithms list clean so users only see real options
        self.algorithms = {k: v for k, v in get_algorithms().items() if k != "example"}
        self.current_event: Event | None = None
        self.config_dirty = False
        self.event_dirty = False
        self.is_applying_config = False
        self.member_name_lookup: dict[str, str] = {}
        self.worker_table_mapping: dict[str, object] = {}
        self.worker_sort_column: str | None = None
        self.worker_sort_descending = False
        self.assignment_use_state: dict[str, bool] = {}
        self.assignment_add_row_id: str | None = None
        self.is_generating = False
        self.generation_thread: threading.Thread | None = None
        self.generation_cancel_requested = threading.Event()
        self.generation_result_queue: queue.Queue[
            tuple[Event | None, Exception | None]
        ] = queue.Queue()
        self.assignment_editor: ttk.Combobox | None = None
        self.assignment_context_menu: tk.Menu | None = None
        self.parameter_tooltips: list["HoverTooltip"] = []

        is_frozen = getattr(sys, "frozen", False)
        # resolve base directories differently for bundled executables
        if is_frozen:
            self.application_directory = Path(sys.executable).resolve().parent
        else:
            self.application_directory = Path(__file__).resolve().parent
        if is_frozen:
            self.resource_root = Path(
                getattr(sys, "_MEIPASS", self.application_directory)
            )
        else:
            self.resource_root = Path(__file__).resolve().parents[1]

        icon_candidates = [
            self.resource_root / "docs" / "images" / "autologic-icon.ico",
            self.application_directory / "autologic-icon.ico",
        ]
        self.icon_path: Path | None = None
        for candidate in icon_candidates:
            if candidate.exists():
                self.icon_path = candidate
                break

        icon_photo_candidates = [
            self.resource_root / "docs" / "images" / "autologic-icon.png",
            self.application_directory / "autologic-icon.png",
        ]
        self.icon_photo_path: Path | None = None
        for candidate in icon_photo_candidates:
            if candidate.exists():
                self.icon_photo_path = candidate
                break
        self.icon_photo_image: tk.PhotoImage | None = None

        self.default_config_path = self.application_directory / "autologic.yaml"
        self.config_path = self.default_config_path

        default_algorithm = (
            "randomize"
            if "randomize" in self.algorithms
            else next(iter(self.algorithms))
        )
        self.event_name_variable = tk.StringVar(value=DEFAULT_EVENT_NAME)
        self.heats_variable = tk.StringVar(value=str(DEFAULT_NUMBER_OF_HEATS))
        self.stations_variable = tk.StringVar(value=str(DEFAULT_NUMBER_OF_STATIONS))
        self.heat_parity_variable = tk.StringVar(value=str(DEFAULT_HEAT_SIZE_PARITY))
        self.novice_parity_variable = tk.StringVar(
            value=str(DEFAULT_NOVICE_SIZE_PARITY)
        )
        self.novice_denominator_variable = tk.StringVar(
            value=str(DEFAULT_NOVICE_DENOMINATOR)
        )
        self.max_iterations_variable = tk.StringVar(value=str(DEFAULT_MAX_ITERATIONS))
        self.algorithm_variable = tk.StringVar(value=default_algorithm)
        self.tsv_path_variable = tk.StringVar()
        self.member_csv_path_variable = tk.StringVar()
        self.config_path_variable = tk.StringVar(value=str(self.config_path))
        self.validation_status_variable = tk.StringVar(value="Validation: --")
        self.status_variable = tk.StringVar(value="Ready")

        style = ttk.Style()
        palette = PALETTE
        # apply a consistent background to prevent mixed theme seams
        self.root.configure(background=palette["background"])
        # remove dotted focus outlines that distract in a dense control panel
        self.root.option_add("*TButton.takefocus", "0")
        style.configure("TFrame", background=palette["panel"])
        style.configure("TLabel", font=("Segoe UI", 10), background=palette["panel"])
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure(
            "TEntry",
            fieldbackground=palette["field"],
            foreground=palette["text"],
        )
        style.configure(
            "TCombobox",
            fieldbackground=palette["field"],
            foreground=palette["text"],
            selectforeground=palette["text"],
        )
        style.map(
            "TEntry",
            fieldbackground=[("readonly", palette["field"])],
            foreground=[("readonly", palette["text"])],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["field"])],
            foreground=[("readonly", palette["text"])],
        )
        style.configure("TLabelframe", background=palette["panel"])
        style.configure(
            "TLabelframe.Label",
            font=("Segoe UI", 10, "bold"),
            background=palette["panel"],
            foreground=style.colors.dark,
        )
        style.configure(
            "Treeview",
            rowheight=30,
            background=palette["panel"],
            fieldbackground=palette["panel"],
        )
        style.configure(
            "Treeview.Heading",
            background=palette["header"],
            foreground=style.colors.dark,
            font=("Segoe UI", 9, "bold"),
            borderwidth=1,
            relief="raised",
        )
        style.map("Treeview.Heading", background=[("active", palette["header"])])
        style.configure(
            "Summary.Header.TLabel",
            font=("Segoe UI", 9, "bold"),
            background=palette["header"],
            foreground=style.colors.dark,
        )
        style.configure(
            "Summary.Valid.TLabel",
            background=palette["panel"],
            foreground=style.colors.fg,
        )
        style.configure(
            "Summary.Invalid.TLabel",
            background=style.colors.danger,
            foreground=style.colors.selectfg,
        )
        style.configure(
            "Saved.TLabel",
            background=palette["panel"],
            foreground=style.colors.success,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Unsaved.TLabel",
            background=palette["panel"],
            foreground=style.colors.warning,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Validation.Ok.TLabel",
            background=palette["panel"],
            foreground=style.colors.success,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Validation.Invalid.TLabel",
            background=palette["panel"],
            foreground=style.colors.warning,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Validation.Empty.TLabel",
            background=palette["panel"],
            foreground=palette["text"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Inline.TCombobox",
            fieldbackground=palette["field"],
            foreground=palette["text"],
            selectforeground=palette["text"],
            padding=(4, 0, 4, 0),
        )
        style.configure(
            "Status.TLabel",
            background=palette["panel"],
            foreground=palette["text"],
            font=("Segoe UI", 9),
        )

        self.checkbox_unchecked_image = self._create_checkbox_image(checked=False)
        self.checkbox_checked_image = self._create_checkbox_image(checked=True)

        self._build_layout()
        self._register_variable_traces()

        legacy_config_path = self.resource_root / "gui" / "autologic.yaml"
        initial_config_path = self.default_config_path
        if not self.default_config_path.exists() and legacy_config_path.exists():
            # prefer the legacy path to preserve relative config references
            initial_config_path = legacy_config_path

        # ensure the default config exists so save operations are predictable
        if (
            initial_config_path == self.default_config_path
            and not self.default_config_path.exists()
        ):
            try:
                self.default_config_path.write_text("", encoding="utf-8")
            except OSError as exc:
                messagebox.showerror(
                    "Error", f"Failed to create default config file: {exc}"
                )

        self._load_config_from_path(initial_config_path)
        self._update_unsaved_indicator()
        self._apply_window_icon(self.root)

        # keep window close wired for clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # window utilities -------------------------------------------------------------------------
    # keeps window-level behavior like icons and dialog defaults consistent
    def _apply_window_icon(self, window: tk.Misc) -> None:
        """Apply the configured app icon to a window.

        Args:
            window: Window or toplevel to receive the icon.
        """
        # prioritize ico for taskbar/title bar fidelity and keep png as fallback
        if self.icon_path:
            try:
                window.iconbitmap(str(self.icon_path))
            except tk.TclError:
                pass
        if not self.icon_photo_path:
            return
        try:
            if not self.icon_photo_image:
                self.icon_photo_image = tk.PhotoImage(
                    master=self.root,
                    file=str(self.icon_photo_path),
                )
            window.iconphoto(True, self.icon_photo_image)
        except tk.TclError:
            return

    def _prepare_dialog(self, dialog: tk.Toplevel) -> None:
        """Apply shared dialog defaults for consistent modal styling.

        Args:
            dialog: Dialog window to configure.
        """
        # keep popups visually consistent and anchored to the main window
        dialog.title("")
        dialog.configure(background=PALETTE["panel"])
        dialog.transient(self.root)
        dialog.resizable(False, False)
        self._apply_window_icon(dialog)

    # tree helpers -----------------------------------------------------------------------------
    # centralizes treeview utilities to keep rendering logic tidy
    def _get_tree_column_name(self, tree: ttk.Treeview, column_id: str) -> str | None:
        """Map a Treeview column id to its logical column name.

        Args:
            tree: Treeview widget to query.
            column_id: Tk column identifier (ex: "#2").

        Returns:
            str | None: Column name or None when unknown.
        """
        if column_id == "#0":
            return None
        try:
            index = int(column_id[1:]) - 1
        except ValueError:
            return None
        columns = list(tree["columns"])
        if 0 <= index < len(columns):
            return columns[index]
        return None

    def _format_member_name_for_display(self, name: str) -> str:
        """Normalize member names to Last, First when possible.

        Args:
            name: Raw name string from the member CSV.

        Returns:
            str: Name formatted for display and sorting.
        """
        cleaned = str(name).strip()
        if not cleaned:
            return ""
        # prefer surname-first ordering for consistent sorting
        if "," in cleaned:
            return cleaned
        name_parts = cleaned.split()
        if len(name_parts) < 2:
            return cleaned
        last_name = name_parts[-1]
        first_name = " ".join(name_parts[:-1])
        return f"{last_name}, {first_name}"

    # inline editors ---------------------------------------------------------------------------
    # handles in-place dropdown editors so edits stay in context
    def _clear_assignment_editor(self) -> None:
        """Remove any active inline assignment editor."""
        if self.assignment_editor:
            self.assignment_editor.destroy()
            self.assignment_editor = None

    def _show_assignment_editor(
        self,
        tree: ttk.Treeview,
        item_id: str,
        column_id: str,
        options: list[str],
        on_commit,
    ) -> None:
        """Show an inline combobox editor for assignment columns.

        Args:
            tree: Treeview that owns the edited cell.
            item_id: Row identifier to edit.
            column_id: Column identifier to edit.
            options: Allowed values for the dropdown.
            on_commit: Callback invoked with the selected value.
        """
        self._clear_assignment_editor()
        # place the editor directly over the cell to avoid extra dialogs
        bbox = tree.bbox(item_id, column_id)
        if not bbox:
            return
        x, y, width, height = bbox
        column_name = self._get_tree_column_name(tree, column_id)
        if not column_name:
            return
        editor = ttk.Combobox(
            tree, values=options, state="readonly", style="Inline.TCombobox"
        )
        current_value = tree.set(item_id, column_name)
        editor.set(current_value or options[0])
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()
        self.assignment_editor = editor

        def finish(commit: bool) -> None:
            """Finalize the inline editor with optional commit."""
            # commit only after a selection or focus-out to avoid partial state
            if not self.assignment_editor:
                return
            value = editor.get().strip()
            editor.destroy()
            self.assignment_editor = None
            if commit and value:
                on_commit(value)

        editor.bind("<<ComboboxSelected>>", lambda _event: finish(True))
        editor.bind("<Return>", lambda _event: finish(True))
        editor.bind("<Escape>", lambda _event: finish(False))

        def handle_focus_out(_event) -> None:
            """Delay closing so the popdown can receive focus."""

            # wait until the dropdown closes so single clicks do not self-dismiss
            def popdown_visible() -> bool:
                """Return True while the combobox popdown is visible."""
                try:
                    popdown = editor.tk.call("ttk::combobox::PopdownWindow", editor)
                    return bool(int(editor.tk.call("winfo", "viewable", popdown)))
                except tk.TclError:
                    return False

            def maybe_finish() -> None:
                """Poll the popdown and finish after it closes."""
                # poll until the dropdown closes so focus changes do not cancel edits
                if not self.assignment_editor or not editor.winfo_exists():
                    return
                if popdown_visible():
                    editor.after(50, maybe_finish)
                    return
                finish(True)

            editor.after(1, maybe_finish)

        editor.bind("<FocusOut>", handle_focus_out)
        # open the dropdown immediately so a single click exposes options
        editor.after(0, lambda: editor.tk.call("ttk::combobox::Post", editor))

    # checkbox rendering -----------------------------------------------------------------------
    # draws custom checkbox images so tree rows show clear state
    def _create_checkbox_image(self, checked: bool) -> tk.PhotoImage:
        """Build a checkbox image for Treeview rows.

        Args:
            checked: Whether to render the checkbox in a checked state.

        Returns:
            tk.PhotoImage: Checkbox image.
        """
        # draw a custom checkbox so checked/unchecked states are obvious
        size = 20
        colors = ttk.Style().colors
        background = colors.bg
        border = colors.fg
        check_color = colors.success if checked else colors.fg

        image = tk.PhotoImage(width=size, height=size)
        image.put(background, to=(0, 0, size, size))

        border_start = 3
        border_end = size - 4
        for x in range(border_start, border_end + 1):
            image.put(border, (x, border_start))
            image.put(border, (x, border_end))
        for y in range(border_start, border_end + 1):
            image.put(border, (border_start, y))
            image.put(border, (border_end, y))

        if checked:
            for offset in range(4):
                image.put(check_color, (5 + offset, 11 + offset))
                image.put(check_color, (5 + offset, 12 + offset))
            for offset in range(7):
                image.put(check_color, (8 + offset, 14 - offset))
                image.put(check_color, (8 + offset, 15 - offset))

        return image

    # dialog layout ----------------------------------------------------------------------------
    # standardizes dialog sizing and centering to match the main window
    def _finalize_dialog_size(self, dialog: tk.Toplevel) -> None:
        """Set the dialog size to its requested size and center it.

        Args:
            dialog: Dialog window to size and position.
        """
        # center dialogs over the main window to avoid disorienting placement
        self.root.update_idletasks()
        dialog.update_idletasks()
        required_width = dialog.winfo_reqwidth()
        required_height = dialog.winfo_reqheight()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        x = root_x + max((root_width - required_width) // 2, 0)
        y = root_y + max((root_height - required_height) // 2, 0)
        dialog.minsize(required_width, required_height)
        dialog.geometry(f"{required_width}x{required_height}+{x}+{y}")

    # layout and panels ------------------------------------------------------------------------
    # constructs the main window layout so panel changes stay localized
    def _build_layout(self) -> None:
        """Build the top-level layout containers."""
        container = tk.Frame(self.root, background=PALETTE["background"])
        container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # split the window so controls stay compact while data expands
        left_column = tk.Frame(container, background=PALETTE["background"])
        right_column = tk.Frame(container, background=PALETTE["background"])
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_column.grid(row=0, column=1, sticky="nsew")

        # allow the data column to absorb extra space when resizing
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        # keep the left column stable so control panels remain readable
        left_column.columnconfigure(0, weight=1)
        left_column.rowconfigure(0, weight=0)
        left_column.rowconfigure(1, weight=0)
        left_column.rowconfigure(2, weight=1)

        # let the data panel grow to fill the remaining space
        right_column.columnconfigure(0, weight=1)
        right_column.rowconfigure(0, weight=1)

        self.control_panel = ttk.Labelframe(
            left_column, text="Control Panel", padding=10
        )
        self.control_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        # build each panel in its own function to keep layout readable
        self._build_control_panel(self.control_panel)

        self.parameters_panel = ttk.Labelframe(
            left_column, text="Parameters", padding=10
        )
        self.parameters_panel.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self._build_parameters_panel(self.parameters_panel)

        self.assignments_panel = ttk.Labelframe(
            left_column, text="Custom Assignments", padding=10
        )
        self.assignments_panel.grid(row=2, column=0, sticky="nsew")
        self._build_assignments_panel(self.assignments_panel)

        self.data_panel = ttk.Labelframe(right_column, text="Event Data", padding=10)
        self.data_panel.grid(row=0, column=0, sticky="nsew")
        self._build_data_panel(self.data_panel)

    def _build_control_panel(self, parent: ttk.Labelframe) -> None:
        """Build the control panel for config/event actions.

        Args:
            parent: Container to populate with control widgets.
        """
        button_row = ttk.Frame(parent)
        button_row.pack(fill=X, pady=(0, 8))

        # keep primary actions grouped for faster scanning
        ttk.Button(
            button_row, text="Load Config", command=self._load_config_prompt
        ).pack(side=LEFT, padx=4)
        ttk.Button(button_row, text="Save Config", command=self._save_config).pack(
            side=LEFT, padx=4
        )
        ttk.Button(button_row, text="Load Event", command=self._load_event_prompt).pack(
            side=LEFT, padx=4
        )

        self.generate_button = ttk.Button(
            button_row,
            text="Generate Event",
            bootstyle="primary",
            command=self._on_generate_button,
        )
        self.generate_button.pack(side=LEFT, padx=4)
        self.save_event_button = ttk.Button(
            button_row,
            text="Save Event",
            bootstyle="success",
            command=self._save_event,
        )
        self.save_event_button.pack(side=LEFT, padx=4)
        self.save_event_button.configure(state="disabled")

        # surface the active config location without allowing edits
        config_row = ttk.Frame(parent)
        config_row.pack(fill=X, pady=(0, 6))
        ttk.Label(config_row, text="Config file").pack(side=LEFT, padx=(0, 6))
        ttk.Entry(
            config_row,
            textvariable=self.config_path_variable,
            state="readonly",
            width=48,
        ).pack(side=LEFT, fill=X, expand=True)

        # keep status and dirty flags aligned for quick visibility
        status_row = ttk.Frame(parent)
        status_row.pack(fill=X)
        status_row.columnconfigure(0, weight=1)
        self.unsaved_label = ttk.Label(status_row, text="", anchor=W)
        self.unsaved_label.grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(
            status_row,
            textvariable=self.status_variable,
            anchor="e",
            style="Status.TLabel",
        )
        self.status_label.grid(row=0, column=1, sticky="e", padx=(10, 0))

    def _build_parameters_panel(self, parent: ttk.Labelframe) -> None:
        """Build the parameter entry panel for config inputs.

        Args:
            parent: Container to populate with parameter inputs.
        """
        form = ttk.Frame(parent)
        form.pack(fill=X)

        # keep core parameters near the top for fast edits
        self._add_labeled_entry(form, "Event name", self.event_name_variable, 0, 0)

        ttk.Label(form, text="Algorithm").grid(row=0, column=2, sticky=W, padx=4)
        ttk.Combobox(
            form,
            textvariable=self.algorithm_variable,
            values=list(self.algorithms.keys()),
            state="readonly",
            width=18,
        ).grid(row=0, column=3, sticky=W, padx=4)

        self._add_labeled_entry(form, "Heats", self.heats_variable, 1, 0, width=8)
        self._add_labeled_entry(form, "Stations", self.stations_variable, 1, 2, width=8)
        self._add_labeled_entry(
            form, "Heat parity", self.heat_parity_variable, 2, 0, width=8
        )
        self._add_labeled_entry(
            form, "Novice parity", self.novice_parity_variable, 2, 2, width=8
        )
        self._add_labeled_entry(
            form, "Novice denominator", self.novice_denominator_variable, 3, 0, width=12
        )
        self._add_labeled_entry(
            form, "Max iterations", self.max_iterations_variable, 3, 2, width=12
        )

        # separate file selectors so they align on the right edge
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=X, pady=(10, 0))
        self._add_file_picker(
            file_frame,
            "AXWare TSV",
            self.tsv_path_variable,
            0,
            lambda: self._browse_file(
                self.tsv_path_variable,
                filetypes=[("TSV", "*.tsv *.txt"), ("All files", "*.*")],
            ),
        )
        self._add_file_picker(
            file_frame,
            "Member CSV",
            self.member_csv_path_variable,
            1,
            lambda: self._browse_file(
                self.member_csv_path_variable,
                filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            ),
        )

    def _build_assignments_panel(self, parent: ttk.Labelframe) -> None:
        """Build the custom assignments panel.

        Args:
            parent: Container to populate with the assignments table.
        """
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True)

        # use a Treeview to mimic spreadsheet-style editing
        self.assignments_tree = ttk.Treeview(
            tree_frame,
            columns=("member_id", "name", "assignment"),
            show="tree headings",
            height=8,
        )
        self.assignments_tree.heading("#0", text="Use", anchor="center")
        self.assignments_tree.heading("member_id", text="Member ID", anchor=W)
        self.assignments_tree.heading("name", text="Name", anchor=W)
        self.assignments_tree.heading(
            "assignment", text="Assignment ▾", anchor="center"
        )
        self.assignments_tree.column("#0", width=60, anchor="center", stretch=False)
        self.assignments_tree.column("member_id", width=120, anchor=W)
        self.assignments_tree.column("name", width=180, anchor=W)
        self.assignments_tree.column("assignment", width=140, anchor="center")
        self.assignments_tree.tag_configure("disabled", foreground="#888888")
        self.assignments_tree.bind("<Button-1>", self._on_assignment_click)
        self.assignments_tree.bind("<Button-3>", self._on_assignment_right_click)
        self.assignments_tree.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side=RIGHT, fill=Y)
        self.assignments_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.assignments_tree.yview)

        self.assignment_context_menu = tk.Menu(self.root, tearoff=0)
        self.assignment_context_menu.add_command(
            label="Delete", command=self._remove_assignment_row
        )

    def _build_data_panel(self, parent: ttk.Labelframe) -> None:
        """Build the event data panel with tables and actions.

        Args:
            parent: Container to populate with event data widgets.
        """
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=0)
        parent.rowconfigure(2, weight=2)

        # heat table and controls live at the top for quick adjustments
        heat_frame = ttk.Labelframe(parent, text="Heats & Classes", padding=8)
        heat_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        heat_frame.columnconfigure(0, weight=1)
        heat_frame.rowconfigure(1, weight=1)

        heat_button_row = ttk.Frame(heat_frame)
        heat_button_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(
            heat_button_row, text="Move Class", command=self._move_class_dialog
        ).pack(side=LEFT, padx=4)
        ttk.Button(
            heat_button_row,
            text="Rotate Run/Work",
            command=self._rotate_run_work,
        ).pack(side=LEFT, padx=4)

        # keep heat summary compact to leave room for role and worker tables
        self.heat_tree = ttk.Treeview(
            heat_frame,
            columns=("heat", "running", "working", "classes"),
            show="headings",
            height=2,
        )
        self.heat_tree.heading("heat", text="Group")
        self.heat_tree.heading("running", text="Running")
        self.heat_tree.heading("working", text="Working")
        self.heat_tree.heading("classes", text="Classes")
        self.heat_tree.column("heat", width=40, anchor="center")
        self.heat_tree.column("running", width=50, anchor="center")
        self.heat_tree.column("working", width=50, anchor="center")
        self.heat_tree.column("classes", width=450, anchor=W)
        self.heat_tree.grid(row=1, column=0, sticky="nsew")
        heat_scrollbar = ttk.Scrollbar(heat_frame, orient="vertical")
        heat_scrollbar.grid(row=1, column=1, sticky="ns")
        self.heat_tree.configure(yscrollcommand=heat_scrollbar.set)
        heat_scrollbar.configure(command=self.heat_tree.yview)

        # role summary sits between heats and workers for validation context
        summary_frame = ttk.Labelframe(parent, text="Role Summary", padding=8)
        summary_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(1, weight=1)

        self.validation_status_label = ttk.Label(
            summary_frame,
            textvariable=self.validation_status_variable,
            anchor=W,
            style="Validation.Empty.TLabel",
        )
        self.validation_status_label.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.summary_table_container = ttk.Frame(summary_frame)
        self.summary_table_container.grid(row=1, column=0, sticky="nsew")

        # worker table is last so it can expand vertically as needed
        worker_frame = ttk.Labelframe(parent, text="Worker Assignments", padding=8)
        worker_frame.grid(row=2, column=0, sticky="nsew")
        worker_frame.columnconfigure(0, weight=1)
        worker_frame.rowconfigure(0, weight=1)

        self.worker_tree = ttk.Treeview(
            worker_frame,
            columns=(
                "working",
                "name",
                "assignment",
                "class",
                "number",
            ),
            show="headings",
            height=10,
        )
        self.worker_column_labels = {
            "working": "Working",
            "name": "Name",
            "assignment": "Assignment ▾",
            "class": "Class",
            "number": "Number",
        }
        self._update_worker_sort_headings()

        self.worker_tree.column("working", width=70, anchor="center")
        self.worker_tree.column("name", width=180, anchor=W)
        self.worker_tree.column("assignment", width=120, anchor="center")
        self.worker_tree.column("class", width=60, anchor="center")
        self.worker_tree.column("number", width=60, anchor="center")
        self.worker_tree.bind("<Button-1>", self._on_worker_assignment_click)

        self.worker_tree.grid(row=0, column=0, sticky="nsew")
        worker_scrollbar = ttk.Scrollbar(worker_frame, orient="vertical")
        worker_scrollbar.grid(row=0, column=1, sticky="ns")
        self.worker_tree.configure(yscrollcommand=worker_scrollbar.set)
        worker_scrollbar.configure(command=self.worker_tree.yview)

    # input wiring -----------------------------------------------------------------------------
    # wires up variable traces so input changes trigger consistent updates
    def _register_variable_traces(self) -> None:
        """Attach variable traces to mark config changes and reload data."""
        config_variables = [
            self.event_name_variable,
            self.heats_variable,
            self.stations_variable,
            self.heat_parity_variable,
            self.novice_parity_variable,
            self.novice_denominator_variable,
            self.max_iterations_variable,
            self.algorithm_variable,
            self.tsv_path_variable,
            self.member_csv_path_variable,
        ]
        # consolidate config dirty tracking for any input change
        for variable in config_variables:
            variable.trace_add("write", self._on_config_variable_change)

        # TSV and CSV changes need special handling beyond dirty state
        self.tsv_path_variable.trace_add("write", self._on_tsv_change)
        self.member_csv_path_variable.trace_add("write", self._on_member_csv_change)

    def _on_close(self) -> None:
        """Close the application window."""
        self.root.destroy()

    # tooltips -----------------------------------------------------------------------------
    # attaches hover tooltips to parameter inputs without interrupting edits
    def _attach_tooltip(self, widget: tk.Widget, label: str) -> None:
        """Attach a tooltip to a widget if a definition exists.

        Args:
            widget: Widget that should display the tooltip.
            label: Parameter label used to look up tooltip text.
        """
        tooltip_text = PARAMETER_TOOLTIPS.get(label)
        if not tooltip_text:
            return
        self.parameter_tooltips.append(
            HoverTooltip(
                root=self.root,
                widget=widget,
                text=tooltip_text,
                background=PALETTE["header"],
                foreground=PALETTE["text"],
                font=("Segoe UI", 10),
            )
        )

    def _add_labeled_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
        width: int = 20,
    ) -> None:
        """Add a label+entry pair to a grid row.

        Args:
            parent: Container for the widgets.
            label: Label text.
            variable: StringVar bound to the entry.
            row: Grid row.
            column: Grid column for the label.
            width: Entry width in characters.
        """
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky=W, padx=4)
        entry_widget = ttk.Entry(parent, textvariable=variable, width=width)
        entry_widget.grid(row=row, column=column + 1, sticky=W, padx=4)
        self._attach_tooltip(entry_widget, label)

    def _add_file_picker(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        browse_command,
    ) -> None:
        """Add a file picker row with label, entry, and browse button.

        Args:
            parent: Container for the widgets.
            label: Label text.
            variable: StringVar bound to the entry.
            row: Grid row to place the picker.
            browse_command: Callback for the Browse button.
        """
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=W, padx=4, pady=2)
        ttk.Entry(parent, textvariable=variable, width=48).grid(
            row=row, column=1, sticky="ew", padx=4, pady=2
        )
        ttk.Button(parent, text="Browse", command=browse_command).grid(
            row=row, column=2, sticky="e", padx=4, pady=2
        )

    def _browse_file(
        self,
        target_variable: tk.StringVar,
        filetypes: list[tuple[str, str]] | None = None,
    ) -> None:
        """Open a file dialog and store the chosen path.

        Args:
            target_variable: Variable to receive the selected path.
            filetypes: File type filters for the dialog.
        """
        # default to the app directory so repeated selections are faster
        options = {"initialdir": str(self.application_directory)}
        if filetypes:
            options["filetypes"] = filetypes
        file_path = filedialog.askopenfilename(**options)
        if file_path:
            target_variable.set(file_path)

    # config loading and saving ----------------------------------------------------------------
    # loads config values into the user interface so config and user interface stay in sync
    def _load_config_prompt(self) -> None:
        """Prompt the user to choose a config file to load."""
        path = filedialog.askopenfilename(
            initialdir=str(self.application_directory),
            filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not path:
            return
        self._load_config_from_path(Path(path))

    def _load_config_from_path(self, config_path: Path) -> None:
        """Load and apply configuration values from a YAML file.

        Args:
            config_path: Path to the config file to load.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config_data = yaml.safe_load(file) or {}
            # resolve file paths relative to the config file location
            config_data = resolve_config_paths(config_data, config_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load config: {exc}")
            return

        self.config_path = config_path
        self.config_path_variable.set(str(config_path))
        self._apply_config_data(config_data)
        self.config_dirty = False
        self._set_status("Loaded config")
        self._update_unsaved_indicator()

    def _apply_config_data(self, config_data: dict) -> None:
        """Apply configuration values to the GUI state.

        Args:
            config_data: Configuration values to apply.
        """
        self.is_applying_config = True
        try:
            # suppress dirty tracking while values are programmatically applied
            if "name" in config_data:
                self.event_name_variable.set(str(config_data["name"]))
            if "axware_export_tsv" in config_data:
                self.tsv_path_variable.set(str(config_data["axware_export_tsv"]))
            if "member_attributes_csv" in config_data:
                self.member_csv_path_variable.set(
                    str(config_data["member_attributes_csv"])
                )
            if "number_of_heats" in config_data:
                self.heats_variable.set(str(config_data["number_of_heats"]))
            if "number_of_stations" in config_data:
                self.stations_variable.set(str(config_data["number_of_stations"]))
            if "heat_size_parity" in config_data:
                self.heat_parity_variable.set(str(config_data["heat_size_parity"]))
            if "novice_size_parity" in config_data:
                self.novice_parity_variable.set(str(config_data["novice_size_parity"]))
            if "novice_denominator" in config_data:
                self.novice_denominator_variable.set(
                    str(config_data["novice_denominator"])
                )
            if "max_iterations" in config_data:
                self.max_iterations_variable.set(str(config_data["max_iterations"]))
            if (
                "algorithm" in config_data
                and config_data["algorithm"] in self.algorithms
            ):
                self.algorithm_variable.set(str(config_data["algorithm"]))

            # rebuild the assignments table so it matches config order and state
            for item in self.assignments_tree.get_children():
                self.assignments_tree.delete(item)
            self.assignment_use_state.clear()

            custom_assignments = config_data.get("custom_assignments", {}) or {}
            for member_id, assignment in custom_assignments.items():
                self._insert_assignment_row(
                    True,
                    str(member_id),
                    self.member_name_lookup.get(str(member_id), ""),
                    str(assignment),
                )

            self._refresh_assignment_names()
            self._ensure_add_assignment_row()
        finally:
            self.is_applying_config = False

        # update dependent data after config values are set
        self._load_member_names()

    def _save_config(self) -> bool:
        """Persist the current GUI configuration to the active YAML file.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        try:
            config_data = self._build_config_payload()
        except ValueError as exc:
            messagebox.showerror("Error", f"Invalid configuration: {exc}")
            return False

        try:
            with open(self.config_path, "w", encoding="utf-8") as file:
                yaml.safe_dump(config_data, file, sort_keys=False)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to save config: {exc}")
            return False

        self.config_dirty = False
        self._set_status("Saved config")
        self._update_unsaved_indicator()
        return True

    def _build_config_payload(self) -> dict:
        """Build a config dictionary from current widget values.

        Returns:
            dict: Configuration payload ready for YAML serialization.
        """
        return {
            "name": self.event_name_variable.get().strip(),
            "axware_export_tsv": self.tsv_path_variable.get().strip(),
            "member_attributes_csv": self.member_csv_path_variable.get().strip(),
            "number_of_heats": self.heats_variable.get().strip(),
            "number_of_stations": self.stations_variable.get().strip(),
            "custom_assignments": self._collect_assignments(),
            "heat_size_parity": self.heat_parity_variable.get().strip(),
            "novice_size_parity": self.novice_parity_variable.get().strip(),
            "novice_denominator": self.novice_denominator_variable.get().strip(),
            "max_iterations": self.max_iterations_variable.get().strip(),
            "algorithm": self.algorithm_variable.get().strip(),
        }

    def _build_config_snapshot(self) -> dict:
        """Build a config snapshot for event persistence.

        Returns:
            dict: Configuration snapshot with resolved data paths.
        """
        config_data = self._build_config_payload()
        # store absolute data paths so pickle reloads do not depend on the config file
        return resolve_config_paths(config_data, self.config_path)

    # generation workflow ---------------------------------------------------------------------
    # runs event generation in a worker thread and consumes results safely
    def _on_generate_button(self) -> None:
        """Handle Generate Event/Cancel button presses."""
        if self.is_generating:
            # signal cancellation without blocking the UI thread
            self.generation_cancel_requested.set()
            self._set_status("Canceling generation...")
            return
        self._start_generation()

    def _start_generation(self) -> None:
        """Start event generation in a background thread."""
        config_data = self._build_config_payload()
        algorithm = config_data.get("algorithm", self.algorithm_variable.get())
        resolved_config_data = resolve_config_paths(config_data, self.config_path)
        resolved_config_data.pop("algorithm", None)

        try:
            # validate inputs before spinning up the worker thread
            config = Config(**resolved_config_data)
            config.validate_paths()
        except Exception as exc:
            messagebox.showerror("Error", f"Invalid configuration: {exc}")
            return

        self._set_status("Generating event...")
        self._set_generation_state(True)
        self.generation_cancel_requested.clear()
        # clear stale results to avoid handling a previous run
        while not self.generation_result_queue.empty():
            try:
                self.generation_result_queue.get_nowait()
            except queue.Empty:
                break

        # run generation in a thread to keep the GUI responsive
        config_payload = config.model_dump()
        self.generation_thread = threading.Thread(
            target=self._run_generation_thread,
            args=(config_payload, algorithm),
            daemon=True,
        )
        self.generation_thread.start()
        self.root.after(100, self._check_generation_queue)

    def _run_generation_thread(self, config_payload: dict, algorithm: str) -> None:
        """Generate the event on a worker thread and queue the result.

        Args:
            config_payload: Validated config payload.
            algorithm: Algorithm name to execute.
        """
        event: Event | None = None
        error: Exception | None = None
        try:
            event = load_event(**config_payload)
            main(
                algorithm=algorithm,
                event=event,
                observer=self._generation_observer,
                export=False,
            )
        except GenerationCancelled as exc:
            error = exc
        except SystemExit as exc:
            error = exc
        except Exception as exc:
            error = exc
        self.generation_result_queue.put((event, error))

    def _generation_observer(self, event_type: str, payload: dict) -> None:
        """Abort generation when a cancel request is detected.

        Args:
            event_type: Event type emitted by the algorithm.
            payload: Metadata from the algorithm.
        """
        if self.generation_cancel_requested.is_set():
            raise GenerationCancelled("Generation cancelled")

    def _check_generation_queue(self) -> None:
        """Poll the generation thread result queue."""
        if not self.is_generating:
            return
        try:
            event, error = self.generation_result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._check_generation_queue)
            return
        self._handle_generation_result(event, error)

    def _handle_generation_result(
        self, event: Event | None, error: Exception | None
    ) -> None:
        """Apply generation results to the GUI.

        Args:
            event: Generated event or None on failure.
            error: Exception raised during generation, if any.
        """
        self._set_generation_state(False)
        if isinstance(error, GenerationCancelled):
            self._set_status("Generation cancelled")
            self._update_unsaved_indicator()
            return
        if isinstance(error, SystemExit):
            messagebox.showerror("Error", "Generation failed; see log for details.")
            self._set_status("Generation failed")
            return
        if error:
            messagebox.showerror("Error", f"Generation failed: {error}")
            self._set_status("Generation failed")
            return
        if not event:
            self._set_status("Generation failed")
            return

        self.current_event = event
        self.event_dirty = True
        self._refresh_event_views()
        self._set_status("Generation completed")
        self._update_unsaved_indicator()

    def _set_generation_state(self, is_generating: bool) -> None:
        """Update UI state for an active generation run.

        Args:
            is_generating: Whether generation is in progress.
        """
        self.is_generating = is_generating
        if is_generating:
            self.generate_button.configure(text="Cancel", bootstyle="danger")
        else:
            self.generate_button.configure(text="Generate Event", bootstyle="primary")
        self._update_save_event_state()

    # event persistence and config snapshots --------------------------------------------------
    # loads and saves event artifacts alongside the active config and embeds config snapshots
    def _get_event_config_snapshot(self, event: Event | None) -> dict | None:
        """Return the config snapshot from an event when available.

        Args:
            event: Event instance to inspect.

        Returns:
            dict | None: Stored config snapshot when present.
        """
        if not event:
            return None
        config_snapshot = getattr(event, "config_snapshot", None)
        if isinstance(config_snapshot, dict):
            return config_snapshot
        return None

    def _set_event_config_snapshot(self) -> None:
        """Attach the current config snapshot to the active event."""
        if not self.current_event:
            return
        config_snapshot = self._build_config_snapshot()
        # store config alongside the event so reloads can restore GUI inputs
        self.current_event.config_snapshot = config_snapshot

    def _save_event(self) -> None:
        """Save CSV/PDF/PKL outputs for the current event."""
        if not self._ensure_event_loaded():
            return

        raw_name = self.event_name_variable.get().strip()
        if not raw_name:
            messagebox.showwarning("Missing event name", "Event name is required")
            return
        event_name = raw_name
        # save outputs next to the active config to keep event assets together
        if self.config_path:
            output_dir = self.config_path.parent
        else:
            output_dir = self.application_directory

        output_paths = [
            output_dir / f"{event_name}.csv",
            output_dir / f"{event_name}.pdf",
            output_dir / f"{event_name}.pkl",
        ]
        existing_files = [path.name for path in output_paths if path.exists()]

        if existing_files:
            overwrite = messagebox.askyesno(
                "Overwrite files?",
                "The following files will be overwritten:\n\n"
                + "\n".join(existing_files),
            )
            if not overwrite:
                return

        # keep event name in sync with the last saved output name
        self.current_event.name = event_name
        self.event_name_variable.set(event_name)

        if not self._save_config():
            return
        self._set_event_config_snapshot()

        # change into the output directory for the export helpers
        previous_dir = Path.cwd()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            os.chdir(output_dir)
            self.current_event.to_csv()
            self.current_event.to_pdf()
            self.current_event.to_pickle()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save event: {exc}")
            return
        finally:
            os.chdir(previous_dir)

        self.event_dirty = False
        self._set_status("Saved event")
        self._update_unsaved_indicator()

    def _load_event_prompt(self) -> None:
        """Prompt the user to load a saved event pickle."""
        path = filedialog.askopenfilename(
            initialdir=str(self.application_directory),
            filetypes=[("Pickle", "*.pkl"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            # use the custom unpickler so legacy module paths still resolve
            with open(path, "rb") as file:
                self.current_event = EventUnpickler(file).load()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load event: {exc}")
            return

        config_snapshot = self._get_event_config_snapshot(self.current_event)
        if config_snapshot:
            self._apply_config_data(config_snapshot)
            self.config_dirty = False
        else:
            self.config_dirty = True

        self.is_applying_config = True
        try:
            self.event_name_variable.set(str(self.current_event.name))
            self.heats_variable.set(str(self.current_event.number_of_heats))
            self.stations_variable.set(str(self.current_event.number_of_stations))
            self.heat_parity_variable.set(str(self.current_event.heat_size_parity))
            self.novice_parity_variable.set(str(self.current_event.novice_size_parity))
            self.novice_denominator_variable.set(
                str(self.current_event.novice_denominator)
            )
            self.max_iterations_variable.set(str(self.current_event.max_iterations))
        finally:
            self.is_applying_config = False
        self.event_dirty = False
        self._refresh_event_views()
        self._set_status("Loaded event")
        self._update_unsaved_indicator()

    # event view refresh ----------------------------------------------------------------------
    # refreshes event-dependent tables so views mirror the active event
    def _refresh_event_views(self) -> None:
        """Refresh all event-dependent tables and controls."""
        self._clear_assignment_editor()
        self._refresh_heat_table()
        self._refresh_summary_table()
        self._refresh_worker_table()
        self._update_save_event_state()

    def _refresh_heat_table(self) -> None:
        """Render the heats/classes table."""
        self.heat_tree.delete(*self.heat_tree.get_children())
        if not self.current_event:
            return

        for heat in self.current_event.heats:
            classes = [category.name for category in heat.categories]
            classes.sort(key=str.lower)
            self.heat_tree.insert(
                "",
                END,
                values=(
                    str(heat.number),
                    str(heat.running),
                    str(heat.working),
                    ", ".join(classes),
                ),
            )

    def _refresh_summary_table(self) -> None:
        """Render the role summary table and validation status."""
        for child in self.summary_table_container.winfo_children():
            child.destroy()

        if not self.current_event:
            ttk.Label(
                self.summary_table_container,
                text="No event loaded",
                anchor=W,
            ).grid(row=0, column=0, sticky=W)
            self.validation_status_variable.set("Validation: --")
            self.validation_status_label.configure(style="Validation.Empty.TLabel")
            return

        # run validation once so we can highlight invalid cells
        validation_state = self._evaluate_event_validity()
        event_is_valid = validation_state["event_is_valid"]
        invalid_cells = validation_state["invalid_cells"]
        if event_is_valid:
            self.validation_status_variable.set("Validation: OK")
            self.validation_status_label.configure(style="Validation.Ok.TLabel")
        else:
            self.validation_status_variable.set("Validation: INVALID")
            self.validation_status_label.configure(style="Validation.Invalid.TLabel")

        for column_index, column_name in enumerate(SUMMARY_COLUMNS):
            header = ttk.Label(
                self.summary_table_container,
                text=column_name,
                style="Summary.Header.TLabel",
                anchor="center",
                padding=(4, 2),
            )
            header.grid(row=0, column=column_index, sticky="nsew", padx=1, pady=1)
            self.summary_table_container.grid_columnconfigure(column_index, weight=1)

        # populate rows per heat to align with PDF output ordering
        for heat_index, heat in enumerate(self.current_event.heats, start=1):
            counts = self._count_assignments(heat)
            novices = len(heat.get_participants_by_attribute("novice"))
            row_values = [
                str(heat_index),
                str(counts["instructor"]),
                str(counts["timing"]),
                str(counts["grid"]),
                str(counts["start"]),
                str(counts["captain"]),
                str(counts["worker"]),
                str(counts["special"]),
                f"{str(len(heat.participants))} ({novices} Novices)",
            ]

            for column_index, column_name in enumerate(SUMMARY_COLUMNS):
                is_invalid = False
                if column_name in invalid_cells.get(heat.number, set()):
                    is_invalid = True

                style_name = (
                    "Summary.Invalid.TLabel" if is_invalid else "Summary.Valid.TLabel"
                )
                cell = ttk.Label(
                    self.summary_table_container,
                    text=row_values[column_index],
                    style=style_name,
                    anchor="center",
                    padding=(4, 2),
                )
                cell.grid(
                    row=heat_index,
                    column=column_index,
                    sticky="nsew",
                    padx=1,
                    pady=1,
                )

    # validation helpers ----------------------------------------------------------------------
    # computes role counts and validity to drive summary highlighting
    def _evaluate_event_validity(self) -> dict:
        """Evaluate event validity and capture which summary cells are invalid.

        Returns:
            dict: Validation results and invalid cell locations.
        """
        invalid_cells: dict[int, set[str]] = {}
        event_is_valid = True

        for heat in self.current_event.heats:
            invalid_columns: set[str] = set()
            counts = self._count_assignments(heat)

            role_minima = utils.roles_and_minima(
                number_of_stations=self.current_event.number_of_stations,
                number_of_novices=len(
                    heat.compliment.get_participants_by_attribute("novice")
                ),
                novice_denominator=self.current_event.novice_denominator,
            )

            for role, minimum in role_minima.items():
                count = counts.get(role, 0)
                if role == "instructor":
                    # instructors can exceed minima but cannot drop below it
                    if count < minimum:
                        invalid_columns.add(role.capitalize())
                        event_is_valid = False
                else:
                    if count != minimum:
                        invalid_columns.add(role.capitalize())
                        event_is_valid = False

            heat_size = len(heat.participants)
            novice_count = len(heat.get_participants_by_attribute("novice"))
            valid_size = (
                abs(self.current_event.mean_heat_size - heat_size)
                <= self.current_event.max_heat_size_delta
            )
            valid_novice_count = (
                abs(self.current_event.mean_heat_novice_count - novice_count)
                <= self.current_event.max_heat_novice_delta
            )
            if not valid_size or not valid_novice_count:
                invalid_columns.add("Total")
                event_is_valid = False

            invalid_cells[heat.number] = invalid_columns

        return {"event_is_valid": event_is_valid, "invalid_cells": invalid_cells}

    def _count_assignments(self, heat) -> dict[str, int]:
        """Count role assignments for a heat.

        Args:
            heat: Heat to summarize.

        Returns:
            dict[str, int]: Assignment counts for the heat.
        """
        counts = {
            "instructor": 0,
            "timing": 0,
            "grid": 0,
            "start": 0,
            "captain": 0,
            "worker": 0,
            "special": 0,
        }
        for participant in heat.participants:
            assignment = participant.assignment or ""
            if assignment in counts:
                counts[assignment] += 1
        return counts

    def _validate_current_event(self) -> None:
        """Validate the current event and update status."""
        if not self.current_event:
            return
        try:
            is_valid = self.current_event.validate()
        except Exception as exc:
            messagebox.showerror("Error", f"Validation error: {exc}")
            return
        self._set_status("Validation passed" if is_valid else "Validation failed")

    # worker table rendering and sorting ------------------------------------------------------
    # keeps worker table rows and sort state in sync with the active event
    def _refresh_worker_table(self) -> None:
        """Render the worker assignments table."""
        self.worker_tree.delete(*self.worker_tree.get_children())
        self.worker_table_mapping.clear()
        if not self.current_event:
            return

        rows = []
        for heat in self.current_event.heats:
            for participant in heat.participants:
                # store participant objects for later inline edits
                rows.append(
                    (
                        heat.working,
                        participant.name,
                        participant.assignment or "",
                        participant.axware_category,
                        participant.number,
                        participant,
                    )
                )

        if self.worker_sort_column is None:
            self.worker_sort_column = "working"
            self.worker_sort_descending = False

        # sort rows based on the current UI sort state
        column_index = {
            "working": 0,
            "name": 1,
            "assignment": 2,
            "class": 3,
            "number": 4,
        }.get(self.worker_sort_column, 0)

        rows.sort(
            key=lambda row: self._coerce_sort_value(
                self.worker_sort_column, row[column_index]
            ),
            reverse=self.worker_sort_descending,
        )

        for row in rows:
            item_id = self.worker_tree.insert(
                "",
                END,
                values=(row[0], row[1], row[2], row[3], row[4]),
            )
            self.worker_table_mapping[item_id] = row[5]

        self._update_worker_sort_headings()

    def _sort_worker_table(self, column_name: str) -> None:
        """Sort the worker table by a selected column.

        Args:
            column_name: Column key to sort by.
        """
        if not self.current_event:
            return

        if self.worker_sort_column == column_name:
            self.worker_sort_descending = not self.worker_sort_descending
        else:
            self.worker_sort_column = column_name
            self.worker_sort_descending = False
        rows = []
        for item_id in self.worker_tree.get_children():
            value = self.worker_tree.set(item_id, column_name)
            rows.append((self._coerce_sort_value(column_name, value), item_id))

        # keep ordering stable while toggling sort direction
        rows.sort(reverse=self.worker_sort_descending)

        for index, (_, item_id) in enumerate(rows):
            self.worker_tree.move(item_id, "", index)

        self._update_worker_sort_headings()

    def _update_worker_sort_headings(self) -> None:
        """Update worker table headers to show sort direction."""
        # annotate only the active sort column to reduce visual noise
        for column_id, label in self.worker_column_labels.items():
            heading_label = label
            if column_id == self.worker_sort_column:
                heading_label = (
                    f"{label} ↓" if self.worker_sort_descending else f"{label} ↑"
                )
            heading_anchor = W if column_id == "name" else "center"
            self.worker_tree.heading(
                column_id,
                text=heading_label,
                anchor=heading_anchor,
                command=lambda c=column_id: self._sort_worker_table(c),
            )

    def _coerce_sort_value(self, column_name: str, value: str):
        """Coerce worker table values into sortable types.

        Args:
            column_name: Column key being sorted.
            value: Raw cell value from the Treeview.

        Returns:
            object: Sortable value.
        """
        numeric_columns = {"working", "number"}
        if column_name in numeric_columns:
            try:
                return int(value)
            except ValueError:
                return 0
        return str(value).lower()

    # heat adjustments ------------------------------------------------------------------------
    # updates heat and class assignments so manual edits reflect in event data
    def _move_class_dialog(self) -> None:
        """Prompt for moving a class to a different heat."""
        if not self._ensure_event_loaded():
            return

        dialog = tk.Toplevel(self.root)
        self._prepare_dialog(dialog)
        dialog.grab_set()

        classes = sorted(self.current_event.categories.keys(), key=str.lower)
        if not classes or not self.current_event.heats:
            messagebox.showwarning("Move class", "No classes or heats available")
            dialog.destroy()
            return

        class_name_variable = tk.StringVar(value=classes[0] if classes else "")
        heat_number_variable = tk.StringVar()

        ttk.Label(dialog, text="Class").grid(row=0, column=0, sticky=W, padx=8, pady=6)
        ttk.Combobox(
            dialog,
            textvariable=class_name_variable,
            values=classes,
            state="readonly",
            width=20,
        ).grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(dialog, text="Heat").grid(row=1, column=0, sticky=W, padx=8, pady=6)
        heat_combo = ttk.Combobox(
            dialog,
            textvariable=heat_number_variable,
            state="readonly",
            width=10,
        )
        heat_combo.grid(row=1, column=1, padx=8, pady=6)

        def update_heat_options(*_) -> None:
            """Update heat options based on the selected class."""
            # keep heat choices limited to actual moves
            category_name = class_name_variable.get().strip()
            current_heat = self.current_event.categories.get(category_name)
            current_heat_number = None
            if current_heat and current_heat.heat:
                current_heat_number = str(current_heat.heat.number)
            heat_values = [
                str(heat.number)
                for heat in self.current_event.heats
                if str(heat.number) != current_heat_number
            ]
            heat_combo.configure(values=heat_values)
            if heat_values:
                if heat_number_variable.get() not in heat_values:
                    heat_number_variable.set(heat_values[0])
            else:
                heat_number_variable.set("")

        class_name_variable.trace_add("write", update_heat_options)
        update_heat_options()

        def on_apply() -> None:
            """Apply the selected class move."""
            # apply the class move and refresh dependent views
            category = class_name_variable.get().strip()
            heat_number = heat_number_variable.get().strip()
            if not category or not heat_number:
                messagebox.showwarning(
                    "Move class", "Select a class and a destination heat."
                )
                return
            try:
                self.current_event.categories[category].set_heat(
                    self.current_event.get_heat(int(heat_number)), verbose=True
                )
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to move class: {exc}")
                return
            dialog.destroy()
            self._mark_event_dirty()
            self._refresh_event_views()
            self._validate_current_event()

        button_row = ttk.Frame(dialog)
        button_row.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(
            side=RIGHT, padx=4
        )
        ttk.Button(button_row, text="Apply", command=on_apply).pack(side=RIGHT, padx=4)
        self._finalize_dialog_size(dialog)

    def _rotate_run_work(self) -> None:
        """Rotate the run/work groups by one heat."""
        if not self._ensure_event_loaded():
            return

        offset = 1 % self.current_event.number_of_heats
        # rotate in place to preserve list references held elsewhere
        self.current_event.heats[:] = (
            self.current_event.heats[-offset:] + self.current_event.heats[:-offset]
        )
        self._mark_event_dirty()
        self._refresh_event_views()
        self._validate_current_event()

    # custom assignments ----------------------------------------------------------------------
    # manages assignment rows so config overrides are explicit and editable
    def _assignment_dialog(
        self,
        use=True,
        member_id="",
        assignment="",
        allowed_member_ids: set[str] | None = None,
        assigned_member_ids: set[str] | None = None,
    ) -> tuple[bool, str, str] | None:
        """Prompt for a custom assignment entry.

        Args:
            use: Whether the assignment is enabled.
            member_id: Selected member ID.
            assignment: Selected assignment role.
            allowed_member_ids: Optional set of member IDs to show in dropdowns.
            assigned_member_ids: Optional set of member IDs already assigned.

        Returns:
            tuple[bool, str, str] | None: (use flag, member ID, assignment) or None.
        """
        dialog = tk.Toplevel(self.root)
        self._prepare_dialog(dialog)
        dialog.grab_set()

        member_id = str(member_id) if member_id is not None else ""
        use_flag = bool(use)
        member_id_variable = tk.StringVar(value=member_id)
        member_name_variable = tk.StringVar(value="")
        assignment_variable = tk.StringVar(value=assignment)

        assigned_member_ids = {
            str(current_id)
            for current_id in (assigned_member_ids or set())
            if current_id is not None
        }
        if allowed_member_ids is None:
            allowed_member_ids = set(self.member_name_lookup.keys())
        allowed_member_ids = {
            str(current_id)
            for current_id in allowed_member_ids
            if current_id is not None
        }
        if member_id:
            allowed_member_ids.add(member_id)

        assignment_names: dict[str, str] = {}
        for item in self.assignments_tree.get_children():
            if self._is_add_assignment_row(item):
                continue
            values = self.assignments_tree.item(item)["values"]
            if len(values) >= 2:
                assignment_names[str(values[0]).strip()] = str(values[1]).strip()
        member_entries = []
        for current_member_id in allowed_member_ids:
            name = self.member_name_lookup.get(
                current_member_id
            ) or assignment_names.get(current_member_id, "")
            name = self._format_member_name_for_display(name)
            if not name:
                name = str(current_member_id)
            member_entries.append((str(current_member_id), name))

        member_entries.sort(key=lambda item: (item[1].lower(), item[0]))
        if not member_entries:
            messagebox.showwarning(
                "Custom assignments", "No members available for selection"
            )
            dialog.destroy()
            return None

        # precompute display names so name/id dropdowns stay aligned
        name_counts: dict[str, int] = {}
        for _, name in member_entries:
            name_counts[name] = name_counts.get(name, 0) + 1

        display_name_by_id: dict[str, str] = {}
        id_by_display_name: dict[str, str] = {}
        unique_name_to_id: dict[str, str] = {}
        for current_member_id, name in member_entries:
            display_name = (
                f"{name} ({current_member_id})"
                if name_counts.get(name, 0) > 1
                else name
            )
            display_name_by_id[current_member_id] = display_name
            id_by_display_name[display_name] = current_member_id
            if name_counts.get(name, 0) == 1:
                unique_name_to_id[name] = current_member_id

        member_id_values = [current_id for current_id, _ in member_entries]
        member_name_values = [
            display_name_by_id[current_id] for current_id, _ in member_entries
        ]

        member_id_state = "readonly"
        member_name_state = "readonly"

        ttk.Label(dialog, text="Member ID").grid(
            row=0, column=0, sticky=W, padx=8, pady=4
        )
        ttk.Combobox(
            dialog,
            textvariable=member_id_variable,
            values=member_id_values,
            state=member_id_state,
            width=32,
        ).grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(dialog, text="Name").grid(row=1, column=0, sticky=W, padx=8, pady=4)
        ttk.Combobox(
            dialog,
            textvariable=member_name_variable,
            values=member_name_values,
            state=member_name_state,
            width=32,
        ).grid(row=1, column=1, padx=8, pady=4)

        ttk.Label(dialog, text="Assignment").grid(
            row=2, column=0, sticky=W, padx=8, pady=4
        )
        ttk.Combobox(
            dialog,
            textvariable=assignment_variable,
            values=ASSIGNMENT_OPTIONS,
            state="readonly",
            width=20,
        ).grid(row=2, column=1, padx=8, pady=4)

        # guard against recursive trace updates when syncing dropdowns
        is_syncing = False

        def sync_from_id(*_) -> None:
            """Sync the name dropdown when the ID changes."""
            # update the name dropdown when the ID changes
            nonlocal is_syncing
            if is_syncing:
                return
            is_syncing = True
            selected_id = member_id_variable.get().strip()
            member_name_variable.set(display_name_by_id.get(selected_id, ""))
            is_syncing = False

        def sync_from_name(*_) -> None:
            """Sync the ID dropdown when the name changes."""
            # update the ID dropdown when the name changes
            nonlocal is_syncing
            if is_syncing:
                return
            is_syncing = True
            selected_name = member_name_variable.get().strip()
            selected_id = id_by_display_name.get(selected_name)
            if not selected_id:
                selected_id = unique_name_to_id.get(selected_name)
            if selected_id:
                member_id_variable.set(selected_id)
            is_syncing = False

        if not member_id_variable.get():
            member_id_variable.set(member_id_values[0])
        sync_from_id()

        member_id_variable.trace_add("write", sync_from_id)
        member_name_variable.trace_add("write", sync_from_name)

        result: dict[str, tuple[bool, str, str]] = {}

        def on_ok() -> None:
            """Validate selections and close the dialog."""
            # validate input before accepting the dialog
            member_value = member_id_variable.get().strip()
            name_value = member_name_variable.get().strip()
            assignment_value = assignment_variable.get().strip()
            if not member_value and name_value:
                member_value = id_by_display_name.get(name_value, "")
                if not member_value:
                    member_value = unique_name_to_id.get(name_value, "")
            if not member_value:
                messagebox.showwarning(
                    "Missing member", "Member ID or name is required"
                )
                return
            if member_value in assigned_member_ids and member_value != member_id:
                messagebox.showwarning(
                    "Duplicate member",
                    "That member already has a custom assignment.",
                )
                return
            if not assignment_value:
                messagebox.showwarning("Missing assignment", "Assignment is required")
                return
            result["data"] = (use_flag, member_value, assignment_value)
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(
            side=RIGHT, padx=4
        )
        ttk.Button(button_row, text="OK", command=on_ok).pack(side=RIGHT, padx=4)
        self._finalize_dialog_size(dialog)

        dialog.wait_window()
        return result.get("data")

    def _add_assignment_row(self) -> None:
        """Open the custom assignment dialog and insert a new row."""
        if not self.member_name_lookup:
            messagebox.showwarning(
                "Custom assignments",
                "Load member attributes CSV before adding assignments.",
            )
            return

        assigned_member_ids = {
            str(self.assignments_tree.item(item)["values"][0]).strip()
            for item in self.assignments_tree.get_children()
            if not self._is_add_assignment_row(item)
        }
        available_member_ids = {
            member_id
            for member_id in self.member_name_lookup.keys()
            if member_id not in assigned_member_ids
        }
        if not available_member_ids:
            messagebox.showwarning(
                "Custom assignments", "All members are already assigned."
            )
            return

        data = self._assignment_dialog(
            allowed_member_ids=available_member_ids,
            assigned_member_ids=assigned_member_ids,
        )
        if not data:
            return
        use_flag, member_id, assignment = data
        name = self.member_name_lookup.get(member_id, "")
        self._insert_assignment_row(use_flag, member_id, name, assignment)
        self._mark_config_dirty()

    def _remove_assignment_row(self) -> None:
        """Remove the selected custom assignment rows."""
        selected = self.assignments_tree.selection()
        for item in selected:
            if self._is_add_assignment_row(item):
                continue
            self.assignments_tree.delete(item)
            self.assignment_use_state.pop(item, None)
        if selected:
            self._mark_config_dirty()
        self._ensure_add_assignment_row()

    def _insert_assignment_row(
        self, use_flag: bool, member_id: str, name: str, assignment: str
    ) -> None:
        """Insert a custom assignment row into the table.

        Args:
            use_flag: Whether the assignment is enabled.
            member_id: Member identifier.
            name: Display name.
            assignment: Assigned role.
        """
        member_id = str(member_id).strip()
        name = str(name).strip()
        assignment = str(assignment).strip()
        item_id = self.assignments_tree.insert(
            "",
            END,
            image=(
                self.checkbox_checked_image
                if use_flag
                else self.checkbox_unchecked_image
            ),
            values=(member_id, name, assignment),
        )
        self.assignment_use_state[item_id] = use_flag
        self._refresh_assignment_styles()
        self._ensure_add_assignment_row()

    def _ensure_add_assignment_row(self) -> None:
        """Ensure the add-assignment row is the last row."""
        if self.assignment_add_row_id and self.assignments_tree.exists(
            self.assignment_add_row_id
        ):
            self.assignments_tree.delete(self.assignment_add_row_id)
        self.assignment_add_row_id = self.assignments_tree.insert(
            "",
            END,
            values=("", "+ Add assignment", ""),
            tags=("add_row",),
        )
        self.assignment_use_state.pop(self.assignment_add_row_id, None)
        self.assignments_tree.item(self.assignment_add_row_id, image="")
        self.assignments_tree.tag_configure("add_row", foreground=PALETTE["accent"])

    def _is_add_assignment_row(self, item_id: str) -> bool:
        """Check whether a row is the add-assignment sentinel row.

        Args:
            item_id: Treeview item identifier.

        Returns:
            bool: True when the row is the add row.
        """
        return item_id == self.assignment_add_row_id

    # assignment interactions -----------------------------------------------------------------
    # handles clicks and inline edits so assignment changes flow into the model
    def _on_assignment_click(self, event) -> str | None:
        """Handle single-click toggles for assignment checkboxes.

        Args:
            event: Tkinter click event.

        Returns:
            str | None: "break" when the click is handled.
        """
        self._clear_assignment_editor()
        item_id = self.assignments_tree.identify_row(event.y)
        if not item_id:
            return None
        if self._is_add_assignment_row(item_id):
            self._add_assignment_row()
            return "break"
        column = self.assignments_tree.identify_column(event.x)
        column_name = self._get_tree_column_name(self.assignments_tree, column)
        if column == "#0":
            self._toggle_assignment_use(item_id)
            self.assignments_tree.selection_set(item_id)
            return "break"
        if column_name == "assignment":
            self.assignments_tree.selection_set(item_id)

            def commit_assignment(value: str) -> None:
                """Persist the assignment selection to the table."""
                # update the inline value and mark config as modified
                values = list(self.assignments_tree.item(item_id)["values"])
                if len(values) < 3:
                    return
                values[2] = value
                self.assignments_tree.item(item_id, values=values)
                self._mark_config_dirty()

            self._show_assignment_editor(
                self.assignments_tree,
                item_id,
                column,
                ASSIGNMENT_OPTIONS,
                commit_assignment,
            )
            return "break"
        return None

    def _on_assignment_right_click(self, event) -> str | None:
        """Open the context menu for custom assignments.

        Args:
            event: Tkinter click event.

        Returns:
            str | None: "break" to stop event propagation.
        """
        item_id = self.assignments_tree.identify_row(event.y)
        if not item_id or self._is_add_assignment_row(item_id):
            return "break"
        self.assignments_tree.selection_set(item_id)
        if self.assignment_context_menu:
            self.assignment_context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _on_worker_assignment_click(self, event) -> str | None:
        """Open the inline assignment editor for worker rows.

        Args:
            event: Tkinter click event.

        Returns:
            str | None: "break" when the click is handled.
        """
        region = self.worker_tree.identify_region(event.x, event.y)
        if region != "cell":
            return None
        item_id = self.worker_tree.identify_row(event.y)
        if not item_id:
            return None
        column_id = self.worker_tree.identify_column(event.x)
        column_name = self._get_tree_column_name(self.worker_tree, column_id)
        if column_name != "assignment":
            return None

        participant = self.worker_table_mapping.get(item_id)
        if not participant:
            return "break"
        self.worker_tree.selection_set(item_id)

        def commit_assignment(value: str) -> None:
            """Persist the assignment selection to the participant."""
            # persist the assignment change to the participant model
            role = value.strip().lower()
            if not role:
                return
            try:
                participant.set_assignment(
                    role, show_previous=True, manual_override=True
                )
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to update assignment: {exc}")
                return
            self._mark_event_dirty()
            self._refresh_event_views()
            self._validate_current_event()

        self._show_assignment_editor(
            self.worker_tree,
            item_id,
            column_id,
            ROLE_OPTIONS,
            commit_assignment,
        )
        return "break"

    def _toggle_assignment_use(self, item_id: str) -> None:
        """Flip the use state for an assignment row.

        Args:
            item_id: Treeview item identifier.
        """
        use_flag = self.assignment_use_state.get(item_id, True)
        self.assignment_use_state[item_id] = not use_flag
        self._refresh_assignment_styles()
        self._mark_config_dirty()

    def _refresh_assignment_styles(self) -> None:
        """Refresh checkbox and text styles for assignment rows."""
        for item in self.assignments_tree.get_children():
            if self._is_add_assignment_row(item):
                continue
            use_flag = self.assignment_use_state.get(item, True)
            tag = "disabled" if not use_flag else ""
            self.assignments_tree.item(
                item,
                image=(
                    self.checkbox_checked_image
                    if use_flag
                    else self.checkbox_unchecked_image
                ),
            )
            self.assignments_tree.item(item, tags=(tag,))

    def _collect_assignments(self) -> dict[str, str]:
        """Collect active custom assignments from the table.

        Returns:
            dict[str, str]: Member ID to assignment mapping.
        """
        assignments: dict[str, str] = {}
        for item in self.assignments_tree.get_children():
            if self._is_add_assignment_row(item):
                continue
            if not self.assignment_use_state.get(item, False):
                continue
            member_id, _, assignment = self.assignments_tree.item(item)["values"]
            assignment_value = str(assignment).strip()
            if assignment_value:
                assignments[str(member_id)] = assignment_value
        return assignments

    def _refresh_assignment_names(self) -> None:
        """Refresh assignment table names from the member lookup."""
        for item in self.assignments_tree.get_children():
            if self._is_add_assignment_row(item):
                continue
            values = list(self.assignments_tree.item(item)["values"])
            member_id = str(values[0]).strip()
            values[1] = self.member_name_lookup.get(member_id, values[1])
            self.assignments_tree.item(item, values=values)

    # data loading ----------------------------------------------------------------------------
    # pulls external data files into lookup maps and warns on missing inputs
    def _on_config_variable_change(self, *_) -> None:
        """Mark config dirty when a tracked variable changes."""
        if self.is_applying_config:
            return
        self._mark_config_dirty()

    def _on_tsv_change(self, *_) -> None:
        """Warn when TSV files lack check-in data."""
        path_value = self.tsv_path_variable.get().strip()
        if not path_value:
            return
        try:
            tsv_path = Path(path_value)
        except TypeError:
            return
        if not tsv_path.is_absolute() and self.config_path:
            tsv_path = (self.config_path.parent / tsv_path).resolve()
        if not tsv_path.exists() or not tsv_path.is_file():
            return
        try:
            with open(tsv_path, newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file, delimiter="\t")
                fieldnames = [name for name in (reader.fieldnames or []) if name]
        except Exception:
            return
        if not fieldnames:
            return
        checkin_present = any(
            str(name).strip().lower() == "checkin" for name in fieldnames
        )
        if checkin_present:
            return
        # surface draft mode early so users know outputs will be locked
        messagebox.showinfo(
            "Draft mode",
            "No check-in data detected - DRAFT mode activated.",
        )

    def _on_member_csv_change(self, *_) -> None:
        """Reload member names when the member CSV changes."""
        if self.is_applying_config:
            return
        self._load_member_names()

    def _load_member_names(self) -> None:
        """Load member names from the attributes CSV into a lookup map."""
        self.member_name_lookup.clear()
        path = self.member_csv_path_variable.get().strip()
        if not path:
            self._refresh_assignment_names()
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    member_id = str(row.get("id", "")).strip()
                    member_name = self._format_member_name_for_display(
                        row.get("name", "")
                    )
                    if member_id:
                        self.member_name_lookup[member_id] = member_name
        except Exception as exc:
            messagebox.showwarning("Member attributes", f"Failed to load names: {exc}")
        self._refresh_assignment_names()

    # state updates ----------------------------------------------------------------------------
    # keeps dirty flags, status labels, and save enablement in sync
    def _ensure_event_loaded(self) -> bool:
        """Ensure an event exists before running event actions.

        Returns:
            bool: True if an event is loaded, False otherwise.
        """
        if not self.current_event:
            messagebox.showwarning("No event", "Generate or load an event first")
            return False
        return True

    def _event_is_draft(self) -> bool:
        """Check whether the current event is marked as draft."""
        return bool(getattr(self.current_event, "draft_mode", False))

    def _update_save_event_state(self) -> None:
        """Enable or disable Save Event based on state."""
        if self.is_generating:
            self.save_event_button.configure(state="disabled")
            return
        if self.current_event and not self._event_is_draft():
            self.save_event_button.configure(state="normal")
        else:
            self.save_event_button.configure(state="disabled")

    def _mark_config_dirty(self) -> None:
        """Mark the config as modified and refresh status."""
        self.config_dirty = True
        self._update_unsaved_indicator()

    def _mark_event_dirty(self) -> None:
        """Mark the event as modified and refresh status."""
        self.event_dirty = True
        self._update_unsaved_indicator()

    def _update_unsaved_indicator(self) -> None:
        """Update the unsaved/draft status label."""
        if self._event_is_draft():
            if self.config_dirty:
                message = "Unsaved changes: config, DRAFT event"
            else:
                message = "DRAFT event"
            self.unsaved_label.configure(text=message, style="Unsaved.TLabel")
            return

        parts = []
        if self.config_dirty:
            parts.append("config")
        if self.event_dirty:
            parts.append("event")
        if parts:
            message = f"Unsaved changes: {', '.join(parts)}"
            self.unsaved_label.configure(text=message, style="Unsaved.TLabel")
        else:
            self.unsaved_label.configure(text="All changes saved", style="Saved.TLabel")

    def _set_status(self, text: str) -> None:
        """Update the status message in the control panel.

        Args:
            text: Status text to display.
        """
        self.status_variable.set(text)

    # run loop --------------------------------------------------------------------------------
    # starts the tkinter event loop for the application
    def run(self) -> None:
        """Start the Tkinter main loop."""
        self.root.mainloop()


# support classes and entrypoint --------------------------------------------------------------
# keeps small helper classes and the script entrypoint grouped together
class HoverTooltip:
    """Display a tooltip for a widget while the cursor hovers."""

    def __init__(
        self,
        root: tk.Tk,
        widget: tk.Widget,
        text: str,
        background: str,
        foreground: str,
        font: tuple[str, int],
    ) -> None:
        self.root = root
        self.widget = widget
        self.text = text
        self.background = background
        self.foreground = foreground
        self.font = font
        self.tooltip_window: tk.Toplevel | None = None

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        self.widget.bind("<FocusOut>", self._on_leave, add="+")

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        """Show the tooltip when the cursor enters the widget."""
        if self.tooltip_window:
            return
        self._show_tooltip()

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        """Hide the tooltip when the cursor leaves the widget."""
        self._hide_tooltip()

    def _show_tooltip(self) -> None:
        """Create and display the tooltip window."""
        tooltip_window = tk.Toplevel(self.root)
        tooltip_window.withdraw()
        tooltip_window.overrideredirect(True)
        tooltip_window.attributes("-topmost", True)
        tooltip_label = tk.Label(
            tooltip_window,
            text=self.text,
            background=self.background,
            foreground=self.foreground,
            font=self.font,
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=4,
            justify="left",
        )
        tooltip_label.pack()
        tooltip_window.update_idletasks()
        x_position, y_position = self._calculate_position(tooltip_window)
        tooltip_window.geometry(f"+{x_position}+{y_position}")
        tooltip_window.deiconify()
        self.tooltip_window = tooltip_window

    def _hide_tooltip(self) -> None:
        """Destroy the tooltip window if it exists."""
        if not self.tooltip_window:
            return
        self.tooltip_window.destroy()
        self.tooltip_window = None

    def _calculate_position(self, tooltip_window: tk.Toplevel) -> tuple[int, int]:
        """Calculate a position that stays near, but not over, the widget."""
        widget_root_x = self.widget.winfo_rootx()
        widget_root_y = self.widget.winfo_rooty()
        widget_width = self.widget.winfo_width()
        widget_height = self.widget.winfo_height()
        tooltip_width = tooltip_window.winfo_reqwidth()
        tooltip_height = tooltip_window.winfo_reqheight()
        virtual_root_x = self.widget.winfo_vrootx()
        virtual_root_y = self.widget.winfo_vrooty()
        virtual_root_width = self.widget.winfo_vrootwidth()
        virtual_root_height = self.widget.winfo_vrootheight()

        if virtual_root_width <= 1 or virtual_root_height <= 1:
            virtual_root_x = 0
            virtual_root_y = 0
            virtual_root_width = self.widget.winfo_screenwidth()
            virtual_root_height = self.widget.winfo_screenheight()

        x_position = widget_root_x + widget_width + 8
        y_position = widget_root_y + max((widget_height - tooltip_height) // 2, 0)

        virtual_root_max_x = virtual_root_x + virtual_root_width
        virtual_root_max_y = virtual_root_y + virtual_root_height

        if x_position + tooltip_width > virtual_root_max_x:
            x_position = widget_root_x - tooltip_width - 8

        if x_position < virtual_root_x:
            x_position = virtual_root_x

        if y_position + tooltip_height > virtual_root_max_y:
            y_position = virtual_root_max_y - tooltip_height - 8

        if y_position < virtual_root_y:
            y_position = virtual_root_y

        return x_position, y_position


class GenerationCancelled(Exception):
    """Raised when a GUI generation run is cancelled."""


class EventUnpickler(pickle.Unpickler):
    """
    Unpickler with legacy module name support.

    Helps with loading old events from the beta version of this program.

    This will be removed in the future.
    """

    MODULE_ALIASES = {
        "Event": "autologic.event",
        "event": "autologic.event",
        "Heat": "autologic.heat",
        "heat": "autologic.heat",
        "Category": "autologic.category",
        "category": "autologic.category",
        "Participant": "autologic.participant",
        "participant": "autologic.participant",
        "Group": "autologic.group",
        "group": "autologic.group",
    }

    CLASS_MODULES = {
        "Event": "autologic.event",
        "Heat": "autologic.heat",
        "Category": "autologic.category",
        "Participant": "autologic.participant",
        "Group": "autologic.group",
    }

    def find_class(self, module: str, name: str):
        """Resolve legacy module names while unpickling events.

        Args:
            module: Module name recorded in the pickle.
            name: Class name recorded in the pickle.

        Returns:
            type: Resolved class object.
        """
        # map legacy module paths so older pickles still load cleanly
        module_alias = self.MODULE_ALIASES.get(module)
        if module_alias:
            module = module_alias
        elif module == "__main__" and name in self.CLASS_MODULES:
            module = self.CLASS_MODULES[name]
        return super().find_class(module, name)


if __name__ == "__main__":
    AutologicGUI().run()
