# GUI Developer Manual

## Purpose

The GUI in `gui.py` loads configuration data, generates events in memory, and presents editable tables for heats, roles, and worker assignments.

## Entry points

- `gui/gui.py`: main GUI module
- `AutologicGUI().run()`: starts the app

## Architecture overview

- `AutologicGUI` owns the entire UI, state, and event lifecycle

- It orchestrates:
  - config loading and saving
  - event generation via `autologic.app.load_event` and `autologic.app.main`
  - validation display and table refreshes
  - saving outputs (CSV, PDF, PKL)

## Layout structure

`_build_layout` divides the window into two columns:

- Left column
  - Control Panel (`_build_control_panel`)
  - Parameters (`_build_parameters_panel`)
  - Custom Assignments (`_build_assignments_panel`)

- Right column
  - Event Data (`_build_data_panel`)
    - Heats & Classes table with actions
    - Role Summary table with validation indicators
    - Worker Assignments table

The panel builders are kept separate to keep layout code readable and to make targeted UI changes easier.

## State and data flow

Key state fields in `AutologicGUI`:

- `current_event`: active `Event` instance or `None`
- `config_dirty` / `event_dirty`: track unsaved changes
- `is_generating`: generation in progress
- `generation_cancel_requested`: cancellation flag for background generation
- `assignment_use_state`: per-row checkbox state for custom assignments
- `worker_table_mapping`: maps worker table rows to `Participant` objects

Event lifecycle:

1. Load config (`_load_config_from_path`) and resolve relative paths
2. Generate event (`_start_generation` -> `_run_generation_thread`)
3. Apply results (`_handle_generation_result`) and refresh views
4. Save outputs (`_save_event`) next to the active config

## Config handling

- Default config lives next to the app (`autologic.yaml`)
- Relative paths in config are resolved against the config file directory
- Config is built from widget values via `_build_config_payload`
- Use `_mark_config_dirty` when user input changes

## Draft mode handling

- `Event.draft_mode` is set when the TSV lacks the `CheckIn` column
- The GUI warns on TSV selection and disables Save Event
- The status label shows `DRAFT event` when draft mode is active

## Assignment editing

Custom assignments:

- Table rows track `use` state and assignment role
- `+ Add assignment` row opens the assignment dialog
- Right-click on a row opens a delete context menu
- The dialog syncs member ID and name dropdowns

Worker assignments:

- Single-click in the Assignment column opens a dropdown
- Updates call `Participant.set_assignment` and refresh tables

Inline dropdowns are handled by `_show_assignment_editor` to avoid pop-up dialogs and keep edits in context.

## Validation and sorting

- `_evaluate_event_validity` returns invalid cells and overall validity
- Role Summary highlights invalid cells in orange
- Worker table sort toggles in `_sort_worker_table` and header updates in `_update_worker_sort_headings`

## Threading and cancellation

- Generation runs in a background thread to keep the UI responsive
- `_generation_observer` checks `generation_cancel_requested` and aborts
- `_check_generation_queue` polls the queue and updates the UI

## Adding new features

Add a new parameter:

1. Add a `tk.StringVar` (or appropriate type) in `__init__`
2. Add the widget in `_build_parameters_panel`
3. Include it in `_build_config_payload`
4. Apply it in `_load_config_from_path`
5. If it affects event generation, include it in `load_event` payload

Add a new panel:

1. Create a new `_build_*` method
2. Wire it in `_build_layout`
3. Store needed widgets on `self` for later updates

Add a new event action:

1. Add a button and callback
2. Mutate `current_event`
3. Call `_mark_event_dirty`, `_refresh_event_views`, and `_validate_current_event`

## Conventions

- Use Google-style docstrings
- Inline comments explain why, not just what
- Avoid abbreviations in identifiers
- Changes to assignment logic or output format should be coordinated

## Quick sanity checks

- `python -m py_compile gui/gui.py` to confirm syntax
- Run `python gui/gui.py` and validate the main flows
