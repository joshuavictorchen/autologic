# Autologic — Specification

Last updated: 2026-02-26

## 1. Scope

Autologic is a desktop application for autocross event coordination. It assigns participants to heats (run/work time slots) and worker roles, validates the result against configurable constraints, and produces printable artifacts for event-day use.

### In scope

- Parsing participant data from AXWare TSV exports
- Parsing member role qualifications from CSV
- YAML-based configuration with pydantic validation
- Heat generation via pluggable algorithms
- Role assignment with qualification enforcement
- Constraint validation (heat size, novice distribution, role coverage)
- PDF output (worker tracking + grid tracking sheets)
- CSV output (worker assignments)
- PKL output (serialized event state for reload)
- GUI (ttkbootstrap) with inline editing, custom assignments, and generation controls
- Algorithm plugin system with auto-discovery

### Out of scope

- Multi-event management
- User authentication or access control
- Network communication or remote data sources
- Registration system integration beyond AXWare TSV import

---

## 2. Domain Model

### 2.1 Participant

A person registered for the event.

- **Identity**: Member # (string) is the primary identifier. When Member # is empty, full name (`"First Last"`) is used as fallback ID.
- **Category membership**: each Participant belongs to exactly one Category, determined by the `Class` field in the AXWare export.
- **Novice status**: determined by the `"NOV"` prefix on the AXWare class string.
- **Role qualifications**: boolean flags per role (instructor, timing, grid, start, captain), loaded from the member attributes CSV. A participant MAY be qualified for zero or more roles.
- **Assignment**: a single role string, set during generation. One of: `instructor`, `timing`, `grid`, `start`, `captain`, `worker`, `special`.
- **Special assignment**: an optional pre-locked role from config. When set, the participant MUST be assigned that specific role during algorithmic generation. The GUI MAY override any assignment (including special) via manual inline editing.

### 2.2 Category

A competition class (e.g., "CS", "BST", "CAM-C") that groups participants.

- A Category belongs to exactly one Heat.
- All Participants in a Category share the same Heat.
- Category is the **atomic unit of heat assignment** — participants cannot be individually moved between heats.

### 2.3 Heat

A time slot representing a run/work group.

- A Heat does not store participants directly. It derives its participant list from its assigned Categories.
- Each Heat has a `running` number (its position, 1-indexed) and a `working` number (which group it works during).
- Each Heat has a `complement` — the Heat that is running while this Heat is working.

#### 2.3.1 Run/Work Group Mapping

The `working` number is computed from the `running` number and the total number of heats:

| Heat count | Mapping |
|------------|---------|
| 2 | working = 3 - running (swap: 1↔2) |
| 3 | working = ((running + 3) % number_of_heats) + 1 |
| 4+ | working = ((running + 5) % number_of_heats) + 1 |

The complement of a heat is the heat whose `running` equals this heat's `working`.

#### 2.3.2 Run/Work Group Rotation

The GUI supports rotating the run/work group mapping by shifting the heats list. This changes the ordering but preserves category-to-heat assignments.

### 2.4 Event

The root domain object. Composes Participants, Categories, and Heats.

- Constructed from: AXWare TSV, member attributes CSV, and a Config.
- Owns all mutable state.
- Responsible for validation and export.

### 2.5 Config

Application configuration, validated via pydantic.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | `"autologic-event"` | Event name, used for output filenames |
| `axware_export_tsv` | path | (required) | Path to AXWare export file |
| `member_attributes_csv` | path | (required) | Path to member qualifications CSV |
| `number_of_heats` | int | 3 | Number of heats to generate |
| `number_of_stations` | int | 5 | Number of course worker stations (= captain count) |
| `custom_assignments` | dict | {} | Pre-locked role assignments keyed by member ID |
| `heat_size_parity` | int | 25 | Divisor for heat size tolerance |
| `novice_size_parity` | int | 10 | Divisor for novice count tolerance |
| `novice_denominator` | int | 3 | Divisor for instructor minimum calculation |
| `max_iterations` | int | 10000 | Algorithm iteration limit |

**Parameter bounds**: the config model does not enforce lower bounds on numeric parameters. Values of zero for `number_of_heats`, `heat_size_parity`, `novice_size_parity`, or `novice_denominator` will produce division-by-zero errors at runtime.

---

## 3. Input Formats

### 3.1 AXWare Export TSV

Tab-delimited file with the following columns (order-independent):

| Column | Required | Notes |
|--------|----------|-------|
| `First Name` | MUST | |
| `Last Name` | MUST | |
| `Member #` | MUST | May be empty; full name used as fallback ID |
| `Class` | MUST | Prefixes: `NOV` (novice), `SR`, `P` are stripped to determine the base category |
| `Number` | MUST | Car number |
| `Checkin` | MAY | If absent, event enters draft mode |

When the `Checkin` column is present, only participants whose checkin value equals `"YES"` (case-insensitive) are included; all others are recorded as no-shows. When the column is absent, all participants are included and the event enters **draft mode** (export is blocked).

