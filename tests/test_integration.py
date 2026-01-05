import csv
import shutil
import time
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

import autologic.app as app_module
import autologic.gui as gui_module
from autologic import utils
from autologic.gui import AutologicGUI


ALGORITHM_NAME = "randomize"
EVENT_NAME = "gui-integration-event"
INVALID_ASSIGNMENT = "invalid-role"
SEED = 1337
STATE_FILE_NAME = "gui_integration_state.yaml"


class MessageBoxRecorder:
    """Record messagebox calls for assertions."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.infos: list[tuple[str, str]] = []
        self.ask_yes_no: list[tuple[str, str]] = []
        self.ask_yes_no_response = True

    def showerror(self, title: str, message: str) -> None:
        """Store a showerror invocation."""
        self.errors.append((title, message))

    def showwarning(self, title: str, message: str) -> None:
        """Store a showwarning invocation."""
        self.warnings.append((title, message))

    def showinfo(self, title: str, message: str) -> None:
        """Store a showinfo invocation."""
        self.infos.append((title, message))

    def askyesno(self, title: str, message: str) -> bool:
        """Store an askyesno invocation and return the configured response."""
        self.ask_yes_no.append((title, message))
        return self.ask_yes_no_response

    def reset(self) -> None:
        """Clear recorded calls so each step can assert on fresh state."""
        self.errors.clear()
        self.warnings.clear()
        self.infos.clear()
        self.ask_yes_no.clear()


class FileDialogRecorder:
    """Provide deterministic responses for file selection dialogs."""

    def __init__(self) -> None:
        self.open_paths: list[Path] = []

    def askopenfilename(self, **_kwargs: object) -> str:
        """Return the next queued path or an empty string."""
        if self.open_paths:
            return str(self.open_paths.pop(0))
        return ""


def wait_for_generation(
    gui_controller: AutologicGUI, timeout_seconds: float = 30
) -> None:
    """Wait for GUI generation to finish so assertions see final state.

    Args:
        gui_controller: GUI controller instance to monitor.
        timeout_seconds: Maximum time to wait for generation completion.

    Raises:
        AssertionError: If generation does not finish in the allotted time.
    """
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout_seconds:
        gui_controller.root.update()
        if not gui_controller.is_generating:
            return
        time.sleep(0.01)
    raise AssertionError("generation did not finish within timeout")


def build_test_config(
    sample_config_path: Path, temporary_directory: Path, output_name: str
) -> tuple[Path, dict]:
    """Create a temporary config with absolute paths for GUI loading.

    Args:
        sample_config_path: Path to the sample YAML file.
        temporary_directory: Directory to write the temp config into.
        output_name: Event name to embed in the config.

    Returns:
        tuple[Path, dict]: Config path and the loaded config data.
    """
    config_data = yaml.safe_load(sample_config_path.read_text(encoding="utf-8")) or {}
    config_data["name"] = output_name
    config_data["algorithm"] = ALGORITHM_NAME
    config_data["axware_export_tsv"] = str(
        (sample_config_path.parent / config_data["axware_export_tsv"]).resolve()
    )
    config_data["member_attributes_csv"] = str(
        (sample_config_path.parent / config_data["member_attributes_csv"]).resolve()
    )

    config_path = temporary_directory / "gui-integration-config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8"
    )
    return config_path, config_data


def load_checked_in_member_ids(axware_export_path: Path) -> set[str]:
    """Collect checked-in member ids from the AXWare export.

    Args:
        axware_export_path: Path to the AXWare TSV export.

    Returns:
        set[str]: Member ids with check-in marked as YES.
    """
    checked_in_member_ids: set[str] = set()
    with axware_export_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, delimiter="\t")
        fieldnames = [name for name in (reader.fieldnames or []) if name]
        checkin_field = None
        for name in fieldnames:
            if str(name).strip().lower() == "checkin":
                checkin_field = name
                break
        for row in reader:
            if checkin_field:
                checkin_value = str(row.get(checkin_field, "")).strip().upper()
                if checkin_value != "YES":
                    continue
            member_id = str(row.get("Member #", "")).strip()
            if member_id:
                checked_in_member_ids.add(member_id)
    return checked_in_member_ids


def format_member_name_for_display(name: str) -> str:
    """Normalize member names to Last, First when possible.

    Args:
        name: Raw name string from the member CSV.

    Returns:
        str: Name formatted for display and sorting.
    """
    cleaned = str(name).strip()
    if not cleaned:
        return ""
    if "," in cleaned:
        return cleaned
    name_parts = cleaned.split()
    if len(name_parts) < 2:
        return cleaned
    last_name = name_parts[-1]
    first_name = " ".join(name_parts[:-1])
    return f"{last_name}, {first_name}"


def lookup_member_name(member_attributes_path: Path, member_id: str) -> str:
    """Resolve a member id to its display name.

    Args:
        member_attributes_path: Path to the member attributes CSV.
        member_id: Member id to find.

    Returns:
        str: Display name for the member id.
    """
    with member_attributes_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if str(row.get("id", "")).strip() == member_id:
                return format_member_name_for_display(row.get("name", ""))
    raise AssertionError("member id not found in member attributes")


def select_custom_assignment_member_id(
    gui_controller: AutologicGUI, checked_in_member_ids: set[str]
) -> str:
    """Pick a member id suitable for custom assignment updates.

    Args:
        gui_controller: GUI controller with member lookup data.
        checked_in_member_ids: Member ids with check-in confirmed.

    Returns:
        str: Selected member id.
    """
    existing_assignments = gui_controller._collect_assignments()
    for member_id in sorted(gui_controller.member_name_lookup.keys()):
        if member_id in existing_assignments:
            continue
        if member_id not in checked_in_member_ids:
            continue
        return member_id
    raise AssertionError("no checked-in member available for a new assignment")


def find_assignment_row(gui_controller: AutologicGUI, member_id: str) -> str:
    """Locate a custom assignment row by member id.

    Args:
        gui_controller: GUI controller instance to query.
        member_id: Member id to locate.

    Returns:
        str: Treeview item id.
    """
    for item_id in gui_controller.assignments_tree.get_children():
        if gui_controller._is_add_assignment_row(item_id):
            continue
        values = gui_controller.assignments_tree.item(item_id)["values"]
        if str(values[0]).strip() == member_id:
            return item_id
    raise AssertionError("assignment row not found")


def find_worker_row(gui_controller: AutologicGUI, participant_name: str) -> str:
    """Find the worker table row for a participant name.

    Args:
        gui_controller: GUI controller instance to query.
        participant_name: Participant display name.

    Returns:
        str: Treeview item id.
    """
    for item_id, participant in gui_controller.worker_table_mapping.items():
        if participant.name == participant_name:
            return item_id
    raise AssertionError("worker row not found")


def choose_assignment_break_target(gui_controller: AutologicGUI):
    """Select a participant whose assignment change should break validation.

    Args:
        gui_controller: GUI controller with a loaded event.

    Returns:
        tuple[object, str]: Participant instance and their current assignment.
    """
    event = gui_controller.current_event
    if not event:
        raise AssertionError("event is required for assignment selection")

    for heat in event.heats:
        counts = gui_controller._count_assignments(heat)
        role_minima = utils.roles_and_minima(
            number_of_stations=event.number_of_stations,
            number_of_novices=len(
                heat.compliment.get_participants_by_attribute("novice")
            ),
            novice_denominator=event.novice_denominator,
        )
        for role, minimum in role_minima.items():
            current_count = counts.get(role, 0)
            if current_count != minimum:
                continue
            for participant in heat.participants:
                if participant.special_assignment:
                    continue
                if participant.assignment == role:
                    return participant, role
    raise AssertionError("no participant found to break validation")


def select_class_move(gui_controller: AutologicGUI):
    """Pick a class move, preferring one that violates size or novice parity.

    Args:
        gui_controller: GUI controller with a loaded event.

    Returns:
        tuple[str, int, int, bool | None]: (class name, source heat, target heat, expected valid)
    """
    event = gui_controller.current_event
    if not event:
        raise AssertionError("event is required for class move selection")

    heat_sizes: dict[int, int] = {}
    heat_novice_counts: dict[int, int] = {}
    for heat in event.heats:
        heat_sizes[heat.number] = len(heat.participants)
        heat_novice_counts[heat.number] = len(
            heat.get_participants_by_attribute("novice")
        )

    for class_name in sorted(event.categories.keys(), key=str.lower):
        category = event.categories[class_name]
        source_heat = category.heat.number
        category_size = len(category.participants)
        category_novices = 0
        for participant in category.participants:
            if participant.novice:
                category_novices += 1
        for heat in event.heats:
            target_heat = heat.number
            if target_heat == source_heat:
                continue
            new_heat_sizes = dict(heat_sizes)
            new_heat_novices = dict(heat_novice_counts)
            new_heat_sizes[source_heat] -= category_size
            new_heat_sizes[target_heat] += category_size
            new_heat_novices[source_heat] -= category_novices
            new_heat_novices[target_heat] += category_novices

            invalid = False
            for heat_number, heat_size in new_heat_sizes.items():
                if abs(heat_size - event.mean_heat_size) > event.max_heat_size_delta:
                    invalid = True
                novice_count = new_heat_novices[heat_number]
                if (
                    abs(novice_count - event.mean_heat_novice_count)
                    > event.max_heat_novice_delta
                ):
                    invalid = True
            if invalid:
                return class_name, source_heat, target_heat, False

    class_names = sorted(event.categories.keys(), key=str.lower)
    if not class_names:
        raise AssertionError("no classes available for move")
    class_name = class_names[0]
    source_heat = event.categories[class_name].heat.number
    for heat in event.heats:
        if heat.number != source_heat:
            return class_name, source_heat, heat.number, None
    raise AssertionError("no alternate heat found for move")


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF for targeted assertions.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        str: Combined extracted text.
    """
    reader = PdfReader(str(pdf_path))
    text_chunks: list[str] = []
    for page in reader.pages:
        text_chunks.append(page.extract_text() or "")
    return "\n".join(text_chunks)


