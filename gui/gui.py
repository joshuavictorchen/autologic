import csv
import pickle
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, END, LEFT, RIGHT, W, X, Y
import yaml

from autologic import utils
from autologic.algorithms import get_algorithms
from autologic.app import load_event, main
from autologic.cli import Config
from autologic.event import Event

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


class ConsoleRedirector:
    def __init__(self, text_widget: tk.Text, original_stream):
        self.text_widget = text_widget
        self.original_stream = original_stream

    def write(self, message: str) -> None:
        if self.original_stream:
            self.original_stream.write(message)
        if not message:
            return
        self.text_widget.after(0, self._append, message)

    def flush(self) -> None:
        if self.original_stream:
            self.original_stream.flush()

    def _append(self, message: str) -> None:
        self.text_widget.insert(END, message)
        self.text_widget.see(END)


class AutologicGUI:
    def __init__(self):
        self.root = ttk.Window(themename="flatly")
        self.root.title("Autologic")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)

        self.algorithms = {k: v for k, v in get_algorithms().items() if k != "example"}
        self.current_event: Event | None = None
        self.config_dirty = False
        self.event_dirty = False
        self.is_applying_config = False
        self.member_name_lookup: dict[str, str] = {}
        self.worker_table_mapping: dict[str, object] = {}
        self.worker_sort_state: dict[str, bool] = {}

        self.application_directory = self._get_application_directory()
        self.default_config_path = self.application_directory / "autologic.yaml"
        self.config_path = self.default_config_path

        self._initialize_variables()
        self._configure_styles()
        self._build_layout()
        self._register_variable_traces()
        self._attach_console_redirector()
        self._ensure_default_config_file()
        self._load_config_from_path(self.default_config_path)
        self._update_unsaved_indicator()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_application_directory(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

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
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=26)
        style.configure(
            "Summary.Header.TLabel",
            font=("Segoe UI", 9, "bold"),
            background=colors.light,
            foreground=colors.dark,
        )
        style.configure(
            "Summary.Valid.TLabel", background=colors.bg, foreground=colors.fg
        )
        style.configure(
            "Summary.Invalid.TLabel",
            background=colors.danger,
            foreground=colors.selectfg,
        )

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        left_column = ttk.Frame(container)
        right_column = ttk.Frame(container)
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
        right_column.rowconfigure(1, weight=0)

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
        self.data_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self._build_data_panel(self.data_panel)

        self.log_panel = ttk.Labelframe(right_column, text="Console Log", padding=10)
        self.log_panel.grid(row=1, column=0, sticky="nsew")
        self._build_log_panel(self.log_panel)

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

        ttk.Button(
            button_row,
            text="Generate Event",
            bootstyle="primary",
            command=self._generate_event,
        ).pack(side=LEFT, padx=4)
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
        self.unsaved_label = ttk.Label(status_row, text="", anchor=W)
        self.unsaved_label.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(status_row, textvariable=self.status_variable, anchor=W).pack(
            side=RIGHT
        )

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
            "Member attributes CSV",
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
            columns=("use", "member_id", "name", "assignment"),
            show="headings",
            height=8,
        )
        self.assignments_tree.heading("use", text="Use")
        self.assignments_tree.heading("member_id", text="Member ID")
        self.assignments_tree.heading("name", text="Name")
        self.assignments_tree.heading("assignment", text="Assignment")
        self.assignments_tree.column("use", width=50, anchor="center")
        self.assignments_tree.column("member_id", width=120, anchor=W)
        self.assignments_tree.column("name", width=180, anchor=W)
        self.assignments_tree.column("assignment", width=140, anchor=W)
        self.assignments_tree.tag_configure("disabled", foreground="#888888")
        self.assignments_tree.bind("<Double-1>", self._toggle_assignment_use)
        self.assignments_tree.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side=RIGHT, fill=Y)
        self.assignments_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.assignments_tree.yview)

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=X, pady=(6, 0))
        ttk.Button(button_frame, text="Add", command=self._add_assignment_row).pack(
            side=LEFT, padx=4
        )
        ttk.Button(
            button_frame, text="Modify", command=self._modify_assignment_row
        ).pack(side=LEFT, padx=4)
        ttk.Button(
            button_frame, text="Remove", command=self._remove_assignment_row
        ).pack(side=LEFT, padx=4)

    def _build_data_panel(self, parent: ttk.Labelframe) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=2)

        top_frame = ttk.Frame(parent)
        top_frame.grid(row=0, column=0, sticky="nsew")
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)
        top_frame.rowconfigure(0, weight=1)

        heat_frame = ttk.Labelframe(top_frame, text="Heats & Classes", padding=8)
        heat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
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
            command=self._rotate_run_work_dialog,
        ).pack(side=LEFT, padx=4)

        self.heat_tree = ttk.Treeview(
            heat_frame,
            columns=("heat", "running", "working", "classes"),
            show="headings",
            height=6,
        )
        self.heat_tree.heading("heat", text="Heat")
        self.heat_tree.heading("running", text="Running")
        self.heat_tree.heading("working", text="Working")
        self.heat_tree.heading("classes", text="Classes")
        self.heat_tree.column("heat", width=60, anchor="center")
        self.heat_tree.column("running", width=70, anchor="center")
        self.heat_tree.column("working", width=70, anchor="center")
        self.heat_tree.column("classes", width=260, anchor=W)
        self.heat_tree.grid(row=1, column=0, sticky="nsew")
        heat_scrollbar = ttk.Scrollbar(heat_frame, orient="vertical")
        heat_scrollbar.grid(row=1, column=1, sticky="ns")
        self.heat_tree.configure(yscrollcommand=heat_scrollbar.set)
        heat_scrollbar.configure(command=self.heat_tree.yview)

        summary_frame = ttk.Labelframe(top_frame, text="Role Summary", padding=8)
        summary_frame.grid(row=0, column=1, sticky="nsew")
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(1, weight=1)

        ttk.Label(
            summary_frame, textvariable=self.validation_status_variable, anchor=W
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.summary_table_container = ttk.Frame(summary_frame)
        self.summary_table_container.grid(row=1, column=0, sticky="nsew")

        worker_frame = ttk.Labelframe(parent, text="Worker Tracking", padding=8)
        worker_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        worker_frame.columnconfigure(0, weight=1)
        worker_frame.rowconfigure(1, weight=1)

        worker_button_row = ttk.Frame(worker_frame)
        worker_button_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(
            worker_button_row,
            text="Update Assignment",
            command=self._update_assignment_dialog,
        ).pack(side=LEFT, padx=4)

        self.worker_tree = ttk.Treeview(
            worker_frame,
            columns=(
                "working",
                "name",
                "class",
                "number",
                "assignment",
                "checked_in",
            ),
            show="headings",
            height=10,
        )
        self.worker_tree.heading("working", text="Working")
        self.worker_tree.heading("name", text="Name")
        self.worker_tree.heading("class", text="Class")
        self.worker_tree.heading("number", text="Number")
        self.worker_tree.heading("assignment", text="Assignment")
        self.worker_tree.heading("checked_in", text="Checked In")

        for column_id in self.worker_tree["columns"]:
            self.worker_tree.heading(
                column_id,
                text=self.worker_tree.heading(column_id)["text"],
                command=lambda c=column_id: self._sort_worker_table(c),
            )

        self.worker_tree.column("working", width=70, anchor="center")
        self.worker_tree.column("name", width=180, anchor=W)
        self.worker_tree.column("class", width=80, anchor="center")
        self.worker_tree.column("number", width=80, anchor="center")
        self.worker_tree.column("assignment", width=120, anchor=W)
        self.worker_tree.column("checked_in", width=90, anchor="center")
        self.worker_tree.bind("<Double-1>", self._update_assignment_dialog)

        self.worker_tree.grid(row=1, column=0, sticky="nsew")
        worker_scrollbar = ttk.Scrollbar(worker_frame, orient="vertical")
        worker_scrollbar.grid(row=1, column=1, sticky="ns")
        self.worker_tree.configure(yscrollcommand=worker_scrollbar.set)
        worker_scrollbar.configure(command=self.worker_tree.yview)

    def _build_log_panel(self, parent: ttk.Labelframe) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self.log_text = tk.Text(parent, height=10, wrap="word", font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            parent, orient="vertical", command=self.log_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

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

    def _attach_console_redirector(self) -> None:
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = ConsoleRedirector(self.log_text, self.original_stdout)
        sys.stderr = ConsoleRedirector(self.log_text, self.original_stderr)

    def _on_close(self) -> None:
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
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
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=W, padx=4, pady=2)
        ttk.Entry(parent, textvariable=variable, width=48).grid(
            row=row, column=1, sticky=W, padx=4, pady=2
        )
        ttk.Button(parent, text="Browse", command=browse_command).grid(
            row=row, column=2, sticky=W, padx=4, pady=2
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
        self._set_status(f"Loaded config from {config_path}")
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

        custom_assignments = config_data.get("custom_assignments", {}) or {}
        for member_id, assignment in custom_assignments.items():
            self._insert_assignment_row(
                True,
                str(member_id),
                self.member_name_lookup.get(str(member_id), ""),
                str(assignment),
            )

        self._refresh_assignment_names()

    def _save_config(self) -> None:
        try:
            config_data = self._build_config_payload()
        except ValueError as exc:
            messagebox.showerror("Error", f"Invalid configuration: {exc}")
            return

        try:
            with open(self.config_path, "w", encoding="utf-8") as file:
                yaml.safe_dump(config_data, file, sort_keys=False)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to save config: {exc}")
            return

        self.config_dirty = False
        self._set_status(f"Saved config to {self.config_path}")
        self._update_unsaved_indicator()

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

    def _generate_event(self) -> None:
        if not self._save_config_silently():
            return

        config_data = self._build_config_payload()
        algorithm = config_data.pop("algorithm", self.algorithm_variable.get())

        try:
            config = Config(**config_data)
            config.validate_paths()
        except Exception as exc:
            messagebox.showerror("Error", f"Invalid configuration: {exc}")
            return

        self._clear_log()
        self._append_log("Generating event...\n")

        def observer(event_type: str, payload: dict) -> None:
            self._append_log(f"{event_type}: {payload}\n")

        try:
            event = load_event(**config.model_dump())
            main(
                algorithm=algorithm,
                event=event,
                interactive=False,
                observer=observer,
                export=False,
            )
        except SystemExit:
            messagebox.showerror("Error", "Generation failed; see log for details.")
            self._set_status("Generation failed")
            return
        except Exception as exc:
            messagebox.showerror("Error", f"Generation failed: {exc}")
            self._set_status("Generation failed")
            return

        self.current_event = event
        self.event_dirty = True
        self._refresh_event_views()
        self._set_status("Generation completed")
        self._update_unsaved_indicator()

    def _save_event(self) -> None:
        if not self._ensure_event_loaded():
            return

        raw_name = self.event_name_variable.get().strip()
        if not raw_name:
            messagebox.showwarning("Missing event name", "Event name is required")
            return

        sanitized_name = self._sanitize_event_name(raw_name)
        output_paths = [
            Path(f"{sanitized_name}.csv"),
            Path(f"{sanitized_name}.pdf"),
            Path(f"{sanitized_name}.pkl"),
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

        self.current_event.name = sanitized_name
        self.event_name_variable.set(sanitized_name)

        try:
            self.current_event.to_csv()
            self.current_event.to_pdf()
            self.current_event.to_pickle()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save event: {exc}")
            return

        self.event_dirty = False
        self._set_status(f"Saved event as {sanitized_name}")
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
                self.current_event = pickle.load(file)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load event: {exc}")
            return

        self._apply_event_parameters(self.current_event)
        self.event_dirty = False
        self._refresh_event_views()
        self._set_status(f"Loaded event {self.current_event.name}")
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
            return

        validation_state = self._evaluate_event_validity()
        event_is_valid = validation_state["event_is_valid"]
        invalid_cells = validation_state["invalid_cells"]
        self.validation_status_variable.set(
            "Validation: OK" if event_is_valid else "Validation: Issues"
        )

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
                        participant.axware_category,
                        participant.number,
                        participant.assignment or "",
                        "",
                        participant,
                    )
                )

        rows.sort(key=lambda row: (row[0], row[1].lower()))

        for row in rows:
            item_id = self.worker_tree.insert(
                "",
                END,
                values=(row[0], row[1], row[2], row[3], row[4], row[5]),
            )
            self.worker_table_mapping[item_id] = row[6]

    def _sort_worker_table(self, column_name: str) -> None:
        if not self.current_event:
            return

        reverse_sort = self.worker_sort_state.get(column_name, False)
        rows = []
        for item_id in self.worker_tree.get_children():
            value = self.worker_tree.set(item_id, column_name)
            rows.append((self._coerce_sort_value(column_name, value), item_id))

        rows.sort(reverse=reverse_sort)

        for index, (_, item_id) in enumerate(rows):
            self.worker_tree.move(item_id, "", index)

        self.worker_sort_state[column_name] = not reverse_sort

    def _coerce_sort_value(self, column_name: str, value: str):
        numeric_columns = {"working", "number"}
        if column_name in numeric_columns:
            try:
                return int(value)
            except ValueError:
                return 0
        return value.lower()

    def _move_class_dialog(self) -> None:
        if not self._ensure_event_loaded():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Move class")
        dialog.grab_set()
        dialog.resizable(False, False)

        classes = sorted(self.current_event.categories.keys(), key=str.lower)
        heats = [str(heat.number) for heat in self.current_event.heats]
        if not classes or not heats:
            messagebox.showwarning("Move class", "No classes or heats available")
            dialog.destroy()
            return

        class_name_variable = tk.StringVar(value=classes[0] if classes else "")
        heat_number_variable = tk.StringVar(value=heats[0] if heats else "")

        ttk.Label(dialog, text="Class").grid(row=0, column=0, sticky=W, padx=8, pady=6)
        ttk.Combobox(
            dialog,
            textvariable=class_name_variable,
            values=classes,
            state="readonly",
            width=20,
        ).grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(dialog, text="Heat").grid(row=1, column=0, sticky=W, padx=8, pady=6)
        ttk.Combobox(
            dialog,
            textvariable=heat_number_variable,
            values=heats,
            state="readonly",
            width=10,
        ).grid(row=1, column=1, padx=8, pady=6)

        def on_apply() -> None:
            category = class_name_variable.get().strip()
            heat_number = heat_number_variable.get().strip()
            if not category or not heat_number:
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

    def _rotate_run_work_dialog(self) -> None:
        if not self._ensure_event_loaded():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Rotate run/work")
        dialog.grab_set()
        dialog.resizable(False, False)

        offset_variable = tk.StringVar(value="1")
        ttk.Label(dialog, text="Offset").grid(row=0, column=0, sticky=W, padx=8, pady=6)
        ttk.Entry(dialog, textvariable=offset_variable, width=8).grid(
            row=0, column=1, padx=8, pady=6
        )

        def on_apply() -> None:
            offset_text = offset_variable.get().strip()
            if not offset_text.isdigit():
                messagebox.showwarning("Invalid offset", "Offset must be a number")
                return
            offset = int(offset_text) % self.current_event.number_of_heats
            self.current_event.heats[:] = (
                self.current_event.heats[-offset:] + self.current_event.heats[:-offset]
            )
            dialog.destroy()
            self._mark_event_dirty()
            self._refresh_event_views()
            self._validate_current_event()

        button_row = ttk.Frame(dialog)
        button_row.grid(row=1, column=0, columnspan=2, pady=8)
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(
            side=RIGHT, padx=4
        )
        ttk.Button(button_row, text="Apply", command=on_apply).pack(side=RIGHT, padx=4)

    def _update_assignment_dialog(self, event=None) -> None:
        if not self._ensure_event_loaded():
            return

        selection = self.worker_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Select a participant to update")
            return

        participant = self.worker_table_mapping.get(selection[0])
        if not participant:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Update assignment")
        dialog.grab_set()
        dialog.resizable(False, False)

        assignment_variable = tk.StringVar(value=participant.assignment or "worker")

        ttk.Label(dialog, text="Participant").grid(
            row=0, column=0, sticky=W, padx=8, pady=6
        )
        ttk.Label(dialog, text=participant.name).grid(
            row=0, column=1, sticky=W, padx=8, pady=6
        )

        ttk.Label(dialog, text="Role").grid(row=1, column=0, sticky=W, padx=8, pady=6)
        ttk.Combobox(
            dialog,
            textvariable=assignment_variable,
            values=ROLE_OPTIONS,
            state="readonly",
            width=20,
        ).grid(row=1, column=1, padx=8, pady=6)

        def on_apply() -> None:
            role = assignment_variable.get().strip().lower()
            if not role:
                return
            try:
                participant.set_assignment(
                    role, show_previous=True, manual_override=True
                )
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to update assignment: {exc}")
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

    def _validate_current_event(self) -> None:
        if not self.current_event:
            return
        try:
            is_valid = self.current_event.validate()
        except Exception as exc:
            messagebox.showerror("Error", f"Validation error: {exc}")
            return
        self._set_status("Validation passed" if is_valid else "Validation failed")

    def _assignment_dialog(
        self, use=True, member_id="", assignment=""
    ) -> tuple[bool, str, str] | None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Assignment")
        dialog.grab_set()
        dialog.resizable(False, False)

        use_variable = tk.BooleanVar(value=use)
        member_id_variable = tk.StringVar(value=member_id)
        assignment_variable = tk.StringVar(value=assignment)
        name_variable = tk.StringVar(value="")

        ttk.Checkbutton(dialog, text="Use", variable=use_variable).grid(
            row=0, column=0, sticky=W, padx=8, pady=6
        )

        ttk.Label(dialog, text="Member ID").grid(
            row=1, column=0, sticky=W, padx=8, pady=4
        )
        member_entry = ttk.Entry(dialog, textvariable=member_id_variable, width=32)
        member_entry.grid(row=1, column=1, padx=8, pady=4)

        ttk.Label(dialog, text="Name").grid(row=2, column=0, sticky=W, padx=8, pady=4)
        ttk.Entry(dialog, textvariable=name_variable, width=32, state="readonly").grid(
            row=2, column=1, padx=8, pady=4
        )

        ttk.Label(dialog, text="Assignment").grid(
            row=3, column=0, sticky=W, padx=8, pady=4
        )
        ttk.Combobox(
            dialog,
            textvariable=assignment_variable,
            values=ASSIGNMENT_OPTIONS,
            state="readonly",
            width=20,
        ).grid(row=3, column=1, padx=8, pady=4)

        def update_name(*_) -> None:
            lookup_id = member_id_variable.get().strip()
            name_variable.set(self.member_name_lookup.get(lookup_id, ""))

        member_id_variable.trace_add("write", update_name)
        update_name()

        result: dict[str, tuple[bool, str, str]] = {}

        def on_ok() -> None:
            member_value = member_id_variable.get().strip()
            assignment_value = assignment_variable.get().strip()
            if not member_value:
                messagebox.showwarning("Missing member ID", "Member ID is required")
                return
            if not assignment_value:
                messagebox.showwarning("Missing assignment", "Assignment is required")
                return
            result["data"] = (use_variable.get(), member_value, assignment_value)
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.grid(row=4, column=0, columnspan=2, pady=8)
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(
            side=RIGHT, padx=4
        )
        ttk.Button(button_row, text="OK", command=on_ok).pack(side=RIGHT, padx=4)

        dialog.wait_window()
        return result.get("data")

    def _add_assignment_row(self) -> None:
        data = self._assignment_dialog()
        if not data:
            return
        use_flag, member_id, assignment = data
        name = self.member_name_lookup.get(member_id, "")
        self._insert_assignment_row(use_flag, member_id, name, assignment)
        self._mark_config_dirty()

    def _modify_assignment_row(self) -> None:
        selected = self.assignments_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        current = self.assignments_tree.item(item_id)["values"]
        data = self._assignment_dialog(
            use=current[0] == "☑", member_id=current[1], assignment=current[3]
        )
        if not data:
            return
        use_flag, member_id, assignment = data
        name = self.member_name_lookup.get(member_id, "")
        self.assignments_tree.item(
            item_id,
            values=("☑" if use_flag else "☐", member_id, name, assignment),
        )
        self._refresh_assignment_styles()
        self._mark_config_dirty()

    def _remove_assignment_row(self) -> None:
        selected = self.assignments_tree.selection()
        for item in selected:
            self.assignments_tree.delete(item)
        if selected:
            self._mark_config_dirty()

    def _insert_assignment_row(
        self, use_flag: bool, member_id: str, name: str, assignment: str
    ) -> None:
        values = ("☑" if use_flag else "☐", member_id, name, assignment)
        self.assignments_tree.insert("", END, values=values)
        self._refresh_assignment_styles()

    def _toggle_assignment_use(self, event) -> None:
        item_id = self.assignments_tree.identify_row(event.y)
        if not item_id:
            return
        values = list(self.assignments_tree.item(item_id)["values"])
        values[0] = "☐" if values[0] == "☑" else "☑"
        self.assignments_tree.item(item_id, values=values)
        self._refresh_assignment_styles()
        self._mark_config_dirty()

    def _refresh_assignment_styles(self) -> None:
        for item in self.assignments_tree.get_children():
            values = self.assignments_tree.item(item)["values"]
            tag = "disabled" if values[0] == "☐" else ""
            self.assignments_tree.item(item, tags=(tag,))

    def _collect_assignments(self) -> dict[str, str]:
        assignments: dict[str, str] = {}
        for item in self.assignments_tree.get_children():
            use_flag, member_id, _, assignment = self.assignments_tree.item(item)[
                "values"
            ]
            if use_flag != "☑":
                continue
            assignment_value = str(assignment).strip()
            if assignment_value:
                assignments[str(member_id)] = assignment_value
        return assignments

    def _refresh_assignment_names(self) -> None:
        for item in self.assignments_tree.get_children():
            values = list(self.assignments_tree.item(item)["values"])
            member_id = str(values[1]).strip()
            values[2] = self.member_name_lookup.get(member_id, values[2])
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

    def _save_config_silently(self) -> bool:
        try:
            config_data = self._build_config_payload()
        except ValueError:
            return False

        try:
            with open(self.config_path, "w", encoding="utf-8") as file:
                yaml.safe_dump(config_data, file, sort_keys=False)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to save config: {exc}")
            return False

        self.config_dirty = False
        self._update_unsaved_indicator()
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
            self.unsaved_label.configure(text=message, bootstyle="warning")
        else:
            self.unsaved_label.configure(text="All changes saved", bootstyle="success")

    def _sanitize_event_name(self, name: str) -> str:
        return "-".join(name.split())

    def _append_log(self, text: str) -> None:
        self.log_text.insert(END, text)
        self.log_text.see(END)

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", END)

    def _set_status(self, text: str) -> None:
        self.status_variable.set(text)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    AutologicGUI().run()
