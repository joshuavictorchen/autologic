# Autologic

[![Pipeline](https://github.com/joshuavictorchen/autologic/actions/workflows/pipeline.yml/badge.svg)](https://github.com/joshuavictorchen/autologic/actions/workflows/pipeline.yml)
[![Release](https://img.shields.io/github/v/release/joshuavictorchen/autologic)](https://github.com/joshuavictorchen/autologic/releases)
[![Coverage](https://img.shields.io/codecov/c/github/joshuavictorchen/autologic)](https://codecov.io/gh/joshuavictorchen/autologic)

This program generates heat + worker assignments for autocross events.

It provides a framework that can be used to programmatically assign `Categories` (car classes) to `Heats`, and `Participants` to roles (work assignments), for a given `Event`.

> [!NOTE]
> **This is a minimum viable prototype product.** It will be cleaned, documented, de-spaghettified, and made more generally applicable after it's gained some field experience at actual events.

## Use

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --config .\path\to\config_file.yaml --algorithm name_of_module` to generate heat and worker assignments for a set of configured parameters.

    - | Sample input file | Description |
      | - | - |
      | [sample_event_config.yaml](./tests/sample_event_config.yaml) | Configurable event parameters (number of heats, number of worker stations, custom assignments, etc.) |
      | [sample_member_attributes.csv](./tests/sample_member_attributes.csv) | Worker qualification table maintained by worker coordinators |
      | [sample_axware_export.tsv](./tests/sample_axware_export.tsv) | Data dump from AXWare |

    - If no `--algorithm` argument is provided, [randomize.py](./autologic/algorithms/randomize.py) is used by default.

3. Optionally load an `Event` configuration and manipulate it by executing `.\path\to\autologic.exe --load .\path\to\event.pkl` and follow the prompts to:

    - Move a `Category` to a different `Heat`
    - Rotate `Heat` run/work groups
    - Update a `Participant`' assignment
    - Run `Event` validation checks
    - Export data

## Contribute

Modules placed in the [./autologic/algorithms/](./autologic/algorithms/) directory  are auto-discovered and exposed as an `--algorithm` choice in the CLI, provided they define exactly one subclass of [HeatGenerator](./autologic/algorithms/_base.py) that is decorated with [@register](./autologic/algorithms/_registry.py).

- See [example.py](./autologic/algorithms/example.py) for a sample scaffold.

Each plugin’s `generate()` method is given a fully initialized `Event` object. Inside it, the plugin must assign all `Categories` to `Heats`, and assign all `Participants` to roles, by mutating the `Event` in place.

- See how the `generate()` method is called in [app.py](./autologic/app.py).

Once the `Event` is returned, `Event.validate()` is called to perform a series of validation checks. If the checks pass, then the `Event` is saved and outputs are generated.

## Validate

> [!NOTE]
> This is a pilot list of generic requirements written in plain English. Algorithm-specific requirements may be enforced at the plugin level.

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

## Sample

> [!NOTE]
> All names in this project are fictional and randomly generated.

### PDF output

<img src="./docs/images/sample-report.png" width="600">

### Code execution

```powershell
(autologic) PS C:\codes\autologic> .\dist\autologic.exe --config .\dist\sample_event_config.yaml --algorithm randomize

  Role minimums
  -------------
  instructor: 16 / 9
      timing: 21 / 6
        grid: 23 / 6
       start: 19 / 3
     captain: 22 / 15

  ==================================================

  [Iteration 0]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 1 (41 total, 13 novices)
  -----------------------------

    Car classes: [EVX, GS, FS, BS, BST, AST, SMF, XB, SST, SSC]

    2 of 3 instructors required

    Heat 1 rejected: unable to fill INSTRUCTOR role(s)

  ==================================================

  [Iteration 1]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 1 (44 total, 17 novices)
  -----------------------------

    Car classes: [DS, GS, AS, CS, DST, SMF, SST, DP, XA, CSM]

    7 of 4 instructors required
    10 of 2 timings required
    10 of 2 grids required
    6 of 1 starts required
    10 of 5 captains required

    Thomas, Mia         assigned to SPECIAL
    Hamilton, Lucas     assigned to INSTRUCTOR
    Martin, Abigail     assigned to INSTRUCTOR
    Evans, Nathan       assigned to INSTRUCTOR
    Brown, Oliver       assigned to INSTRUCTOR
    Robinson, Ella      assigned to START
    Graham, Mia         assigned to CAPTAIN
    Reed, Lucas         assigned to CAPTAIN
    Medina, David       assigned to CAPTAIN
    Lopez, Charlotte    assigned to CAPTAIN
    Baker, Jack         assigned to CAPTAIN
    Nelson, Lily        assigned to TIMING
    Rogers, Sophia      assigned to TIMING
    Reyes, Hannah       assigned to GRID
    Murray, Luna        assigned to GRID
    Foster, Theodore    assigned to WORKER
    Peterson, Benjamin  assigned to WORKER
    Watson, Matthew     assigned to WORKER
    Herrera, Jackson    assigned to WORKER
    Myers, Penelope     assigned to WORKER
    Murphy, Oliver      assigned to WORKER
    King, Grace         assigned to WORKER
    Jimenez, Zoey       assigned to WORKER
    Hughes, Samuel      assigned to WORKER
    Barnes, Oliver      assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Russell, Layla      assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Patel, Chloe        assigned to WORKER
    Walker, David       assigned to WORKER
    Stewart, Isaac      assigned to WORKER
    Gray, Avery         assigned to WORKER
    Morgan, James       assigned to WORKER
    Perry, Aria         assigned to WORKER
    Phillips, Zoey      assigned to WORKER
    Simmons, Isabella   assigned to WORKER
    Alexander, Amelia   assigned to WORKER
    Bryant, Ella        assigned to WORKER
    Green, Chloe        assigned to WORKER
    Adams, Penelope     assigned to WORKER
    Rodriguez, William  assigned to WORKER
    Cooper, Charlotte   assigned to WORKER
    Harris, Michael     assigned to WORKER
    Moore, Alexander    assigned to WORKER

  Heat 2 (40 total, 13 novices)
  -----------------------------

    Car classes: [EVX, P, DSP, BS, GST, CST, BST, XB, ESP, SSC]

    6 of 3 instructors required
    6 of 2 timings required
    4 of 2 grids required
    5 of 1 starts required
    6 of 5 captains required

    Taylor, Henry       assigned to SPECIAL
    Reynolds, Henry     assigned to CAPTAIN
    Hughes, Samuel      assigned to CAPTAIN
    Jordan, Charlotte   assigned to CAPTAIN
    Rodriguez, Sofia    assigned to CAPTAIN
    Tran, Avery         assigned to CAPTAIN
    Hall, Joseph        assigned to GRID
    Cole, Emily         assigned to GRID
    Turner, Elias       assigned to INSTRUCTOR
    Patterson, Benjamin assigned to INSTRUCTOR
    Wallace, Michael    assigned to INSTRUCTOR
    Allen, Samuel       assigned to TIMING
    Ellis, Aiden        assigned to TIMING
    Gonzalez, Benjamin  assigned to START
    Anderson, Lucas     assigned to WORKER
    Wright, Victoria    assigned to WORKER
    Ruiz, Joseph        assigned to WORKER
    Brooks, Ella        assigned to WORKER
    Howard, Henry       assigned to WORKER
    Martinez, Isabella  assigned to WORKER
    Turner, Elias       assigned to WORKER
    Powell, Nathan      assigned to WORKER
    Ramos, Evelyn       assigned to WORKER
    Castillo, Victoria  assigned to WORKER
    Miller, Elijah      assigned to WORKER
    Coleman, Hannah     assigned to WORKER
    Romero, James       assigned to WORKER
    Mendoza, David      assigned to WORKER
    Wilson, Amelia      assigned to WORKER
    Moreno, Abigail     assigned to WORKER
    Scott, Leo          assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Cox, Abigail        assigned to WORKER
    Alvarez, Grace      assigned to WORKER
    Smith, Olivia       assigned to WORKER
    Garcia, Emily       assigned to WORKER
    West, Daniel        assigned to WORKER
    Richardson, Emily   assigned to WORKER
    Henderson, Mia      assigned to WORKER
    Ford, Grace         assigned to WORKER

  Heat 3 (39 total, 11 novices)
  -----------------------------

    Car classes: [CAM-C, SR, ES, FS, EST, HS, AST, CAM-T, SM, FP]

    3 of 3 instructors required
    5 of 2 timings required
    9 of 2 grids required
    8 of 1 starts required
    6 of 5 captains required

    Clark, Jackson      assigned to INSTRUCTOR (custom assignment)
    Johnson, Noah       assigned to INSTRUCTOR (custom assignment)
    White, Evelyn       assigned to INSTRUCTOR
    Gibson, Sofia       assigned to CAPTAIN
    Williams, Emma      assigned to CAPTAIN
    Edwards, Eleanor    assigned to CAPTAIN
    Young, Luna         assigned to CAPTAIN
    Davis, Sophia       assigned to CAPTAIN
    Carter, Theodore    assigned to TIMING
    Ortiz, Isabella     assigned to TIMING
    Lewis, Aiden        assigned to GRID
    Hayes, Matthew      assigned to GRID
    Griffin, Evelyn     assigned to START
    Bailey, Amelia      assigned to WORKER
    Jenkins, Elias      assigned to WORKER
    Morris, Mia         assigned to WORKER
    Long, Jack          assigned to WORKER
    Jackson, Harper     assigned to WORKER
    Gutierrez, William  assigned to WORKER
    Kelly, Mia          assigned to WORKER
    Ward, Daniel        assigned to WORKER
    Stevens, Samuel     assigned to WORKER
    Ramos, Evelyn       assigned to WORKER
    Cruz, Layla         assigned to WORKER
    Garcia, Liam        assigned to WORKER
    Martinez, Matthew   assigned to WORKER
    Fisher, Sophia      assigned to WORKER
    Miller, Elijah      assigned to WORKER
    Vasquez, William    assigned to WORKER
    Gray, Avery         assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Cook, Elijah        assigned to WORKER
    Aguilar, Joseph     assigned to WORKER
    Coleman, Hannah     assigned to WORKER
    Thompson, Daniel    assigned to WORKER
    Jones, Ava          assigned to WORKER
    Foster, Theodore    assigned to WORKER
    Hernandez, James    assigned to WORKER
    Stewart, Isaac      assigned to WORKER

  ---

  >>> Iteration 1 accepted <<<

  ==============================================================================

  [Event validation checks]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 1 (44 total, 17 novices)
  -----------------------------

    Car classes: [DS, GS, AS, CS, DST, SMF, SST, DP, XA, CSM]

    4 of 4 instructors assigned
    2 of 2 timings assigned
    2 of 2 grids assigned
    1 of 1 starts assigned
    5 of 5 captains assigned

  Heat 2 (40 total, 13 novices)
  -----------------------------

    Car classes: [EVX, P, DSP, BS, GST, CST, BST, XB, ESP, SSC]

    3 of 3 instructors assigned
    2 of 2 timings assigned
    2 of 2 grids assigned
    1 of 1 starts assigned
    5 of 5 captains assigned

  Heat 3 (39 total, 11 novices)
  -----------------------------

    Car classes: [CAM-C, SR, ES, FS, EST, HS, AST, CAM-T, SM, FP]

    3 of 3 instructors assigned
    2 of 2 timings assigned
    2 of 2 grids assigned
    1 of 1 starts assigned
    5 of 5 captains assigned

  Summary
  -------

    All checks passed.

  The following individuals have not checked in and are therefore excluded:

  - Simmons, Isabella
  - Parker, Aria
  - Castillo, Victoria

  Worker assignment sheet saved to autologic-event.csv

  Worker assignment printout saved to autologic-event.pdf

  Event state saved to autologic-event.pkl
```

### Event perturbation

```powershell
(autologic) PS C:\codes\autologic> .\dist\autologic.exe --load .\autologic-event.pkl

Event loaded: autologic-event

---

[1] Move a Category to a different Heat
[2] Rotate Heat run/work groups
[3] Update a Participant assignment
[4] Run Event validation checks
[5] Export data
[Q] Quit

Selection: 2

---

Apply a run/work group offset: 1

Heat 1 | Running 1 | Working 2 | CAM-C, SR, ES, FS, EST, HS, AST, CAM-T, SM, FP
Heat 2 | Running 2 | Working 3 | DS, GS, AS, CS, DST, SMF, SST, DP, XA, CSM
Heat 3 | Running 3 | Working 1 | EVX, P, DSP, BS, GST, CST, BST, XB, ESP, SSC

---

[1] Move a Category to a different Heat
[2] Rotate Heat run/work groups
[3] Update a Participant assignment
[4] Run Event validation checks
[5] Export data
[Q] Quit

Selection: 5

---

Files with the same Event name will be overwritten!

Save Event as: updated-event

  Worker assignment sheet saved to updated-event.csv

  Worker assignment printout saved to updated-event.pdf

  Event state saved to updated-event.pkl
```