def clear_directory(directory: Path) -> None:
    """Remove all files and folders in the target directory.

    Args:
        directory: Directory to clear before running integration steps.
    """
    for child in directory.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def set_config_path(gui_controller: AutologicGUI, config_path: Path) -> None:
    """Update the GUI controller config path fields together.

    Args:
        gui_controller: GUI controller instance to mutate.
        config_path: New config path to apply.
    """
    gui_controller.config_path = config_path
    gui_controller.config_path_variable.set(str(config_path))


def create_draft_tsv(source_path: Path, output_path: Path) -> None:
    """Create a draft TSV without check-in data for draft-mode testing.

    Args:
        source_path: Path to the original AXWare TSV.
        output_path: Path to write the modified TSV.
    """
    with source_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, delimiter="\t")
        fieldnames = [
            name
            for name in (reader.fieldnames or [])
            if name and str(name).strip().lower() != "checkin"
        ]
        if not fieldnames:
            raise AssertionError("draft TSV requires at least one field")
        with output_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            for row in reader:
                cleaned_row = {key: row.get(key, "") for key in fieldnames}
                writer.writerow(cleaned_row)


def load_state(state_path: Path) -> dict:
    """Load the shared integration state if it exists."""
    if not state_path.exists():
        return {}
    return yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}


