Last updated: 2026-02-26

# Autologic — Code Map

## Overview

Autologic is a desktop application for autocross event coordination. It reads participant data from AXWare TSV exports and member-qualification CSVs, assigns participants to heats (run/work time slots) and worker roles via a pluggable algorithm system, validates the result against configurable constraints, and produces printable PDF artifacts. The GUI is built on ttkbootstrap (themed Tkinter). Architecture is a single-package monolith with a plugin system for heat-generation algorithms.

## Directory Structure

```text
autologic/
├── algorithms/            # pluggable heat-generation algorithm system
│   ├── _base.py           # HeatGenerator ABC + observer pattern
│   ├── _registry.py       # auto-discovery and registration of algorithm modules
│   ├── example.py         # scaffold / template algorithm
│   └── randomize.py       # production algorithm (brute-force randomize-and-check)
├── app.py                 # orchestration: load_event() factory + main() runner
├── category.py            # Category model (car class grouping)
├── config.py              # pydantic Config model + path resolution
├── event.py               # Event model (root domain object, validation, export)
├── group.py               # Group base class for participant collections
├── gui.py                 # monolithic ttkbootstrap GUI (~2700 lines)
├── heat.py                # Heat model (time slot, derived participants)
├── participant.py         # Participant model (role qualification + assignment)
├── pdf.py                 # PDF generation via reportlab
├── utils.py               # role definitions, sort helpers, normalization
└── hook-algorithms.py     # PyInstaller hidden-imports hook
docs/
├── images/                # icon, screenshots, demo gif
scripts/
└── msr_export_attribute_mapper.py  # CLI tool: MSR export -> member attributes CSV
tests/
├── sample_axware_export.tsv        # 128 participants (125 checked-in, 3 no-shows)
├── sample_event_config.yaml        # reference config
├── sample_member_attributes.csv    # 172 members with role qualifications
└── test_integration.py             # ordered integration test suite (~1150 lines)
```

## Top-Level Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, dependencies, build config |
| `requirements.in` / `requirements.txt` | Pinned runtime dependencies |
| `requirements-dev.in` | Dev/test dependencies |
| `codecov.yml` | Coverage reporting config |
| `.github/workflows/pipeline.yml` | CI: lint (black) → build (PyInstaller) → test (pytest) → release |

## Key Entry Points

- `autologic/gui.py` — GUI entry point (`if __name__ == "__main__": AutologicGUI().run()`)
- `autologic/app.py` — headless orchestration (`load_event()` + `main()`)
- `autologic/algorithms/randomize.py` — production algorithm; start here to understand heat generation
- `autologic/event.py` — root domain model; start here to understand the data model

## Component Boundaries

### Group (`group.py`)

- **Owns**: base collection behavior for participant containers
- **Key files**: `group.py`
- **Interface**: `participants`, `total`, `get_participants_by_attribute()`, `get_available(role)`, `get_participant_by_id()`, `get_participant_by_name()`
- **Depends on**: nothing
- **Depended on by**: Event, Heat, Category (all inherit from Group)

### Participant (`participant.py`)

- **Owns**: individual participant state — identity, qualifications, assignment
- **Key files**: `participant.py`
- **Interface**: `set_assignment()`, `category` (property), `heat` (property), `has_sole_role` (property)
- **Depends on**: Event (back-reference), utils
- **Depended on by**: Category, Heat, Event, algorithms
- **Invariants**: a participant with a `special_assignment` can only be assigned that specific role; assignment requires qualification (role attribute = True) unless role is "worker"

### Category (`category.py`)

- **Owns**: grouping participants by car class; heat membership
- **Key files**: `category.py`
- **Interface**: `add_participant()`, `set_heat(heat)`, `heat` attribute
- **Depends on**: Group, Participant
- **Depended on by**: Event, Heat (derives participants from categories)
- **Invariants**: a category belongs to exactly one heat; all participants in a category share the same heat

### Heat (`heat.py`)

- **Owns**: time-slot representation, participant derivation, per-heat validation
- **Key files**: `heat.py`
- **Interface**: `participants` (property, derived from categories), `valid_size`, `valid_novice_count`, `valid_role_fulfillment`, `working` (property), `complement` (property)
- **Depends on**: Group, Event (back-reference), utils
- **Depended on by**: Event, algorithms, GUI
- **Invariants**: heat does not store participants directly — derives them from assigned categories; `working` maps running heat number to work-group number based on heat count

### Event (`event.py`)