#### 3.1.1 Category Parsing

The `Class` field is uppercased and then parsed via mutually exclusive prefix matching:

1. If prefixed with `"NOV"`: participant is marked novice, prefix is stripped, and the remainder becomes the category string (e.g., `"NOVCS"` → novice + category `"CS"`, `"NOVSRCAM-T"` → novice + category `"SRCAM-T"`).
2. Else if prefixed with `"SR"`: category string becomes `"SR"` regardless of suffix (e.g., `"SRCAM-T"` → category `"SR"`).
3. Else if prefixed with `"P"`: category string becomes `"P"` regardless of suffix.
4. Otherwise: the original `Class` value (not uppercased) is used as the category string.

These branches are mutually exclusive — a `"NOV"`-prefixed class never passes through `"SR"` or `"P"` normalization.

### 3.2 Member Attributes CSV

Comma-delimited file with columns:

| Column | Required | Notes |
|--------|----------|-------|
| `id` | MUST | String member identifier (e.g., `"SAMPLE-457"`) |
| `name` | MUST | Display name |
| `instructor` | MAY | Boolean qualification flag |
| `timing` | MAY | Boolean qualification flag |
| `grid` | MAY | Boolean qualification flag |
| `start` | MAY | Boolean qualification flag |
| `captain` | MAY | Boolean qualification flag |
| `gate` | MAY | Present in format but not used in role assignment |

### 3.3 YAML Configuration