def save_state(state_path: Path, state: dict) -> None:
    """Persist the shared integration state to disk."""
    state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")


def create_gui_controller(monkeypatch):
    """Create a GUI controller with stubbed dialogs and deterministic seed."""
    messagebox_recorder = MessageBoxRecorder()
    filedialog_recorder = FileDialogRecorder()

    monkeypatch.setattr(gui_module, "messagebox", messagebox_recorder)
    monkeypatch.setattr(gui_module, "filedialog", filedialog_recorder)

    def seeded_load_event(**config_payload):
        """Inject a deterministic seed into GUI-driven generation."""
        return app_module.load_event(**config_payload, seed=SEED)

    monkeypatch.setattr(gui_module, "load_event", seeded_load_event)

    default_config_path = Path(gui_module.__file__).resolve().parent / "autologic.yaml"
    default_config_existed = default_config_path.exists()

    try:
        gui_controller = AutologicGUI()
    except gui_module.tk.TclError as exc:
        raise RuntimeError(
            "Tkinter/Tcl unavailable; install Python with Tcl/Tk support "
            f"to run GUI integration tests. Details: {exc}"
        ) from exc
    gui_controller.root.withdraw()
    gui_controller.root.update()

    def cleanup() -> None:
        """Destroy the Tk root and remove any auto-created config file."""
        gui_controller.root.destroy()
        if not default_config_existed and default_config_path.exists():
            default_config_path.unlink()

    return gui_controller, messagebox_recorder, filedialog_recorder, cleanup


