# Tests

> [!NOTE]
> All names in the sample files here are fictional and randomly generated.

## Overview

- `tests/test_integration.py` is the ordered GUI integration suite.
- `tests/sample_event_config.yaml` and the sample TSV/CSV inputs are shared fixtures for the integration flow.

## Integration test flow

The GUI integration test in `tests/test_integration.py` is split into ordered steps and uses a shared
workspace plus a lightweight state file to pass artifacts between steps.

Key behaviors:

- Ordered steps are enforced with `pytest-order`.
- A module-scoped `integration_workspace` temp directory stores artifacts for the run.
- A `gui_integration_state.yaml` file in the workspace carries paths and identifiers between steps.
- `create_gui_controller` stubs `messagebox` and `filedialog` and injects a fixed RNG seed.
- `clear_directory` resets the workspace at the start of a run for deterministic behavior.
- The GUI integration requires Tcl/Tk support; missing Tcl/Tk raises a hard error.

## Running

```bash
pip install -r requirements-dev.in
pytest tests/test_integration.py
```

On Windows, ensure your Python install includes Tcl/Tk (the standard python.org installer does).

## Adding new tests

### Add a new ordered integration step

- Add a new test in `tests/test_integration.py` with `@pytest.mark.order(N)` and append it to the flow.
- Use `load_state`/`save_state` to pass any new artifacts (paths, IDs) between steps.
- Keep inputs deterministic (fixed seed, stable sample data).
- Prefer using `integration_workspace` for files so cleanup stays centralized.

### Add standalone tests

- Create a new test file or function outside the ordered flow.
- Use `tmp_path`/`tmp_path_factory` for isolation.
- Avoid reading or writing the integration state file.
- If you must interact with the GUI, use `create_gui_controller` and always call its cleanup.

## Data hygiene

- Keep new sample fixtures in `tests/` and document them here if they are required.