- **Owns**: root domain object — composes participants, categories, heats; validation; export
- **Key files**: `event.py`
- **Interface**: `validate()`, `to_csv()`, `to_pdf()`, `to_pickle()`, `get_work_assignments()`, `get_run_assignments()`, `get_heat_assignments()`
- **Depends on**: Group, Category, Heat, Participant, pdf, utils
- **Depended on by**: app, algorithms, GUI
- **Invariants**: `check_role_minima()` runs at construction — fails fast if not enough qualified workers; `validate()` checks all heats post-generation

### Config (`config.py`)

- **Owns**: pydantic config model, path resolution
- **Key files**: `config.py`
- **Interface**: `Config` (BaseModel), `CustomAssignmentRecord`, `resolve_config_paths()`
- **Depends on**: pydantic
- **Depended on by**: GUI, app

### Algorithms (`algorithms/`)

- **Owns**: pluggable heat-generation strategies
- **Key files**: `_base.py` (ABC), `_registry.py` (discovery), `randomize.py` (production impl)
- **Interface**: `HeatGenerator.generate(event)`, `@register` decorator, `get_algorithms()`, `get_generator(name)`
- **Depends on**: Event, utils
- **Depended on by**: app, GUI
- **Invariants**: each algorithm module must define exactly one `HeatGenerator` subclass decorated with `@register`; `generate()` mutates the event in place

### App (`app.py`)

- **Owns**: orchestration — event factory and generation pipeline
- **Key files**: `app.py`
- **Interface**: `load_event(...)` (factory), `main(algorithm, event, observer, export)` (runner)
- **Depends on**: Event, algorithms, utils
- **Depended on by**: GUI

### PDF (`pdf.py`)

- **Owns**: PDF artifact generation (sign-in sheets, grid sheets)
- **Key files**: `pdf.py`
- **Interface**: `generate_event_pdf(event, output_path=None)`
- **Depends on**: Event, reportlab
- **Depended on by**: Event (called from `to_pdf()`)

### GUI (`gui.py`)

- **Owns**: all UI state, widgets, user interaction, threading for generation
- **Key files**: `gui.py` (monolithic ~2700 lines)
- **Interface**: `AutologicGUI().run()`
- **Depends on**: app, Config, Event, algorithms, utils, ttkbootstrap, tkinter
- **Depended on by**: nothing (top-level entry)
- **Invariants**: generation runs in background thread; communication via `queue.Queue`; cancellation via `threading.Event` checked by observer

### MSR Export Mapper (`scripts/msr_export_attribute_mapper.py`)

- **Owns**: CLI tool to convert MSR registration exports to autologic member-attributes CSV
- **Key files**: `scripts/msr_export_attribute_mapper.py`
- **Interface**: Click CLI with `--msr_export_csv` and `--member_attributes_csv` options
- **Depends on**: click, csv
- **Depended on by**: nothing (standalone utility)

## Data Flow

```
Inputs:
  AXWare TSV ──┐
  Member CSV ──┤
  YAML Config ─┘
       │
       ▼
  Event Construction (load_participants → load_categories → load_heats → check_role_minima)
       │
       ▼
  Algorithm (Randomizer.generate mutates Event in place)
    ├── randomize_heats(): assign Categories to Heats
    ├── validate size / novice / role constraints per Heat
    └── assign roles to Participants (special → constrained → workers)
       │
       ▼
  Validation (Event.validate → Heat.valid_size, valid_novice_count, valid_role_fulfillment)
       │
       ▼
  Outputs:
    ├── PDF (sign-in + grid tracking sheets)
    ├── CSV (worker assignments)
    └── PKL (serialized Event for reload)
```

**State ownership**: all mutable state lives on the Event object graph (Event → Categories → Participants, Event → Heats). The algorithm mutates this graph. The GUI holds a reference to `current_event` and refreshes views from it.

**Participant ↔ Heat relationship is indirect**: `Participant.category_string → Event.categories[key] → Category.heat → Heat`. The algorithm assigns categories to heats; participants follow.

## Feature → Code Locations

| Feature | Primary Location | Notes |
|---------|-----------------|-------|
| Event construction | `event.py:Event.__init__`, `app.py:load_event` | TSV/CSV parsing, category grouping |
| Heat generation | `algorithms/randomize.py:Randomizer.generate` | brute-force random + validate loop |
| Algorithm plugin system | `algorithms/_registry.py`, `algorithms/_base.py` | auto-discovery via `importlib` |
| Validation | `heat.py:valid_size/valid_novice_count/valid_role_fulfillment`, `event.py:validate` | per-heat constraint checks |
| Role definitions & minima | `utils.py:roles_and_minima` | instructor, timing, grid, start, captain |
| PDF generation | `pdf.py:generate_event_pdf` | reportlab, worker + grid tracking tables |
| Config management | `config.py:Config`, `gui.py:_load_config_from_path/_save_config` | pydantic model ↔ YAML ↔ GUI widgets |
| Custom assignments | `config.py:CustomAssignmentRecord`, `participant.py:set_assignment` | per-participant role locks |
| Run/work group rotation | `heat.py:Heat.working` | formula depends on heat count |
| GUI | `gui.py:AutologicGUI` | monolithic controller (~2700 lines) |
| MSR import | `scripts/msr_export_attribute_mapper.py` | standalone CLI tool |
| Draft mode | `event.py:load_participants` | detected when TSV lacks "Checkin" column |