@pytest.fixture(scope="module")
def integration_workspace(tmp_path_factory) -> Path:
    """Create a shared workspace for the ordered integration steps."""
    workspace = tmp_path_factory.mktemp("gui_integration")
    clear_directory(workspace)
    return workspace


@pytest.fixture(scope="module")
def state_path(integration_workspace: Path) -> Path:
    """Return the shared state file path for the ordered integration steps."""
    return integration_workspace / STATE_FILE_NAME


@pytest.mark.order(1)
def test_step01_load_config(integration_workspace: Path, state_path: Path, monkeypatch):
    """Load a config with invalid and valid branches and persist the path."""
    clear_directory(integration_workspace)
    sample_config_path = Path(__file__).resolve().parent / "sample_event_config.yaml"
    config_path, config_data = build_test_config(
        sample_config_path, integration_workspace, EVENT_NAME
    )

    gui_controller, messagebox_recorder, filedialog_recorder, cleanup = (
        create_gui_controller(monkeypatch)
    )
    try:
        # ensure missing configs surface errors
        filedialog_recorder.open_paths.append(integration_workspace / "missing.yaml")
        messagebox_recorder.reset()
        gui_controller._load_config_prompt()
        assert messagebox_recorder.errors

        # load a valid config and confirm status text
        gui_controller._load_config_from_path(config_path)
        assert gui_controller.event_name_variable.get() == EVENT_NAME
        assert Path(gui_controller.tsv_path_variable.get()) == Path(
            config_data["axware_export_tsv"]
        )
        assert Path(gui_controller.member_csv_path_variable.get()) == Path(
            config_data["member_attributes_csv"]
        )
        assert gui_controller.config_dirty is False
        assert gui_controller.unsaved_label.cget("text") == "All changes saved"
    finally:
        cleanup()

    save_state(
        state_path,
        {
            "config_path": str(config_path),
            "axware_export_tsv": config_data["axware_export_tsv"],
            "member_attributes_csv": config_data["member_attributes_csv"],
            "event_name": EVENT_NAME,
        },
    )


@pytest.mark.order(2)
def test_step02_change_params(state_path: Path, monkeypatch):
    """Change config parameters with invalid and valid edits."""
    state = load_state(state_path)
    assert state.get("config_path"), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])
    config_payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    updated_heat_parity = str(int(config_payload["heat_size_parity"]) + 1)

    gui_controller, _, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)
        assert gui_controller.unsaved_label.cget("text") == "All changes saved"

        # apply an invalid value to cover dirty tracking
        gui_controller.heats_variable.set("not-a-number")
        assert "config" in gui_controller.unsaved_label.cget("text")

        # restore valid inputs and adjust heat parity
        gui_controller.heats_variable.set(str(config_payload["number_of_heats"]))
        gui_controller.heat_parity_variable.set(updated_heat_parity)
        gui_controller.event_name_variable.set(EVENT_NAME)
        assert "config" in gui_controller.unsaved_label.cget("text")
    finally:
        cleanup()

    state["updated_heat_parity"] = updated_heat_parity
    save_state(state_path, state)