Standard YAML file. Paths in the config MAY be relative (resolved against the config file's parent directory) or absolute.

---

## 4. Roles and Minima

Roles are the set of worker positions that must be filled each heat. Role names are lowercase strings used consistently as dict keys, attribute names, and assignment values.

| Role | Minimum per Heat | Notes |
|------|-----------------|-------|
| `instructor` | max(3, round(novices_in_complement_heat / novice_denominator)) | Dynamic; uses banker's rounding, floored at 3 |
| `timing` | 2 | Fixed |
| `grid` | 2 | Fixed |
| `start` | 1 | Fixed |
| `captain` | number_of_stations | Configurable |
| `worker` | — | Default assignment; no minimum |
| `special` | — | Custom assignment; no minimum |

The roles and their per-heat minimums are defined in a single location. The `gate` role appears in member attribute data but is not included in the role set — it is loaded as a participant attribute but never used in assignment or validation.

---

## 5. Algorithm System

### 5.1 Plugin Interface

Algorithms are pluggable modules in `autologic/algorithms/`. Each module SHOULD define exactly one `HeatGenerator` subclass decorated with `@register`. If multiple subclasses register in the same module, later registrations silently overwrite earlier ones (keyed by module name). This is convention, not an enforced invariant.

The `@register` decorator keys the algorithm by module name (e.g., `randomize`).

Discovery is automatic via `importlib`. Modules prefixed with `_` are excluded.

### 5.2 Algorithm Contract

Each algorithm's `generate(event)` method MUST mutate the Event in place by:
1. Assigning every Category to a Heat.
2. Assigning every Participant to a role.

After `generate()` returns, the event is validated. If validation fails, the event is invalid and output generation is blocked.

### 5.3 Observer Pattern

Algorithms support an observer pattern for cancellation. Observers are callables registered on the algorithm instance. Algorithms MUST invoke observers at regular intervals during long-running loops to provide cancellation checkpoints. Observers MAY raise exceptions to abort generation.

### 5.4 Randomizer Algorithm (Production)

The `Randomizer` uses a brute-force randomize-and-check approach:

1. Randomly assign categories to heats.
2. Validate: heat sizes within tolerance, novice counts within tolerance, enough qualified workers per role per heat.
3. If invalid, retry. The outer loop runs `max_iterations + 1` times (0 through `max_iterations` inclusive). The inner `randomize_heats()` loop has no iteration bound — it retries until the CAM constraint and heat size constraint are both satisfied.
4. On valid configuration: assign roles in priority order (most constrained first), then assign remaining participants as "worker".

**CAM class constraint**: all categories whose name starts with `"CAM-"` MUST be assigned to the same heat. This constraint is hardcoded in the Randomizer and is not configurable.

**Special assignment handling**: participants with special assignments are assigned first, before role-based assignment.

**Role assignment priority**: roles are sorted by `role_extras` (ascending) — the most constrained roles (fewest surplus qualified participants) are filled first.

---

## 6. Validation

Validation runs after heat generation via `Event.validate()`. All heats MUST pass all checks for the event to be valid.

### 6.1 Heat Size

For each heat:
```
mean = round(total_participants / number_of_heats)
max_delta = ceil(total_participants / heat_size_parity)
abs(heat.total - mean) <= max_delta
```

### 6.2 Novice Distribution

For each heat:
```
mean = round(total_novices / number_of_heats)
max_delta = ceil(total_novices / novice_size_parity)
abs(heat.novice_count - mean) <= max_delta
```

### 6.3 Role Coverage

For each heat, for each role:
- The number of assigned participants MUST equal the role minimum, **except** `instructor` which MAY exceed the minimum.
- All participant assignments MUST be one of the recognized role names, `"worker"`, or `"special"`.

### 6.4 Novice Warning

Novices assigned to specialized roles (non-worker) generate warnings but do not fail validation.

### 6.5 Pre-Generation Check

Before generation, the system performs a coarse staffing check: for each role, the total number of qualified participants must meet or exceed `minimum * number_of_heats`. The instructor minimum for this check uses the event-wide average novices-per-heat, not per-heat complement novice counts. This is a fail-fast guard, not a guarantee that per-heat role fulfillment will succeed — the algorithm may still fail to distribute qualified participants adequately across individual heats.

---

## 7. Outputs

### 7.1 PDF

Generated via reportlab. Contains:
1. **Title**: event name.
2. **Heat/Class table**: which classes run/work in each heat.
3. **Role summary table**: per-heat assignment counts (plain counts, no validation highlighting).
4. **Worker tracking sheet**: sorted by heat, then name. Columns: working group, name, class, number, assignment, checked-in (blank placeholder for paper tracking).
5. **Grid tracking sheet**: sorted by heat, class, number. Columns: running group, name, class, number, run tally (blank placeholder for paper tracking).

Page numbering uses "Page X of Y" format via two-pass canvas.

### 7.2 CSV

Worker assignments in tabular format. Columns match the worker tracking sheet.

### 7.3 PKL (Pickle)

Serialized Event object for later reload. Includes an embedded config snapshot for config restoration on load. Deserialization handles legacy module name mappings for backward compatibility.

---

## 8. GUI

### 8.1 Architecture

- Framework: ttkbootstrap (themed Tkinter)
- Threading: generation runs in a background thread; results communicated via a queue; cancellation via a shared flag checked by the algorithm observer

### 8.2 Layout

Two-column layout:
- **Left**: Control Panel (generate/save/load buttons), Parameters pane, Custom Assignments pane
- **Right**: Event Data — Heats & Classes, Role Summary, Worker Assignments

### 8.3 Key Interactions

- **Generate Event**: validates config, runs algorithm in background thread, refreshes views on completion.
- **Cancel**: sets cancellation flag; observer aborts generation at the next checkpoint.
- **Save Config**: serializes current widget state to YAML.
- **Load Config**: reads YAML, applies to widgets.
- **Save Event**: writes CSV, PDF, PKL to config directory.
- **Load Event**: deserializes PKL, restores config snapshot, refreshes views.
- **Move Class**: modal dialog to move a category to a different heat.
- **Rotate Run/Work**: shifts the heats list to change run/work mapping.
- **Inline editing**: worker assignments editable via combobox overlay in the worker table.
- **Custom assignments**: add/edit/remove/toggle via treeview with checkbox images.

### 8.4 Dirty Tracking

The GUI tracks two dirty flags:
- `config_dirty`: any parameter or assignment change since last save.
- `event_dirty`: any post-generation change (class move, assignment edit, rotation).

An in-panel status label shows an unsaved indicator when either flag is set.

### 8.5 Draft Mode

When the AXWare export lacks a `Checkin` column, the event enters draft mode. In draft mode, the **Save Event** button is disabled.

---

## 9. Custom Assignments

Custom assignments pre-lock specific participants to specific roles before generation.

- Stored in config as a dict keyed by member ID (string or int).
- Values may be plain strings (role name) or `CustomAssignmentRecord` objects (with `assignment` and `is_active` fields).
- Inactive assignments are persisted in config but not applied during generation.
- A participant with a custom assignment:
  - MUST be assigned that role during algorithmic generation.
  - Is auto-qualified for the assigned role (the qualification flag is set dynamically).
  - The GUI MAY override the assignment via manual inline editing (bypasses qualification and special-assignment checks).
- No-show participants with special assignments are excluded from the event. The GUI asks whether to continue without the participant before the generation worker starts. Non-GUI callers receive a warning and generation continues without the participant.

---

## 10. MSR Export Mapper

Standalone CLI tool (`scripts/msr_export_attribute_mapper.py`) that converts MotorsportReg (MSR) export data to the member attributes CSV format expected by Autologic.

- Click CLI with `--msr_export_csv` and `--member_attributes_csv` options.
- Merges MSR work assignments with existing member attributes (additive only — adds qualifications, never removes).
- Outputs `private_updated_member_attributes.csv`.

---

## 11. CI/CD

Pipeline: lint (black) → build (PyInstaller, Windows) → test (pytest + coverage) → release (GitHub Release on version tags).

- Build produces a single `autologic.exe` via PyInstaller `--onefile --noconsole`.
- Tests run on `windows-latest`.
- Release uploads exe + sample files to GitHub Releases.
