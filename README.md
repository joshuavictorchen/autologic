# Autologic

[![Pipeline](https://github.com/joshuavictorchen/autologic/actions/workflows/pipeline.yml/badge.svg)](https://github.com/joshuavictorchen/autologic/actions/workflows/pipeline.yml)
[![Release](https://img.shields.io/github/v/release/joshuavictorchen/autologic)](https://github.com/joshuavictorchen/autologic/releases)
[![Coverage](https://img.shields.io/codecov/c/github/joshuavictorchen/autologic)](https://codecov.io/gh/joshuavictorchen/autologic)

This program generates heat + worker assignments for autocross events.

It also provides a framework that can be used to programmatically assign `Categories` (car classes) to `Heats`, and `Participants` to roles (work assignments), for a given `Event`.

## Use

> [!NOTE]
> All names in this project are fictional and randomly generated.

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/) or by [clicking on this link](https://github.com/joshuavictorchen/autologic/releases/latest/download/autologic.exe).

2. Open a terminal window and execute `.\path\to\autologic.exe --config .\path\to\config_file.yaml --algorithm name_of_module` to generate heat and worker assignments for a set of configured parameters.

    - | Sample input file | Description |
      | - | - |
      | [sample_event_config.yaml](https://github.com/joshuavictorchen/autologic/releases/latest/download/sample_event_config.yaml) | Configurable event parameters (number of heats, number of worker stations, custom assignments, etc.) |
      | [sample_member_attributes.csv](https://github.com/joshuavictorchen/autologic/releases/latest/download/sample_member_attributes.csv) | Worker qualification table maintained by worker coordinators |
      | [sample_axware_export.tsv](https://github.com/joshuavictorchen/autologic/releases/latest/download/sample_axware_export.tsv) | Data dump from AXWare |

    - If no `--algorithm` argument is provided, [randomize.py](./autologic/algorithms/randomize.py) is used by default.

3. Optionally load an `Event` configuration and manipulate it by executing `.\path\to\autologic.exe --load .\path\to\event.pkl` and follow the prompts to:

    - Move a `Category` to a different `Heat`
    - Rotate `Heat` run/work groups
    - Update a `Participant`' assignment
    - Run `Event` validation checks
    - Export data

## Validate

- Heat size must be within `[(number of participants in event) ÷ (number of heats)] ± (heat size delta)`
  - Where heat size delta is equal to `(number of participants in event) ÷ (heat size parity)`
    - Where heat size parity is a configurable parameter
- The number of novices within a heat must be within `[(number of novices in event) ÷ (number of heats)] ± (novice size delta)`
  - Where novice size delta is equal to `(number of novices in event) ÷ (novice size parity)`
    - Where novice size parity is a configurable parameter
- All specialized roles must be filled within each heat:

  | Role | Required per heat |
  | - | - |
  | Instructor | ≥ `(number of novices in complimentary heat) ÷ (novice denominator)` |
  | Timing | = 2 |
  | Grid | = 2 |
  | Start | = 1 |
  | Captain | = `(number of worker stations on course)` |

  - Where novice denominator and number of stations are configurable parameters
- Novices may be assigned to special roles (if qualified), but the program logs a warning for each of these assignments

## Contribute

Modules placed in the [./autologic/algorithms/](./autologic/algorithms/) directory  are auto-discovered and exposed as an `--algorithm` choice in the CLI, provided they define exactly one subclass of [HeatGenerator](./autologic/algorithms/_base.py) that is decorated with [@register](./autologic/algorithms/_registry.py).

- See [example.py](./autologic/algorithms/example.py) for a sample scaffold.

Each plugin’s `generate()` method is given a fully initialized `Event` object. Inside it, the plugin must assign all `Categories` to `Heats`, and assign all `Participants` to roles, by mutating the `Event` in place.

- See how the `generate()` method is called in [app.py](./autologic/app.py).

Once the `Event` is returned, `Event.validate()` is called to perform a series of validation checks. If the checks pass, then the `Event` is saved and outputs are generated.

`HeatGenerator.add_observer(...)` and `HeatGenerator._notify(...)` are optional; algorithms work without them.

- Observers are currently a GUI cancellation hook, so `_notify(...)` calls inside long loops provide cancellation checkpoints.
- `_notify(event_type, payload)` accepts any payload shape today; the GUI does not interpret payloads yet.

The Parameters pane in the GUI is currently tuned to `randomize.py`; other algorithms may ignore some fields, which is expected for now and does not affect heat generation.