@pytest.mark.order(3)
def test_step03_add_custom_assignment(state_path: Path, monkeypatch):
    """Add custom assignments with invalid and valid branches."""
    state = load_state(state_path)
    assert state.get("config_path"), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])
    axware_export_path = Path(state["axware_export_tsv"])

    gui_controller, messagebox_recorder, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)

        # confirm assignments cannot be added without member data
        messagebox_recorder.reset()
        gui_controller.member_name_lookup.clear()
        gui_controller._add_assignment_row()
        assert messagebox_recorder.warnings

        # add a real custom assignment for a checked-in member
        gui_controller._load_member_names()
        checked_in_member_ids = load_checked_in_member_ids(axware_export_path)
        new_member_id = select_custom_assignment_member_id(
            gui_controller, checked_in_member_ids
        )
        new_member_name = gui_controller.member_name_lookup[new_member_id]
        gui_controller._insert_assignment_row(
            True, new_member_id, new_member_name, "special"
        )
        gui_controller._mark_config_dirty()
        assert "config" in gui_controller.unsaved_label.cget("text")
    finally:
        cleanup()

    state["new_member_id"] = new_member_id
    save_state(state_path, state)


@pytest.mark.order(4)
def test_step04_update_custom_assignment(state_path: Path, monkeypatch):
    """Update a custom assignment with invalid and valid values."""
    state = load_state(state_path)
    assert state.get(
        "new_member_id"
    ), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])
    new_member_id = state["new_member_id"]

    gui_controller, _, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)
        gui_controller._load_member_names()

        new_member_name = gui_controller.member_name_lookup[new_member_id]
        gui_controller._insert_assignment_row(
            True, new_member_id, new_member_name, "special"
        )
        assignment_row_id = find_assignment_row(gui_controller, new_member_id)

        # apply an invalid assignment value
        updated_values = list(
            gui_controller.assignments_tree.item(assignment_row_id)["values"]
        )
        updated_values[2] = INVALID_ASSIGNMENT
        gui_controller.assignments_tree.item(assignment_row_id, values=updated_values)
        gui_controller._mark_config_dirty()
        assert "config" in gui_controller.unsaved_label.cget("text")

        # restore a valid assignment value
        updated_values[2] = "special"
        gui_controller.assignments_tree.item(assignment_row_id, values=updated_values)
        gui_controller._mark_config_dirty()
    finally:
        cleanup()


@pytest.mark.order(5)
def test_step05_save_config(state_path: Path, monkeypatch):
    """Save the config with invalid and valid paths."""
    state = load_state(state_path)
    assert state.get(
        "new_member_id"
    ), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])
    new_member_id = state["new_member_id"]
    updated_heat_parity = state.get("updated_heat_parity")

    gui_controller, messagebox_recorder, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)
        gui_controller._load_member_names()

        new_member_name = gui_controller.member_name_lookup[new_member_id]
        gui_controller._insert_assignment_row(
            True, new_member_id, new_member_name, "special"
        )
        if updated_heat_parity:
            gui_controller.heat_parity_variable.set(updated_heat_parity)
        gui_controller._mark_config_dirty()
        assert "config" in gui_controller.unsaved_label.cget("text")

        # fail to save into a missing directory
        messagebox_recorder.reset()
        invalid_config_path = config_path.parent / "missing" / "config.yaml"
        set_config_path(gui_controller, invalid_config_path)
        assert gui_controller._save_config() is False
        assert messagebox_recorder.errors

        # save successfully
        messagebox_recorder.reset()
        set_config_path(gui_controller, config_path)
        assert gui_controller._save_config() is True
        assert gui_controller.unsaved_label.cget("text") == "All changes saved"
    finally:
        cleanup()

    saved_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if updated_heat_parity:
        assert saved_config["heat_size_parity"] == updated_heat_parity
    assert saved_config["custom_assignments"][new_member_id] == "special"


