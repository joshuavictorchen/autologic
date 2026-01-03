import pickle
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import yaml

import autologic
from event import Event
from algorithms import get_algorithms
from cli import Config


class AutologicGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Autologic")
        self.algorithms = {k: v for k, v in get_algorithms().items() if k != "example"}
        self.current_event: Event | None = None
        self.status_var = tk.StringVar(value="Ready")
        self.default_algo = (
            "randomize"
            if "randomize" in self.algorithms
            else next(iter(self.algorithms))
        )

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TButton", padding=6)
        style.configure("TLabelframe", padding=6)
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=24)

        self._build_layout()

    def _build_layout(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.new_event_tab = ttk.Frame(notebook)
        self.load_event_tab = ttk.Frame(notebook)
        notebook.add(self.new_event_tab, text="New Event")
        notebook.add(self.load_event_tab, text="Load Event")

        self._build_new_event_tab()
        self._build_load_event_tab()

        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_new_event_tab(self):
        frame = self.new_event_tab

        config_frame = ttk.LabelFrame(frame, text="Event configuration")
        config_frame.pack(fill=tk.X, padx=10, pady=10)

        config_actions = ttk.Frame(config_frame)
        config_actions.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 6))
        ttk.Button(
            config_actions, text="Load config", command=self._load_config_file
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            config_actions, text="Save config", command=self._save_config_file
        ).pack(side=tk.LEFT, padx=5)

        self.event_name_var = tk.StringVar(value="autologic-event")
        self.heats_var = tk.IntVar(value=3)
        self.stations_var = tk.IntVar(value=5)
        self.heat_parity_var = tk.IntVar(value=25)
        self.novice_parity_var = tk.IntVar(value=10)
        self.novice_denominator_var = tk.IntVar(value=3)
        self.max_iterations_var = tk.IntVar(value=10000)
        self.algorithm_var = tk.StringVar(value=self.default_algo)
        self.tsv_path_var = tk.StringVar()
        self.member_csv_path_var = tk.StringVar()

        self._add_labeled_entry(config_frame, "Event name", self.event_name_var, 1, 0)
        self._add_labeled_entry(config_frame, "Heats", self.heats_var, 1, 1, width=8)
        self._add_labeled_entry(
            config_frame, "Stations", self.stations_var, 1, 2, width=8
        )
        self._add_labeled_entry(
            config_frame, "Heat parity", self.heat_parity_var, 2, 0, width=8
        )
        self._add_labeled_entry(
            config_frame, "Novice parity", self.novice_parity_var, 2, 1, width=8
        )
        self._add_labeled_entry(
            config_frame,
            "Novice denominator",
            self.novice_denominator_var,
            2,
            2,
            width=12,
        )
        self._add_labeled_entry(
            config_frame, "Max iterations", self.max_iterations_var, 3, 0, width=12
        )

        file_frame = ttk.Frame(config_frame)
        file_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        self._add_file_picker(
            file_frame,
            "AXWare TSV",
            self.tsv_path_var,
            0,
            lambda: self._browse_file(self.tsv_path_var),
        )
        self._add_file_picker(
            file_frame,
            "Member attributes CSV",
            self.member_csv_path_var,
            1,
            lambda: self._browse_file(self.member_csv_path_var),
        )

        algo_frame = ttk.Frame(config_frame)
        algo_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Label(algo_frame, text="Algorithm").grid(row=0, column=0, sticky="w")
        ttk.OptionMenu(
            algo_frame,
            self.algorithm_var,
            self.algorithm_var.get(),
            *self.algorithms.keys(),
        ).grid(row=0, column=1, sticky="w")

        assignment_frame = ttk.LabelFrame(frame, text="Custom assignments")
        assignment_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        self.assignments_tree = ttk.Treeview(
            assignment_frame,
            columns=("use", "member_id", "name", "assignment"),
            show="headings",
            height=6,
        )
        self.assignments_tree.heading("use", text="Use")
        self.assignments_tree.heading("member_id", text="Member ID")
        self.assignments_tree.heading("name", text="Name")
        self.assignments_tree.heading("assignment", text="Assignment(s)")
        self.assignments_tree.column("use", width=50, anchor="center")
        self.assignments_tree.column("member_id", width=140, anchor="w")
        self.assignments_tree.column("name", width=160, anchor="w")
        self.assignments_tree.column("assignment", width=200, anchor="w")
        self.assignments_tree.tag_configure("disabled", foreground="#888888")
        self.assignments_tree.bind("<Double-1>", self._toggle_use_on_click)
        self.assignments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        assignment_buttons = ttk.Frame(assignment_frame)
        assignment_buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        ttk.Button(
            assignment_buttons, text="Add", command=self._add_assignment_row
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            assignment_buttons, text="Modify", command=self._modify_assignment_row
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            assignment_buttons, text="Remove", command=self._remove_assignment_row
        ).pack(fill=tk.X, pady=2)

        config_actions = ttk.Frame(frame)
        config_actions.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(
            config_actions, text="Generate outputs", command=self._run_generation
        ).pack(side=tk.RIGHT, padx=5)

        status_frame = ttk.LabelFrame(frame, text="Run status")
        status_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        self.status_text = tk.Text(status_frame, height=12, wrap="word")
        self.status_text.pack(fill=tk.BOTH, expand=True)

    def _build_load_event_tab(self):
        frame = self.load_event_tab

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.pkl_path_var = tk.StringVar()
        self._add_file_picker(
            top_frame,
            "Load event pickle",
            self.pkl_path_var,
            0,
            lambda: self._browse_file(
                self.pkl_path_var, filetypes=[("Pickle", "*.pkl"), ("All files", "*.*")]
            ),
        )
        ttk.Button(top_frame, text="Load", command=self._load_pickle).grid(
            row=0, column=2, padx=5
        )

        actions_frame = ttk.LabelFrame(frame, text="Actions")
        actions_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            actions_frame, text="Move class", command=self._move_category_dialog
        ).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(
            actions_frame, text="Rotate run/work", command=self._rotate_heats_dialog
        ).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        ttk.Button(
            actions_frame,
            text="Update assignment",
            command=self._update_assignment_dialog,
        ).grid(row=0, column=2, padx=5, pady=2, sticky="w")
        ttk.Button(actions_frame, text="Validate", command=self._validate_event).grid(
            row=0, column=3, padx=5, pady=2, sticky="w"
        )
        ttk.Button(
            actions_frame, text="Export", command=self._export_event_dialog
        ).grid(row=0, column=4, padx=5, pady=2, sticky="w")

        summary_frame = ttk.LabelFrame(frame, text="Event summary")
        summary_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        self.summary_text = tk.Text(summary_frame, height=12, wrap="word")
        self.summary_text.pack(fill=tk.BOTH, expand=True)

    def _add_labeled_entry(self, parent, label, variable, row, column, width=20):
        ttk.Label(parent, text=label).grid(
            row=row, column=column * 2, sticky="w", padx=5, pady=3
        )
        ttk.Entry(parent, textvariable=variable, width=width).grid(
            row=row, column=column * 2 + 1, sticky="w", padx=5, pady=3
        )

    def _add_file_picker(self, parent, label, variable, row, browse_command):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Entry(parent, textvariable=variable, width=60).grid(
            row=row, column=1, sticky="w", padx=5, pady=3
        )
        ttk.Button(parent, text="Browse", command=browse_command).grid(
            row=row, column=2, sticky="w", padx=5, pady=3
        )

    def _browse_file(self, target_var, filetypes=None):
        opts = {}
        if filetypes:
            opts["filetypes"] = filetypes
        file_path = filedialog.askopenfilename(**opts)
        if file_path:
            target_var.set(file_path)

    def _insert_assignment_row(self, use_flag, member_id, name, assignment_str):
        values = ("☑" if use_flag else "☐", member_id, name, assignment_str)
        self.assignments_tree.insert("", tk.END, values=values)
        self._refresh_assignment_styles()

    def _assignment_dialog(self, use=True, member_id="", name="", assignment=""):
        dialog = tk.Toplevel(self.root)
        dialog.title("Assignment")
        dialog.grab_set()
        dialog.resizable(False, False)

        use_var = tk.BooleanVar(value=use)
        member_var = tk.StringVar(value=member_id)
        name_var = tk.StringVar(value=name)
        assignment_var = tk.StringVar(value=assignment)

        ttk.Checkbutton(dialog, text="Use", variable=use_var).grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )

        ttk.Label(dialog, text="Member ID").grid(
            row=1, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Entry(dialog, textvariable=member_var, width=40).grid(
            row=1, column=1, padx=8, pady=4
        )

        ttk.Label(dialog, text="Name").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(dialog, textvariable=name_var, width=40).grid(
            row=2, column=1, padx=8, pady=4
        )

        ttk.Label(dialog, text="Assignment(s)").grid(
            row=3, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Entry(dialog, textvariable=assignment_var, width=40).grid(
            row=3, column=1, padx=8, pady=4
        )
        ttk.Label(dialog, text="comma-separated (e.g., instructor, captain)").grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4)
        )

        result = {}

        def on_ok():
            if not member_var.get().strip():
                messagebox.showwarning("Missing member ID", "Member ID is required")
                return
            result["data"] = (
                use_var.get(),
                member_var.get().strip(),
                name_var.get().strip(),
                assignment_var.get().strip(),
            )
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.grid(row=5, column=0, columnspan=2, pady=8)
        ttk.Button(button_row, text="Cancel", command=on_cancel).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(button_row, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=4)

        dialog.wait_window()
        return result.get("data")

    def _toggle_use_on_click(self, event):
        item_id = self.assignments_tree.identify_row(event.y)
        if not item_id:
            return
        values = list(self.assignments_tree.item(item_id)["values"])
        values[0] = "☐" if values[0] == "☑" else "☑"
        self.assignments_tree.item(item_id, values=values)
        self._refresh_assignment_styles()

    def _refresh_assignment_styles(self):
        for item in self.assignments_tree.get_children():
            values = self.assignments_tree.item(item)["values"]
            tag = "disabled" if values[0] == "☐" else ""
            self.assignments_tree.item(item, tags=(tag,))

    def _add_assignment_row(self):
        data = self._assignment_dialog()
        if not data:
            return
        use_flag, member_id, name, assignment_str = data
        self._insert_assignment_row(use_flag, member_id, name, assignment_str)

    def _modify_assignment_row(self):
        selected = self.assignments_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        current = self.assignments_tree.item(item_id)["values"]
        data = self._assignment_dialog(
            use=current[0] == "☑",
            member_id=current[1],
            name=current[2],
            assignment=current[3],
        )
        if not data:
            return
        use_flag, member_id, name, assignment_str = data
        self.assignments_tree.item(
            item_id,
            values=("☑" if use_flag else "☐", member_id, name, assignment_str),
        )
        self._refresh_assignment_styles()

    def _remove_assignment_row(self):
        selected = self.assignments_tree.selection()
        for item in selected:
            self.assignments_tree.delete(item)

    def _collect_assignments(self):
        assignments = {}
        for item in self.assignments_tree.get_children():
            use_flag, member_id, _, assignment = self.assignments_tree.item(item)[
                "values"
            ]
            if use_flag != "☑":
                continue
            tokens = [t.strip() for t in str(assignment).split(",") if t.strip()]
            if len(tokens) > 1:
                assignments[member_id] = tokens
            elif tokens:
                assignments[member_id] = tokens[0]
        return assignments

    def _load_config_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            config = Config(**data)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load config: {exc}")
            return

        self.event_name_var.set(config.name)
        self.tsv_path_var.set(str(config.axware_export_tsv))
        self.member_csv_path_var.set(str(config.member_attributes_csv))
        self.heats_var.set(config.number_of_heats)
        self.stations_var.set(config.number_of_stations)
        self.heat_parity_var.set(config.heat_size_parity)
        self.novice_parity_var.set(config.novice_size_parity)
        self.novice_denominator_var.set(config.novice_denominator)
        self.max_iterations_var.set(config.max_iterations)

        for item in self.assignments_tree.get_children():
            self.assignments_tree.delete(item)
        for key, value in config.custom_assignments.items():
            assignment_str = ", ".join(value) if isinstance(value, list) else str(value)
            self._insert_assignment_row(True, key, "", assignment_str)
        self._set_status(f"Loaded config from {path}")

    def _save_config_file(self):
        config = self._build_config_dict()
        path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML", "*.yaml"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w") as f:
                yaml.safe_dump(config, f)
            self._set_status(f"Saved config to {path}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save config: {exc}")

    def _build_config_dict(self):
        return {
            "name": self.event_name_var.get(),
            "axware_export_tsv": self.tsv_path_var.get(),
            "member_attributes_csv": self.member_csv_path_var.get(),
            "number_of_heats": self.heats_var.get(),
            "number_of_stations": self.stations_var.get(),
            "custom_assignments": self._collect_assignments(),
            "heat_size_parity": self.heat_parity_var.get(),
            "novice_size_parity": self.novice_parity_var.get(),
            "novice_denominator": self.novice_denominator_var.get(),
            "max_iterations": self.max_iterations_var.get(),
        }

    def _run_generation(self):
        self.status_text.delete("1.0", tk.END)
        config_data = self._build_config_dict()
        algorithm = self.algorithm_var.get()
        try:
            config = Config(**config_data)
            config.validate_paths()
        except Exception as exc:
            messagebox.showerror("Error", f"Invalid configuration: {exc}")
            return

        def observer(event_type, payload):
            self._append_status(f"{event_type}: {payload}")
            self.root.update_idletasks()

        try:
            event = autologic.load_event(**config.model_dump())
            autologic.main(
                algorithm=algorithm, event=event, interactive=False, observer=observer
            )
            self._set_status("Generation completed")
            self._append_status("Generation completed successfully")
        except Exception as exc:
            messagebox.showerror("Error", f"Generation failed: {exc}")
            self._set_status("Generation failed")

    def _append_status(self, text):
        self.status_text.insert(tk.END, f"{text}\n")
        self.status_text.see(tk.END)

    def _load_pickle(self):
        path = self.pkl_path_var.get()
        if not path:
            picked = filedialog.askopenfilename(
                filetypes=[("Pickle", "*.pkl"), ("All files", "*.*")]
            )
            if not picked:
                return
            path = picked
            self.pkl_path_var.set(path)
        try:
            with open(path, "rb") as f:
                self.current_event = pickle.load(f)
            self._set_status(f"Loaded event {self.current_event.name}")
            self._refresh_summary()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load pickle: {exc}")

    def _move_category_dialog(self):
        if not self._ensure_event_loaded():
            return
        categories = list(self.current_event.categories.keys())
        heats = [str(h.number) for h in self.current_event.heats]
        category = simpledialog.askstring(
            "Move class", f"Choose class from: {', '.join(categories)}"
        )
        if not category or category.upper() not in categories:
            return
        heat = simpledialog.askstring(
            "Assign to heat", f"Choose heat from: {', '.join(heats)}"
        )
        if not heat:
            return
        try:
            self.current_event.categories[category.upper()].set_heat(
                self.current_event.get_heat(int(heat)), verbose=True
            )
            self._refresh_summary()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to move class: {exc}")

    def _rotate_heats_dialog(self):
        if not self._ensure_event_loaded():
            return
        offset_str = simpledialog.askstring("Rotate run/work", "Enter offset:")
        if not offset_str or not offset_str.isdigit():
            return
        offset = int(offset_str) % self.current_event.number_of_heats
        self.current_event.heats[:] = (
            self.current_event.heats[-offset:] + self.current_event.heats[:-offset]
        )
        self._refresh_summary()

    def _update_assignment_dialog(self):
        if not self._ensure_event_loaded():
            return
        participant_names = [p.name for p in self.current_event.participants]
        participant = simpledialog.askstring(
            "Update assignment",
            f"Choose participant from: {', '.join(participant_names)}",
        )
        if not participant:
            return
        role = simpledialog.askstring(
            "Role",
            "Choose role (special, instructor, timing, grid, start, captain, worker):",
        )
        if not role:
            return
        try:
            self.current_event.get_participant_by_name(participant).set_assignment(
                role.lower(), show_previous=True, manual_override=True
            )
            self._refresh_summary()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to update assignment: {exc}")

    def _validate_event(self):
        if not self._ensure_event_loaded():
            return
        try:
            valid = self.current_event.validate()
            self._refresh_summary()
            message = "Validation passed" if valid else "Validation failed"
            self._set_status(message)
        except Exception as exc:
            messagebox.showerror("Error", f"Validation error: {exc}")

    def _export_event_dialog(self):
        if not self._ensure_event_loaded():
            return
        new_name = simpledialog.askstring("Export", "Save event as:")
        if not new_name:
            return
        self.current_event.name = new_name
        try:
            self.current_event.to_csv()
            self.current_event.to_pdf()
            self.current_event.to_pickle()
            self._set_status(f"Exported as {new_name}")
        except Exception as exc:
            messagebox.showerror("Error", f"Export failed: {exc}")

    def _refresh_summary(self):
        if not self.current_event:
            return
        self.summary_text.delete("1.0", tk.END)
        for heat in self.current_event.heats:
            header = (
                f"Heat {heat.number} | Running {heat.running} | Working {heat.working}"
            )
            categories = ", ".join(sorted([c.name for c in heat.categories]))
            assignments = {
                role: len(heat.get_participants_by_attribute("assignment", role))
                for role in [
                    "instructor",
                    "timing",
                    "grid",
                    "start",
                    "captain",
                    "worker",
                    "special",
                ]
            }
            novice_count = len(heat.get_participants_by_attribute("novice"))
            self.summary_text.insert(tk.END, f"{header}\n")
            self.summary_text.insert(tk.END, f"  Classes: {categories}\n")
            self.summary_text.insert(
                tk.END,
                f"  Roles: {assignments} | Total {len(heat.participants)} ({novice_count} novices)\n\n",
            )
        self.summary_text.see(tk.END)

    def _ensure_event_loaded(self):
        if not self.current_event:
            messagebox.showwarning("No event", "Load an event pickle first")
            return False
        return True

    def _set_status(self, text):
        self.status_var.set(text)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AutologicGUI().run()
