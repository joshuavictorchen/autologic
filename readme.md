# Autologic

This program generates heat + worker assignments for autocross events.

It provides a framework that may be used to assign `Categories` (car classes) to `Heats`, and `Participants` to `Roles` (specialized work assignments).

The default algorithm loads an `Event`, randomly assigns `Categories` to `Heats`, checks against acceptance criteria (can all `Roles` be filled within each `Heat`; do all `Heats` contain a similar number of `Participants`; are Novices evenly distributed across `Heats`; etc.), and keeps iterating until all criteria are met.

- The dictionary of roles and their minimum requirements per heat is semi-hardcoded in [utils.py](./source/utils.py)'s `roles_and_minima` definition:
  - The minimum number of instructors in a heat is equal to `number_of_novices` divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.
  - The minimum number of corner captains in a heat is equal to `number_of_stations`.

- Heat sizes are constrained to `mean_heat_size` of the `Event` +/- a `max_heat_size_delta`, which can be tuned in the configuration file.

- Novice distribution across heats is constrained to `mean_heat_novice_count` of the `Event` +/- a `max_heat_novice_delta`, which can be tuned in the configuration file.

> [!NOTE]
> **This is a minimum viable prototype product.** The documentation is simply this README file. It will be cleaned and made more generally applicable after it's gained some field experience at actual events.

## Contributing

We've made it easy to add your own algorithms:

- Algorithms receive a pre-instantiated `Event` and must assign `Categories` to `Heats`, and assign roles to all `Participants` by mutating the `Event` within a `generate()` function.

  - See how the `generate()` function is called in [autologic.py](./source/autologic.py).

- Any class in `./source/algorithms` decorated with `@register` is auto-discovered and exposed as an `--algorithm` choice in the CLI.

  - See [example.py](./source/algorithms/example.py) for a sample scaffold.