@pytest.mark.order(6)
def test_step06_generate_event(state_path: Path, monkeypatch):
    """Generate an event with invalid and valid configurations."""
    state = load_state(state_path)
    assert state.get("config_path"), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])

    gui_controller, messagebox_recorder, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)

        # invalid generation with non-numeric heats
        messagebox_recorder.reset()
        gui_controller.heats_variable.set("not-a-number")
        gui_controller._start_generation()
        wait_for_generation(gui_controller)
        assert messagebox_recorder.errors
        assert gui_controller.current_event is None

        # reload config to clear dirty state before a valid run
        gui_controller._load_config_from_path(config_path)

        messagebox_recorder.reset()
        gui_controller._start_generation()
        wait_for_generation(gui_controller)
        assert gui_controller.current_event is not None
        assert gui_controller.validation_status_variable.get() == "Validation: OK"
        assert gui_controller.unsaved_label.cget("text") == "Unsaved changes: event"
        assert messagebox_recorder.errors == []
    finally:
        cleanup()


@pytest.mark.order(7)
def test_step07_move_class_and_validate(state_path: Path, monkeypatch):
    """Move a class between heats and validate the result."""
    state = load_state(state_path)
    assert state.get("config_path"), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])

    gui_controller, _, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)
        gui_controller._start_generation()
        wait_for_generation(gui_controller)

        class_name, source_heat, target_heat, expected_valid = select_class_move(
            gui_controller
        )
        category = gui_controller.current_event.categories[class_name]
        category.set_heat(
            gui_controller.current_event.get_heat(target_heat), verbose=True
        )
        gui_controller._mark_event_dirty()
        gui_controller._refresh_event_views()
        gui_controller._validate_current_event()

        validation_state = gui_controller._evaluate_event_validity()
        event_is_valid = validation_state["event_is_valid"]
        if expected_valid is not None:
            assert event_is_valid is expected_valid

        expected_status = "Validation: OK" if event_is_valid else "Validation: INVALID"
        expected_message = (
            "Validation passed" if event_is_valid else "Validation failed"
        )
        assert gui_controller.validation_status_variable.get() == expected_status
        assert gui_controller.status_variable.get() == expected_message

        # restore the original class placement
        category.set_heat(
            gui_controller.current_event.get_heat(source_heat), verbose=True
        )
        gui_controller._mark_event_dirty()
        gui_controller._refresh_event_views()
        gui_controller._validate_current_event()
        assert gui_controller.validation_status_variable.get() == "Validation: OK"
    finally:
        cleanup()


@pytest.mark.order(8)
def test_step08_rotate_run_work(state_path: Path, monkeypatch):
    """Rotate run/work groups with invalid and valid branches."""
    state = load_state(state_path)
    assert state.get("config_path"), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])

    gui_controller, messagebox_recorder, _, cleanup = create_gui_controller(monkeypatch)
    try:
        # confirm rotation warns when no event exists
        messagebox_recorder.reset()
        gui_controller._rotate_run_work()
        assert messagebox_recorder.warnings

        gui_controller._load_config_from_path(config_path)
        gui_controller._start_generation()
        wait_for_generation(gui_controller)

        original_run_groups = {}
        for participant in gui_controller.current_event.participants:
            original_run_groups[participant.id] = participant.heat.running

        gui_controller._rotate_run_work()

        rotated_run_groups = {}
        for participant in gui_controller.current_event.participants:
            rotated_run_groups[participant.id] = participant.heat.running

        assert original_run_groups != rotated_run_groups
    finally:
        cleanup()