## Invariants

- **Category is the unit of heat assignment** — participants cannot be individually moved between heats; only whole categories move.
- **Role qualification is enforced** — `Participant.set_assignment()` rejects unqualified assignments (except "worker").
- **Special assignments are locked** — once set, cannot be reassigned to a different role.
- **Minimum role staffing checked at construction** — `Event.check_role_minima()` fails fast before generation begins.
- **Validation is post-generation** — `Event.validate()` runs after the algorithm completes; failure prevents export.
- **GUI generation is threaded** — algorithm runs in a background thread; the main thread polls a queue.
- **Algorithm observer pattern for cancellation** — GUI injects observer; `_notify()` checks `threading.Event`; raises `GenerationCancelled` to abort.

## Cross-Cutting Concerns

| Concern | Location |
|---------|----------|
| Role names and minima | `utils.py:roles_and_minima()` — single source of truth |
| Sorting helpers | `utils.py:sort_dict_by_value/sort_dict_by_nested_value/sort_dict_by_nested_keys` |
| Custom assignment normalization | `utils.py:normalize_custom_assignments()` — handles legacy formats |
| Config path resolution | `config.py:resolve_config_paths()` — resolves relative to config file |
| Pickle compatibility | `gui.py:EventUnpickler` — maps legacy module names for deserialization |
| PyInstaller bundling | `hook-algorithms.py`, `.github/workflows/pipeline.yml` |

## Conventions and Patterns

- **Naming**: role names are lowercase strings (`"instructor"`, `"timing"`, etc.) used as both dict keys and dynamic attributes
- **New algorithms**: add a module in `algorithms/`, define one `HeatGenerator` subclass with `@register`
- **Config**: YAML loaded via `pyyaml`, validated via pydantic `Config` model
- **Testing**: ordered integration tests in `tests/test_integration.py` using `pytest-order`; tests drive the GUI controller programmatically
- **Formatting**: `black` for code formatting (enforced in CI)
- **Participant identity**: Member # is primary ID; falls back to full name when Member # is empty

## Search Anchors

| Symbol | File | Purpose |
|--------|------|---------|
| `class Event` | `event.py` | root domain model |
| `class Participant` | `participant.py` | participant state and assignment |
| `class Category` | `category.py` | car class grouping |
| `class Heat` | `heat.py` | time slot + validation |
| `class Group` | `group.py` | base collection |
| `class HeatGenerator` | `algorithms/_base.py` | algorithm ABC |
| `class Randomizer` | `algorithms/randomize.py` | production algorithm |
| `class Config` | `config.py` | pydantic config model |
| `class AutologicGUI` | `gui.py` | GUI controller |
| `roles_and_minima` | `utils.py` | role definitions |
| `generate_event_pdf` | `pdf.py` | PDF builder |
| `load_event` | `app.py` | event factory |
| `normalize_custom_assignments` | `utils.py` | legacy format handling |
| `WORKER_ASSIGNMENT` | `participant.py` | default role constant |
| `GenerationCancelled` | `gui.py` | cancellation exception |
| `EventUnpickler` | `gui.py` | pickle compatibility |

## Known Gotchas

- **`Heat.participants` is a derived property** — it recomputes from categories on every access; there is no cached list.
- **No-show + special assignment** — these conflicts are collected on `Event.no_show_special_assignments` and must be resolved before generation continues. `Participant.set_assignment` assumes an event context and raises if called for a no-show.
- **`gate` role in member CSV but not in `roles_and_minima()`** — the attribute is loaded onto Participant objects but never used in validation or assignment.
- **Algorithm `exit(1)` on failure** — `randomize.py` calls `exit(1)` when max iterations exceeded; GUI catches this as `SystemExit`.
- **`working` property formula changes by heat count** — 2-heat, 3-heat, and 4+-heat events use different mapping logic.
- **CAM class constraint** — `randomize_heats()` requires all CAM classes to be in the same heat; hardcoded, not configurable.
- **Tests run on Windows in CI** — pipeline builds and tests on `windows-latest`; local dev may be Linux/WSL.
- **Draft mode** — when TSV lacks "Checkin" column, all participants are included but event saving is blocked.