## Retrieval and use

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --config .\path\to\config_file.yaml --algorithm name_of_module` to generate heat and worker assignments for a set of configured parameters.

    - See [sample_event_config.yaml](./tests/sample_event_config.yaml) for an example of a configuration file.
    - See [sample_axware_export.tsv](./tests/sample_axware_export.tsv) (pulled from AXWare) and [sample_member_attributes.csv](./tests/sample_member_attributes.csv) (maintained by worker coordinators) for examples of the expected input data structures.
    - If no `--algorithm` argument is provided, [randomize.py](./source/algorithms/randomize.py) is used by default.

3. Load an `Event` configuration and manipulate it by executing `.\path\to\autologic.exe --load .\path\to\event.pkl` and follow the prompts to:

    - Move a `Category` to a different `Heat`
    - Rotate `Heat` run/work groups
    - Update a `Participant`' assignment
    - Run `Event` validation checks
    - Export data

## Examples

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

  Heat 1 (41 total, 14 novices)
  -----------------------------

    Car classes: [DSP, ES, FS, BS, GST, BST, AST, DP, XA, CSM]

    4 of 4 instructors required
    6 of 2 timings required
    5 of 2 grids required
    6 of 1 starts required
    9 of 5 captains required

    White, Evelyn       assigned to INSTRUCTOR
    Cruz, Layla         assigned to INSTRUCTOR
    Smith, Olivia       assigned to INSTRUCTOR
    Moore, Alexander    assigned to INSTRUCTOR
    Gutierrez, William  assigned to GRID
    Gibson, Sofia       assigned to GRID
    Williams, Emma      assigned to TIMING
    Allen, Samuel       assigned to TIMING
    Hughes, Samuel      assigned to CAPTAIN
    Rodriguez, Sofia    assigned to CAPTAIN
    Tran, Avery         assigned to CAPTAIN
    Young, Luna         assigned to CAPTAIN
    Harris, Michael     assigned to CAPTAIN
    Wilson, Amelia      assigned to START
    Wright, Victoria    assigned to WORKER
    Jackson, Harper     assigned to WORKER
    Kelly, Mia          assigned to WORKER
    Ward, Daniel        assigned to WORKER
    Stevens, Samuel     assigned to WORKER
    Ramos, Evelyn       assigned to WORKER
    Garcia, Liam        assigned to WORKER
    Martinez, Matthew   assigned to WORKER
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
    Cox, Abigail        assigned to WORKER
    Alvarez, Grace      assigned to WORKER
    Garcia, Emily       assigned to WORKER
    Thompson, Daniel    assigned to WORKER
    Adams, Penelope     assigned to WORKER
    Rodriguez, William  assigned to WORKER
    Cooper, Charlotte   assigned to WORKER

  Heat 2 (44 total, 18 novices)
  -----------------------------

    Car classes: [EVX, CAM-C, DS, SR, EST, CS, DST, XB, SST, SSC]

    5 of 4 instructors required
    9 of 2 timings required
    8 of 2 grids required
    7 of 1 starts required
    6 of 5 captains required

    Hamilton, Lucas     assigned to INSTRUCTOR
    Martin, Abigail     assigned to INSTRUCTOR
    Brown, Oliver       assigned to INSTRUCTOR
    Phillips, Zoey      assigned to INSTRUCTOR
    Clark, Jackson      assigned to CAPTAIN    (custom assignment)
    Robinson, Ella      assigned to CAPTAIN
    Reed, Lucas         assigned to CAPTAIN
    Medina, David       assigned to CAPTAIN
    Hall, Joseph        assigned to CAPTAIN
    Reyes, Hannah       assigned to GRID
    Lewis, Aiden        assigned to GRID
    Griffin, Evelyn     assigned to START
    Carter, Theodore    assigned to TIMING
    Alexander, Amelia   assigned to TIMING
    Anderson, Lucas     assigned to WORKER
    Bailey, Amelia      assigned to WORKER
    Jenkins, Elias      assigned to WORKER
    Morris, Mia         assigned to WORKER
    Long, Jack          assigned to WORKER
    Foster, Theodore    assigned to WORKER
    Peterson, Benjamin  assigned to WORKER
    Watson, Matthew     assigned to WORKER
    Herrera, Jackson    assigned to WORKER
    Myers, Penelope     assigned to WORKER
    Hayes, Matthew      assigned to WORKER
    Fisher, Sophia      assigned to WORKER
    Miller, Elijah      assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Russell, Layla      assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Patel, Chloe        assigned to WORKER
    Walker, David       assigned to WORKER
    Stewart, Isaac      assigned to WORKER
    Gray, Avery         assigned to WORKER
    Morgan, James       assigned to WORKER
    Perry, Aria         assigned to WORKER
    Simmons, Isabella   assigned to WORKER
    Bryant, Ella        assigned to WORKER
    West, Daniel        assigned to WORKER
    Cole, Emily         assigned to WORKER
    Ellis, Aiden        assigned to WORKER
    Richardson, Emily   assigned to WORKER
    Green, Chloe        assigned to WORKER
    Ford, Grace         assigned to WORKER

  Heat 3 (38 total, 9 novices)
  ----------------------------

    Car classes: [P, GS, AS, CST, HS, CAM-T, SMF, SM, FP, ESP]

    7 of 3 instructors required
    6 of 2 timings required
    10 of 2 grids required
    6 of 1 starts required
    7 of 5 captains required

    Taylor, Henry       assigned to SPECIAL
    Thomas, Mia         assigned to SPECIAL
    Reynolds, Henry     assigned to CAPTAIN
    Graham, Mia         assigned to CAPTAIN
    Jordan, Charlotte   assigned to CAPTAIN
    Edwards, Eleanor    assigned to CAPTAIN
    Davis, Sophia       assigned to CAPTAIN
    Johnson, Noah       assigned to INSTRUCTOR (custom assignment)
    Turner, Elias       assigned to INSTRUCTOR
    Patterson, Benjamin assigned to INSTRUCTOR
    Nelson, Lily        assigned to TIMING
    Rogers, Sophia      assigned to TIMING
    Gonzalez, Benjamin  assigned to START
    Lopez, Charlotte    assigned to GRID
    Baker, Jack         assigned to GRID
    Wallace, Michael    assigned to WORKER
    Murphy, Oliver      assigned to WORKER
    King, Grace         assigned to WORKER
    Jimenez, Zoey       assigned to WORKER
    Evans, Nathan       assigned to WORKER
    Hughes, Samuel      assigned to WORKER
    Barnes, Oliver      assigned to WORKER
    Moreno, Abigail     assigned to WORKER
    Scott, Leo          assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Vasquez, William    assigned to WORKER
    Gray, Avery         assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Cook, Elijah        assigned to WORKER
    Aguilar, Joseph     assigned to WORKER
    Coleman, Hannah     assigned to WORKER
    Jones, Ava          assigned to WORKER
    Foster, Theodore    assigned to WORKER
    Hernandez, James    assigned to WORKER
    Murray, Luna        assigned to WORKER
    Stewart, Isaac      assigned to WORKER
    Ortiz, Isabella     assigned to WORKER
    Henderson, Mia      assigned to WORKER

  ---

  >>> Iteration 1 accepted <<<

  ==============================================================================

  [Event validation checks]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 1 (41 total, 14 novices)
  -----------------------------

    Car classes: [DSP, ES, FS, BS, GST, BST, AST, DP, XA, CSM]

    4 of 4 instructors assigned
    2 of 2 timings assigned
    2 of 2 grids assigned
    1 of 1 starts assigned
    5 of 5 captains assigned

  Heat 2 (44 total, 18 novices)
  -----------------------------

    Car classes: [EVX, CAM-C, DS, SR, EST, CS, DST, XB, SST, SSC]

    4 of 4 instructors assigned
    2 of 2 timings assigned
    2 of 2 grids assigned
    1 of 1 starts assigned
    5 of 5 captains assigned

  Heat 3 (38 total, 9 novices)
  ----------------------------

    Car classes: [P, GS, AS, CST, HS, CAM-T, SMF, SM, FP, ESP]

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

Heat 1 | Running 1 | Working 2 | P, GS, AS, CST, HS, CAM-T, SMF, SM, FP, ESP
Heat 2 | Running 2 | Working 3 | DSP, ES, FS, BS, GST, BST, AST, DP, XA, CSM
Heat 3 | Running 3 | Working 1 | EVX, CAM-C, DS, SR, EST, CS, DST, XB, SST, SSC

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

Save Event as: modified-event

  Worker assignment sheet saved to modified-event.csv

  Worker assignment printout saved to modified-event.pdf

  Event state saved to modified-event.pkl
```