@pytest.mark.order(9)
def test_step09_update_worker_assignment(state_path: Path, monkeypatch):
    """Update worker assignments and confirm validation reactions."""
    state = load_state(state_path)
    assert state.get("config_path"), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])

    gui_controller, _, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)
        gui_controller._start_generation()
        wait_for_generation(gui_controller)

        participant, original_assignment = choose_assignment_break_target(
            gui_controller
        )
        participant.set_assignment(
            "worker", verbose=False, show_previous=True, manual_override=True
        )
        gui_controller._mark_event_dirty()
        gui_controller._refresh_event_views()
        gui_controller._validate_current_event()
        assert gui_controller.validation_status_variable.get() == "Validation: INVALID"
        assert gui_controller.status_variable.get() == "Validation failed"

        participant.set_assignment(
            original_assignment, verbose=False, show_previous=True, manual_override=True
        )
        gui_controller._mark_event_dirty()
        gui_controller._refresh_event_views()
        gui_controller._validate_current_event()
        assert gui_controller.validation_status_variable.get() == "Validation: OK"

        worker_row_id = find_worker_row(gui_controller, participant.name)
        assert (
            gui_controller.worker_tree.set(worker_row_id, "assignment")
            == original_assignment
        )
    finally:
        cleanup()


@pytest.mark.order(10)
def test_step10_save_event(state_path: Path, monkeypatch):
    """Save the event with invalid name and overwrite prompts."""
    state = load_state(state_path)
    assert state.get("config_path"), "state file missing; run ordered integration steps"

    config_path = Path(state["config_path"])

    gui_controller, messagebox_recorder, _, cleanup = create_gui_controller(monkeypatch)
    try:
        gui_controller._load_config_from_path(config_path)
        gui_controller._start_generation()
        wait_for_generation(gui_controller)

        # refuse to save with a missing event name
        messagebox_recorder.reset()
        gui_controller.event_name_variable.set("")
        gui_controller._save_event()
        assert messagebox_recorder.warnings

        gui_controller.event_name_variable.set(EVENT_NAME)
        output_directory = config_path.parent
        csv_path = output_directory / f"{EVENT_NAME}.csv"
        pdf_path = output_directory / f"{EVENT_NAME}.pdf"
        pickle_path = output_directory / f"{EVENT_NAME}.pkl"

        csv_path.write_text("dummy", encoding="utf-8")
        pdf_path.write_bytes(b"dummy")
        pickle_path.write_bytes(b"dummy")

        # decline overwrite and confirm files remain unchanged
        messagebox_recorder.reset()
        messagebox_recorder.ask_yes_no_response = False
        gui_controller._save_event()
        assert messagebox_recorder.ask_yes_no
        assert csv_path.read_text(encoding="utf-8") == "dummy"
        assert pdf_path.read_bytes() == b"dummy"
        assert pickle_path.read_bytes() == b"dummy"

        # accept overwrite and confirm outputs are regenerated
        messagebox_recorder.reset()
        messagebox_recorder.ask_yes_no_response = True
        gui_controller._save_event()
        assert gui_controller.unsaved_label.cget("text") == "All changes saved"
        assert csv_path.exists()
        assert pdf_path.exists()
        assert pickle_path.exists()
        assert csv_path.read_text(encoding="utf-8") != "dummy"
        assert pdf_path.read_bytes() != b"dummy"
        assert pickle_path.read_bytes() != b"dummy"
    finally:
        cleanup()

    state["csv_path"] = str(csv_path)
    state["pdf_path"] = str(pdf_path)
    state["pickle_path"] = str(pickle_path)
    save_state(state_path, state)


