# Autologic

[![Pipeline](https://github.com/joshuavictorchen/autologic/actions/workflows/pipeline.yml/badge.svg)](https://github.com/joshuavictorchen/autologic/actions/workflows/pipeline.yml)
[![Release](https://img.shields.io/github/v/release/joshuavictorchen/autologic)](https://github.com/joshuavictorchen/autologic/releases)
[![Coverage](https://img.shields.io/codecov/c/github/joshuavictorchen/autologic)](https://codecov.io/gh/joshuavictorchen/autologic)

`Autologic` is a desktop application for coordinating autocross events. It generates balanced run/work groups, assigns participants to required worker roles, and produces printable outputs for day-of-event operations.

The application models events in terms of `Categories` (car classes), `Heats`, and `Participants`, and applies configurable constraints to ensure adequate role coverage, instructor availability for novices, and parity across groups.

## Motivation

Autocross events are typically organized by dividing participants into competitive classes and assigning those classes to run/work groups. In addition to balancing group sizes, worker coordinators must ensure that each heat has adequate coverage for specialized roles (timing, grid, start, course captains, etc.) and sufficient instructors to support novice drivers.

The available planning window is often very short - commonly limited to the time between registration close and the start of the event. Producing well-balanced assignments manually under these conditions poses a logistical challenge.

`Autologic` automates this process. It generates run/work groups, assigns participants to roles based on qualifications and constraints, and produces printable artifacts (sign-in sheets and grid sheets) suitable for use by worker coordinators and grid workers on event day.

## Inputs

- **Event data export** ([sample file](tests/sample_axware_export.tsv))
  - A tabular export of participant data for a single event (name, member ID, car class, car number, novice status, etc.).
  - Currently supports AXWare TSV exports.

- **Member attributes** ([sample file](tests/sample_member_attributes.csv))
  - A table mapping members to the roles for which they are qualified (CSV).

> [!NOTE]
> AXWare is currently the only supported event export format. The input layer is intentionally minimal, and additional connectors for other registration systems can be added with modest effort.
> Support for additional formats can be requested by [opening an issue](https://github.com/joshuavictorchen/autologic/issues/new).

## Use

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/) or [directly from this link](https://github.com/joshuavictorchen/autologic/releases/latest/download/autologic.exe).

2. Place the executable in a local folder and run it once.

   - AXWare exports and the member attributes CSV are typically stored in this same folder.

3. Launch the application.

   - A default `autologic.yaml` configuration file is created and loaded automatically.
   - While additional configuration files may be loaded or saved, most workflows simply use the default.

4. Update parameters and file selections in the **Parameters** pane as needed.

   - An `Event Name - Date` naming convention is recommended for clarity.

5. Use the **Custom Assignments** pane to enforce specific role assignments for individual participants, if desired.

6. Click **Generate Event** to construct run/work groups and initial worker assignments.

7. Review the **Role Summary** pane.

   - The pane updates automatically after edits and highlights invalid or unsatisfied constraints.

8. Review the **Heats & Classes** pane.

   - Classes may be moved between heats.
   - Run/work group rotation may be adjusted.

9. Review the **Worker Assignments** pane.

   - Columns may be sorted as needed.
   - Individual assignments may be edited in place.

10. Click **Save Config** to persist the current configuration.

11. Click **Save Event** to generate output artifacts (PDF and PKL event state files).

    - The PDF is intended for printing and day-of-event use by worker coordinators and grid workers.

## Validation

After heat and role assignment, the generated event is validated against a set of configurable constraints. Validation failures prevent event output generation; warnings are logged but do not block generation.

### Heat size constraints

- Heat size must fall within
  `[(number of participants in event) ÷ (number of heats)] ± (heat size delta)`

  - Heat size delta is defined as
    `(number of participants in event) ÷ (heat size parity)`
  - Heat size parity is configurable.

### Novice distribution constraints

- The number of novices per heat must fall within
  `[(number of novices in event) ÷ (number of heats)] ± (novice size delta)`

  - Novice size delta is defined as
    `(number of novices in event) ÷ (novice size parity)`
  - Novice size parity is configurable.

### Role coverage constraints

All specialized roles must be filled within each heat:

| Role       | Required per heat                                                    |
| ---------- | -------------------------------------------------------------------- |
| Instructor | ≥ `(number of novices in complementary heat) ÷ (novice denominator)` |
| Timing     | = 2                                                                  |
| Grid       | = 2                                                                  |
| Start      | = 1                                                                  |
| Captain    | = `(number of worker stations on course)`                            |

- Novice denominator and number of worker stations are configurable parameters.
- Novices may be assigned to specialized roles if qualified; each such assignment generates a warning.

## Contribution

Autologic supports pluggable heat-generation algorithms.

Modules placed in [`./autologic/algorithms/`](./autologic/algorithms/) are auto-discovered and exposed as `--algorithm` options in the CLI, provided the module defines **exactly one** subclass of [`HeatGenerator`](./autologic/algorithms/_base.py) decorated with [`@register`](./autologic/algorithms/_registry.py).

- [`example.py`](./autologic/algorithms/example.py) provides a minimal reference implementation.

Each algorithm’s `generate()` method receives a fully initialized `Event` object. The algorithm is responsible for:

- assigning all `Categories` to `Heats`, and
- assigning all `Participants` to roles,

by mutating the `Event` in place.

The invocation flow can be traced in [`app.py`](./autologic/app.py).

After `generate()` completes, `Event.validate()` is executed. If validation passes, the event state is persisted and output artifacts may be generated.

### Observers

`HeatGenerator.add_observer(...)` and `HeatGenerator._notify(...)` are optional.

- Observers currently serve as GUI cancellation hooks.
- `_notify(...)` calls within long-running loops provide cancellation checkpoints.
- `_notify(event_type, payload)` accepts arbitrary payloads; payloads are not currently interpreted by the GUI.

### GUI parameter compatibility

The **Parameters** pane in the GUI is currently tuned to `randomize.py`. Other algorithms may ignore some parameters; this behavior is expected and does not affect heat generation.
