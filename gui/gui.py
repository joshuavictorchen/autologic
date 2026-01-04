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
from autologic.cli import Config, resolve_config_paths
from autologic.event import Event

ASSIGNMENT_OPTIONS = ["instructor", "timing", "grid", "start", "captain", "special"]
ROLE_OPTIONS = ASSIGNMENT_OPTIONS + ["worker"]
SUMMARY_COLUMNS = [
    "Heat",
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


class GenerationCancelled(Exception):
    """Raised when a GUI generation run is cancelled."""


class EventUnpickler(pickle.Unpickler):
    """Unpickler with legacy module name support."""

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
        module_alias = self.MODULE_ALIASES.get(module)
        if module_alias:
            module = module_alias
        elif module == "__main__" and name in self.CLASS_MODULES:
            module = self.CLASS_MODULES[name]
        return super().find_class(module, name)


class AutologicGUI:
    def __init__(self):
        self.root = ttk.Window(themename="flatly")
        self.root.title("Autologic")
        self.root.geometry("1800x1200")
        self.root.minsize(1200, 800)

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

        self.application_directory = self._get_application_directory()
        self.resource_root = self._get_resource_root()
        self.icon_path = self._get_icon_path()
        self.icon_photo_path = self._get_icon_photo_path()
        self.icon_photo_image: tk.PhotoImage | None = None
        self.default_config_path = self.application_directory / "autologic.yaml"
        self.config_path = self.default_config_path

        self._initialize_variables()
        self._configure_styles()
        self._initialize_checkbox_images()
        self._build_layout()
        self._register_variable_traces()
        self._ensure_default_config_file()
        self._load_config_from_path(self.default_config_path)
        self._update_unsaved_indicator()
        self._apply_window_icon(self.root)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_application_directory(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def _get_resource_root(self) -> Path:
        """Return the base directory for bundled resources."""
        if getattr(sys, "frozen", False):
            return Path(getattr(sys, "_MEIPASS", self.application_directory))
        return Path(__file__).resolve().parents[1]

    def _get_icon_path(self) -> Path | None:
        """Return the icon path if available."""
        candidates = [
            self.resource_root / "docs" / "images" / "autologic-icon.ico",
            self.application_directory / "autologic-icon.ico",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _get_icon_photo_path(self) -> Path | None:
        """Return the icon PNG path if available."""
        candidates = [
            self.resource_root / "docs" / "images" / "autologic-icon.png",
            self.application_directory / "autologic-icon.png",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _apply_window_icon(self, window: tk.Misc) -> None:
        """Set the window icon if the icon file is available."""
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
        """Configure shared dialog attributes."""
        dialog.title("")
        dialog.configure(background=PALETTE["panel"])
        dialog.transient(self.root)
        dialog.resizable(False, False)
        self._apply_window_icon(dialog)

    def _get_tree_column_name(self, tree: ttk.Treeview, column_id: str) -> str | None:
        """Return the column name for a Treeview column id."""
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

    def _clear_assignment_editor(self) -> None:
        """Remove any active inline assignment editor."""
        if self.assignment_editor:
            self.assignment_editor.destroy()
            self.assignment_editor = None

    def _is_combobox_popdown_visible(self, combobox: ttk.Combobox) -> bool:
        """Return True if the combobox popdown window is visible."""
        try:
            popdown = combobox.tk.call("ttk::combobox::PopdownWindow", combobox)
            return bool(int(combobox.tk.call("winfo", "viewable", popdown)))
        except tk.TclError:
            return False

    def _show_assignment_editor(
        self,
        tree: ttk.Treeview,
        item_id: str,
        column_id: str,
        options: list[str],
        on_commit,
    ) -> None:
        """Show an inline combobox editor for assignment columns."""
        self._clear_assignment_editor()
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
            def maybe_finish() -> None:
                if not self.assignment_editor or not editor.winfo_exists():
                    return
                if self._is_combobox_popdown_visible(editor):
                    editor.after(50, maybe_finish)
                    return
                finish(True)

            editor.after(1, maybe_finish)

        editor.bind("<FocusOut>", handle_focus_out)
        editor.after(0, lambda: editor.tk.call("ttk::combobox::Post", editor))

    def _initialize_variables(self) -> None:
        default_algorithm = (
            "randomize"
            if "randomize" in self.algorithms
            else next(iter(self.algorithms))
        )

        self.event_name_variable = tk.StringVar(value="autologic-event")
        self.heats_variable = tk.StringVar(value="3")
        self.stations_variable = tk.StringVar(value="5")
        self.heat_parity_variable = tk.StringVar(value="25")
        self.novice_parity_variable = tk.StringVar(value="10")
        self.novice_denominator_variable = tk.StringVar(value="3")
        self.max_iterations_variable = tk.StringVar(value="10000")
        self.algorithm_variable = tk.StringVar(value=default_algorithm)
        self.tsv_path_variable = tk.StringVar()
        self.member_csv_path_variable = tk.StringVar()
        self.config_path_variable = tk.StringVar(value=str(self.config_path))
        self.validation_status_variable = tk.StringVar(value="Validation: --")
        self.status_variable = tk.StringVar(value="Ready")

    def _configure_styles(self) -> None:
        style = ttk.Style()
        colors = style.colors
        palette = PALETTE
        self.root.configure(background=palette["background"])
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
            foreground=colors.dark,
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
            foreground=colors.dark,
            font=("Segoe UI", 9, "bold"),
            borderwidth=1,
            relief="raised",
        )
        style.map("Treeview.Heading", background=[("active", palette["header"])])
        style.configure(
            "Summary.Header.TLabel",
            font=("Segoe UI", 9, "bold"),
            background=palette["header"],
            foreground=colors.dark,
        )
        style.configure(
            "Summary.Valid.TLabel", background=palette["panel"], foreground=colors.fg
        )
        style.configure(
            "Summary.Invalid.TLabel",
            background=colors.danger,
            foreground=colors.selectfg,
        )
        style.configure(
            "Saved.TLabel",
            background=palette["panel"],
            foreground=colors.success,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Unsaved.TLabel",
            background=palette["panel"],
            foreground=colors.warning,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Validation.Ok.TLabel",
            background=palette["panel"],
            foreground=colors.success,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Validation.Invalid.TLabel",
            background=palette["panel"],
            foreground=colors.warning,
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

    def _initialize_checkbox_images(self) -> None:
        """Create checkbox images for the assignments table."""
        self.checkbox_unchecked_image = self._create_checkbox_image(checked=False)
        self.checkbox_checked_image = self._create_checkbox_image(checked=True)

    def _create_checkbox_image(self, checked: bool) -> tk.PhotoImage:
        """Build a checkbox image for Treeview rows.

        Args:
            checked: Whether to render the checkbox in a checked state.

        Returns:
            tk.PhotoImage: Checkbox image.
        """
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

    def _finalize_dialog_size(self, dialog: tk.Toplevel) -> None:
        """Set the dialog size to its requested size and center it."""
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

    def _build_layout(self) -> None:
        container = tk.Frame(self.root, background=PALETTE["background"])
        container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        left_column = tk.Frame(container, background=PALETTE["background"])
        right_column = tk.Frame(container, background=PALETTE["background"])
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_column.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        left_column.columnconfigure(0, weight=1)
        left_column.rowconfigure(0, weight=0)
        left_column.rowconfigure(1, weight=0)
        left_column.rowconfigure(2, weight=1)

        right_column.columnconfigure(0, weight=1)
        right_column.rowconfigure(0, weight=1)

        self.control_panel = ttk.Labelframe(
            left_column, text="Control Panel", padding=10
        )
        self.control_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
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
        button_row = ttk.Frame(parent)
        button_row.pack(fill=X, pady=(0, 8))

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

        config_row = ttk.Frame(parent)
        config_row.pack(fill=X, pady=(0, 6))
        ttk.Label(config_row, text="Config file").pack(side=LEFT, padx=(0, 6))
        ttk.Entry(
            config_row,
            textvariable=self.config_path_variable,
            state="readonly",
            width=48,
        ).pack(side=LEFT, fill=X, expand=True)

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
        form = ttk.Frame(parent)
        form.pack(fill=X)

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

        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=X, pady=(10, 0))
        self._add_file_picker(
            file_frame,
            "AXWare TSV",
            self.tsv_path_variable,
            0,
            lambda: self._browse_file(
                self.tsv_path_variable,
                filetypes=[("TSV", "*.tsv"), ("All files", "*.*")],
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
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True)

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
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=0)
        parent.rowconfigure(2, weight=2)

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

        self.heat_tree = ttk.Treeview(
            heat_frame,
            columns=("heat", "running", "working", "classes"),
            show="headings",
            height=2,
        )
        self.heat_tree.heading("heat", text="Heat")
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

    def _register_variable_traces(self) -> None:
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
        for variable in config_variables:
            variable.trace_add("write", self._on_config_variable_change)

        self.member_csv_path_variable.trace_add("write", self._on_member_csv_change)

    def _on_close(self) -> None:
        self.root.destroy()

    def _add_labeled_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
        width: int = 20,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky=W, padx=4)
        ttk.Entry(parent, textvariable=variable, width=width).grid(
            row=row, column=column + 1, sticky=W, padx=4
        )

    def _add_file_picker(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        browse_command,
    ) -> None:
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
        options = {"initialdir": str(self.application_directory)}
        if filetypes:
            options["filetypes"] = filetypes
        file_path = filedialog.askopenfilename(**options)
        if file_path:
            target_variable.set(file_path)

    def _ensure_default_config_file(self) -> None:
        if self.default_config_path.exists():
            return
        try:
            self.default_config_path.write_text("", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(
                "Error", f"Failed to create default config file: {exc}"
            )

    def _load_config_prompt(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=str(self.application_directory),
            filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not path:
            return
        self._load_config_from_path(Path(path))

    def _load_config_from_path(self, config_path: Path) -> None:
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config_data = yaml.safe_load(file) or {}
            config_data = resolve_config_paths(config_data, config_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load config: {exc}")
            return

        self.config_path = config_path
        self.config_path_variable.set(str(config_path))

        self.is_applying_config = True
        try:
            self._apply_config_data(config_data)
        finally:
            self.is_applying_config = False

        self._load_member_names()
        self.config_dirty = False
        self._set_status("Loaded config")
        self._update_unsaved_indicator()

    def _apply_config_data(self, config_data: dict) -> None:
        if "name" in config_data:
            self.event_name_variable.set(str(config_data["name"]))
        if "axware_export_tsv" in config_data:
            self.tsv_path_variable.set(str(config_data["axware_export_tsv"]))
        if "member_attributes_csv" in config_data:
            self.member_csv_path_variable.set(str(config_data["member_attributes_csv"]))
        if "number_of_heats" in config_data:
            self.heats_variable.set(str(config_data["number_of_heats"]))
        if "number_of_stations" in config_data:
            self.stations_variable.set(str(config_data["number_of_stations"]))
        if "heat_size_parity" in config_data:
            self.heat_parity_variable.set(str(config_data["heat_size_parity"]))
        if "novice_size_parity" in config_data:
            self.novice_parity_variable.set(str(config_data["novice_size_parity"]))
        if "novice_denominator" in config_data:
            self.novice_denominator_variable.set(str(config_data["novice_denominator"]))
        if "max_iterations" in config_data:
            self.max_iterations_variable.set(str(config_data["max_iterations"]))
        if "algorithm" in config_data and config_data["algorithm"] in self.algorithms:
            self.algorithm_variable.set(str(config_data["algorithm"]))

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

    def _save_config(self) -> bool:
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

    def _on_generate_button(self) -> None:
        if self.is_generating:
            self._cancel_generation()
        else:
            self._start_generation()

    def _start_generation(self) -> None:
        config_data = self._build_config_payload()
        algorithm = config_data.get("algorithm", self.algorithm_variable.get())
        resolved_config_data = resolve_config_paths(config_data, self.config_path)
        resolved_config_data.pop("algorithm", None)

        try:
            config = Config(**resolved_config_data)
            config.validate_paths()
        except Exception as exc:
            messagebox.showerror("Error", f"Invalid configuration: {exc}")
            return

        self._set_status("Generating event...")
        self._set_generation_state(True)
        self.generation_cancel_requested.clear()
        while not self.generation_result_queue.empty():
            try:
                self.generation_result_queue.get_nowait()
            except queue.Empty:
                break

        config_payload = config.model_dump()
        self.generation_thread = threading.Thread(
            target=self._run_generation_thread,
            args=(config_payload, algorithm),
            daemon=True,
        )
        self.generation_thread.start()
        self.root.after(100, self._check_generation_queue)

    def _cancel_generation(self) -> None:
        self.generation_cancel_requested.set()
        self._set_status("Canceling generation...")

    def _run_generation_thread(self, config_payload: dict, algorithm: str) -> None:
        event: Event | None = None
        error: Exception | None = None
        try:
            event = load_event(**config_payload)
            main(
                algorithm=algorithm,
                event=event,
                interactive=False,
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
        if self.generation_cancel_requested.is_set():
            raise GenerationCancelled("Generation cancelled")

    def _check_generation_queue(self) -> None:
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
        self.is_generating = is_generating
        if is_generating:
            self.generate_button.configure(text="Cancel", bootstyle="danger")
            self.save_event_button.configure(state="disabled")
        else:
            self.generate_button.configure(text="Generate Event", bootstyle="primary")
            self.save_event_button.configure(
                state="normal" if self.current_event else "disabled"
            )

    def _save_event(self) -> None:
        if not self._ensure_event_loaded():
            return

        raw_name = self.event_name_variable.get().strip()
        if not raw_name:
            messagebox.showwarning("Missing event name", "Event name is required")
            return
        event_name = raw_name
        output_dir = self._get_output_directory()

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

        self.current_event.name = event_name
        self.event_name_variable.set(event_name)

        if not self._save_config():
            return

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
        path = filedialog.askopenfilename(
            initialdir=str(self.application_directory),
            filetypes=[("Pickle", "*.pkl"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "rb") as file:
                self.current_event = EventUnpickler(file).load()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load event: {exc}")
            return

        self._apply_event_parameters(self.current_event)
        self.event_dirty = False
        self._refresh_event_views()
        self._set_status("Loaded event")
        self._update_unsaved_indicator()

    def _apply_event_parameters(self, event: Event) -> None:
        self.is_applying_config = True
        try:
            self.event_name_variable.set(str(event.name))
            self.heats_variable.set(str(event.number_of_heats))
            self.stations_variable.set(str(event.number_of_stations))
            self.heat_parity_variable.set(str(event.heat_size_parity))
            self.novice_parity_variable.set(str(event.novice_size_parity))
            self.novice_denominator_variable.set(str(event.novice_denominator))
            self.max_iterations_variable.set(str(event.max_iterations))
        finally:
            self.is_applying_config = False
        self._mark_config_dirty()

    def _refresh_event_views(self) -> None:
        self._clear_assignment_editor()
        self._refresh_heat_table()
        self._refresh_summary_table()
        self._refresh_worker_table()
        self.save_event_button.configure(
            state="normal" if self.current_event else "disabled"
        )

    def _refresh_heat_table(self) -> None:
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

    def _evaluate_event_validity(self) -> dict:
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

    def _refresh_worker_table(self) -> None:
        self.worker_tree.delete(*self.worker_tree.get_children())
        self.worker_table_mapping.clear()
        if not self.current_event:
            return

        rows = []
        for heat in self.current_event.heats:
            for participant in heat.participants:
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

        rows.sort(reverse=self.worker_sort_descending)

        for index, (_, item_id) in enumerate(rows):
            self.worker_tree.move(item_id, "", index)

        self._update_worker_sort_headings()

    def _update_worker_sort_headings(self) -> None:
        """Update worker table headers to show sort direction."""
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
        numeric_columns = {"working", "number"}
        if column_name in numeric_columns:
            try:
                return int(value)
            except ValueError:
                return 0
        return str(value).lower()

    def _move_class_dialog(self) -> None:
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
        if not self._ensure_event_loaded():
            return

        offset = 1 % self.current_event.number_of_heats
        self.current_event.heats[:] = (
            self.current_event.heats[-offset:] + self.current_event.heats[:-offset]
        )
        self._mark_event_dirty()
        self._refresh_event_views()
        self._validate_current_event()

    # assignment editing now handled inline via single-click dropdowns

    def _validate_current_event(self) -> None:
        if not self.current_event:
            return
        try:
            is_valid = self.current_event.validate()
        except Exception as exc:
            messagebox.showerror("Error", f"Validation error: {exc}")
            return
        self._set_status("Validation passed" if is_valid else "Validation failed")

    def _get_assignment_member_ids(self) -> set[str]:
        """Return member IDs already assigned in the custom assignments table."""
        return {
            str(self.assignments_tree.item(item)["values"][0]).strip()
            for item in self.assignments_tree.get_children()
            if not self._is_add_assignment_row(item)
        }

    def _get_assignment_names_by_id(self) -> dict[str, str]:
        """Return a mapping of member IDs to names from the assignments table."""
        names_by_id: dict[str, str] = {}
        for item in self.assignments_tree.get_children():
            if self._is_add_assignment_row(item):
                continue
            values = self.assignments_tree.item(item)["values"]
            if len(values) >= 2:
                names_by_id[str(values[0]).strip()] = str(values[1]).strip()
        return names_by_id

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

        assignment_names = self._get_assignment_names_by_id()
        member_entries = []
        for current_member_id in allowed_member_ids:
            name = self.member_name_lookup.get(
                current_member_id
            ) or assignment_names.get(current_member_id, "")
            name = str(name).strip() if name else ""
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

        is_syncing = False

        def sync_from_id(*_) -> None:
            nonlocal is_syncing
            if is_syncing:
                return
            is_syncing = True
            selected_id = member_id_variable.get().strip()
            member_name_variable.set(display_name_by_id.get(selected_id, ""))
            is_syncing = False

        def sync_from_name(*_) -> None:
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
        if not self.member_name_lookup:
            messagebox.showwarning(
                "Custom assignments",
                "Load member attributes CSV before adding assignments.",
            )
            return

        assigned_member_ids = self._get_assignment_member_ids()
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
        return item_id == self.assignment_add_row_id

    def _on_assignment_click(self, event) -> str | None:
        """Handle single-click toggles for assignment checkboxes."""
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
        item_id = self.assignments_tree.identify_row(event.y)
        if not item_id or self._is_add_assignment_row(item_id):
            return "break"
        self.assignments_tree.selection_set(item_id)
        if self.assignment_context_menu:
            self.assignment_context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _on_worker_assignment_click(self, event) -> str | None:
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
        for item in self.assignments_tree.get_children():
            if self._is_add_assignment_row(item):
                continue
            values = list(self.assignments_tree.item(item)["values"])
            member_id = str(values[0]).strip()
            values[1] = self.member_name_lookup.get(member_id, values[1])
            self.assignments_tree.item(item, values=values)

    def _on_config_variable_change(self, *_) -> None:
        if self.is_applying_config:
            return
        self._mark_config_dirty()

    def _on_member_csv_change(self, *_) -> None:
        if self.is_applying_config:
            return
        self._load_member_names()

    def _load_member_names(self) -> None:
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
                    member_name = str(row.get("name", "")).strip()
                    if member_id:
                        self.member_name_lookup[member_id] = member_name
        except Exception as exc:
            messagebox.showwarning("Member attributes", f"Failed to load names: {exc}")
        self._refresh_assignment_names()

    def _ensure_event_loaded(self) -> bool:
        if not self.current_event:
            messagebox.showwarning("No event", "Generate or load an event first")
            return False
        return True

    def _mark_config_dirty(self) -> None:
        self.config_dirty = True
        self._update_unsaved_indicator()

    def _mark_event_dirty(self) -> None:
        self.event_dirty = True
        self._update_unsaved_indicator()

    def _update_unsaved_indicator(self) -> None:
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

    def _get_output_directory(self) -> Path:
        """Return the directory for generated outputs."""
        if self.config_path:
            return self.config_path.parent
        return self.application_directory

    def _set_status(self, text: str) -> None:
        self.status_variable.set(text)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    AutologicGUI().run()