@pytest.mark.order(11)
def test_step11_inspect_outputs(state_path: Path):
    """Inspect CSV and PDF outputs for targeted accuracy checks."""
    state = load_state(state_path)
    assert state.get("csv_path"), "state file missing; run ordered integration steps"

    csv_path = Path(state["csv_path"])
    pdf_path = Path(state["pdf_path"])
    member_attributes_path = Path(state["member_attributes_csv"])
    new_member_id = state.get("new_member_id")
    assert new_member_id, "state file missing; run ordered integration steps"

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        rows = list(reader)

    assert header == [
        "heat",
        "name",
        "class",
        "number",
        "assignment",
        "checked_in",
    ]
    assert rows

    custom_participant_name = lookup_member_name(member_attributes_path, new_member_id)

    def find_csv_row(name: str):
        for row in rows:
            if row[1] == name:
                return row
        return None

    added_assignment_row = find_csv_row(custom_participant_name)
    assert added_assignment_row is not None
    assert added_assignment_row[4] == "special"

    pdf_text = extract_pdf_text(pdf_path).upper()
    assert EVENT_NAME.upper() in pdf_text
    assert "WORKER TRACKING" in pdf_text
    assert "GRID TRACKING" in pdf_text
    assert custom_participant_name.upper() in pdf_text


@pytest.mark.order(12)
def test_step12_load_pickle(state_path: Path, monkeypatch):
    """Load the saved event pickle with invalid and valid branches."""
    state = load_state(state_path)
    assert state.get("pickle_path"), "state file missing; run ordered integration steps"

    pickle_path = Path(state["pickle_path"])
    config_path = Path(state["config_path"])
    updated_heat_parity = state.get("updated_heat_parity")
    new_member_id = state.get("new_member_id")

    gui_controller, messagebox_recorder, filedialog_recorder, cleanup = (
        create_gui_controller(monkeypatch)
    )
    try:
        gui_controller._load_config_from_path(config_path)

        # invalid pickle load should surface an error
        messagebox_recorder.reset()
        filedialog_recorder.open_paths.append(pickle_path.parent / "missing.pkl")
        gui_controller._load_event_prompt()
        assert messagebox_recorder.errors

        # valid pickle load should restore state
        messagebox_recorder.reset()
        filedialog_recorder.open_paths.append(pickle_path)
        gui_controller._load_event_prompt()
        assert gui_controller.current_event is not None
        assert gui_controller.event_name_variable.get() == EVENT_NAME
        if updated_heat_parity:
            assert gui_controller.heat_parity_variable.get() == updated_heat_parity
        assert gui_controller.config_dirty is False
        assert gui_controller.event_dirty is False
        assert gui_controller.validation_status_variable.get() == "Validation: OK"

        loaded_assignments = gui_controller._collect_assignments()
        if new_member_id:
            assert loaded_assignments[new_member_id] == "special"

        assert gui_controller.current_event.validate() is True
    finally:
        cleanup()


@pytest.mark.order(13)
def test_step13_draft_mode_blocks_save(
    integration_workspace: Path, state_path: Path, monkeypatch
):
    """Confirm draft mode disables Save Event when check-in data is missing."""
    state = load_state(state_path)
    assert state.get(
        "axware_export_tsv"
    ), "state file missing; run ordered integration steps"

    original_tsv = Path(state["axware_export_tsv"])
    draft_tsv = integration_workspace / "draft_axware_export.tsv"
    create_draft_tsv(original_tsv, draft_tsv)

    sample_config_path = Path(__file__).resolve().parent / "sample_event_config.yaml"
    config_path, config_data = build_test_config(
        sample_config_path, integration_workspace, "draft-event"
    )
    config_data["axware_export_tsv"] = str(draft_tsv)
    config_path.write_text(
        yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8"
    )

    gui_controller, messagebox_recorder, _, cleanup = create_gui_controller(monkeypatch)
    try:
        messagebox_recorder.reset()
        gui_controller._load_config_from_path(config_path)
        assert messagebox_recorder.infos

        gui_controller._start_generation()
        wait_for_generation(gui_controller)
        assert gui_controller.current_event is not None
        assert gui_controller.current_event.draft_mode is True
        assert str(gui_controller.save_event_button["state"]) == "disabled"
        assert "DRAFT" in gui_controller.unsaved_label.cget("text")
    finally:
        cleanup()
