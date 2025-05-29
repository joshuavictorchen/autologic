# Autologic

This program generates heat + worker assignments for autocross events.

It provides a framework that may be used to assign `Categories` (car classes) to `Heats`, and `Participants` to `Roles` (specialized work assignments).

The default algorithm loads an `Event`, randomly assigns `Categories` to `Heats`, checks against acceptance criteria (can all `Roles` be filled within each `Heat`; do all `Heats` contain a similar number of `Participants`; are Novices evenly distributed across `Heats`; etc.), and keeps iterating until all criteria are met.

> [!NOTE]
> **This is a minimum viable prototype product.** The main code is untested semi-hardcoded spaghetti. The documentation is simply this README file. It will be cleaned and made more generally applicable after it's gained some field experience at actual events.

All names found in the sample files and documentation within this repository are fictional and have been randomly generated.

## Retrieval and usage

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --config .\path\to\config_file.yaml` to generate heat and worker assignments for a set of configured parameters.

### Notes

- See [sample_event_config.yaml](./tests/sample_event_config.yaml) for an example of a configuration file.
  - See [sample_axware_export.tsv](./tests/sample_axware_export.tsv) (pulled from AXWare) and [sample_member_attributes.csv](./tests/sample_member_attributes.csv) (maintained by worker coordinators) for examples of the expected input data structures.

- The dictionary of roles and their minimum requirements per heat is semi-hardcoded in [utils.py](./source/utils.py)'s `roles_and_minima` definition:
  - The minimum number of instructors in a heat is equal to `number_of_novices` divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.
  - The minimum number of corner captains in a heat is equal to `number_of_stations`.

- Heat sizes are constrained to `mean_group_size` of the `Event` +/- a `max_group_delta`, which can be tuned in the configuration file.

- Novice distribution across heats is constrained to `mean_novice_count` of the `Event` +/- a `max_novice_delta`, which can be tuned in the configuration file.

## Sample execution

```powershell
(autologic) PS C:\codes\autologic> .\dist\autologic.exe --config .\dist\sample_event_config.yaml

  Role minimums
  -------------
  instructor: 16 / 15
      timing: 26 / 6
        grid: 31 / 6
       start: 24 / 3
     captain: 26 / 15

  ==================================================

  [Iteration 0]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 0 rejected: novice count of 8

  ==================================================

  [Iteration 1]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 0 (38 total, 10 novices)
  -----------------------------

    Car classes: [CAM-C, DS, SR, ES, AS, XB, SST, DP, SM, XA]

    4 of 3 instructors required
    8 of 2 timings required
    13 of 2 grids required
    7 of 1 starts required
    7 of 5 captains required

    Clark, Jackson      assigned to SPECIAL
    Hamilton, Lucas     assigned to INSTRUCTOR
    Martin, Abigail     assigned to INSTRUCTOR
    White, Evelyn       assigned to INSTRUCTOR
    Robinson, Ella      assigned to CAPTAIN
    Myers, Penelope     assigned to CAPTAIN
    Gibson, Sofia       assigned to CAPTAIN
    Hall, Joseph        assigned to CAPTAIN
    Green, Chloe        assigned to CAPTAIN
    Ellis, Aiden        assigned to TIMING
    Harris, Michael     assigned to TIMING
    Lewis, Aiden        assigned to START
    Reyes, Hannah       assigned to GRID
    Hayes, Matthew      assigned to GRID
    Bailey, Amelia      assigned to WORKER
    Jenkins, Elias      assigned to WORKER
    Morris, Mia         assigned to WORKER
    Long, Jack          assigned to WORKER
    Foster, Theodore    assigned to WORKER
    Peterson, Benjamin  assigned to WORKER
    Watson, Matthew     assigned to WORKER
    Herrera, Jackson    assigned to WORKER
    Griffin, Evelyn     assigned to WORKER
    Jackson, Harper     assigned to WORKER
    Gutierrez, William  assigned to WORKER
    Kelly, Mia          assigned to WORKER
    Ward, Daniel        assigned to WORKER
    Stevens, Samuel     assigned to WORKER
    Evans, Nathan       assigned to WORKER
    Hughes, Samuel      assigned to WORKER
    Barnes, Oliver      assigned to WORKER
    West, Daniel        assigned to WORKER
    Cole, Emily         assigned to WORKER
    Richardson, Emily   assigned to WORKER
    Adams, Penelope     assigned to WORKER
    Rodriguez, William  assigned to WORKER
    Stewart, Isaac      assigned to WORKER
    Cooper, Charlotte   assigned to WORKER

  Heat 1 (39 total, 13 novices)
  -----------------------------

    Car classes: [P, EST, BS, GST, HS, CAM-T, FP, CSM, ESP, SSC]

    5 of 4 instructors required
    7 of 2 timings required
    6 of 2 grids required
    7 of 1 starts required
    5 of 5 captains required

    Reynolds, Henry     assigned to CAPTAIN
    Hughes, Samuel      assigned to CAPTAIN
    Edwards, Eleanor    assigned to CAPTAIN
    Davis, Sophia       assigned to CAPTAIN
    Moore, Alexander    assigned to CAPTAIN
    Johnson, Noah       assigned to INSTRUCTOR (custom assignment)
    Turner, Elias       assigned to INSTRUCTOR
    Patterson, Benjamin assigned to INSTRUCTOR
    Wallace, Michael    assigned to INSTRUCTOR
    Howard, Henry       assigned to GRID
    Ramos, Evelyn       assigned to GRID
    Carter, Theodore    assigned to TIMING
    Allen, Samuel       assigned to TIMING
    Gonzalez, Benjamin  assigned to START
    Fisher, Sophia      assigned to WORKER
    Miller, Elijah      assigned to WORKER
    Ruiz, Joseph        assigned to WORKER
    Brooks, Ella        assigned to WORKER
    Martinez, Isabella  assigned to WORKER
    Turner, Elias       assigned to WORKER
    Powell, Nathan      assigned to WORKER
    Castillo, Victoria  assigned to WORKER
    Miller, Elijah      assigned to WORKER
    Coleman, Hannah     assigned to WORKER
    Romero, James       assigned to WORKER
    Mendoza, David      assigned to WORKER
    Wilson, Amelia      assigned to WORKER
    Vasquez, William    assigned to WORKER
    Gray, Avery         assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Cook, Elijah        assigned to WORKER
    Aguilar, Joseph     assigned to WORKER
    Coleman, Hannah     assigned to WORKER
    Jones, Ava          assigned to WORKER
    Foster, Theodore    assigned to WORKER
    Hernandez, James    assigned to WORKER
    Ortiz, Isabella     assigned to WORKER
    Henderson, Mia      assigned to WORKER
    Ford, Grace         assigned to WORKER

  Heat 2 (46 total, 18 novices)
  -----------------------------

    Car classes: [EVX, DSP, GS, FS, CST, BST, AST, CS, DST, SMF]

    7 of 6 instructors required
    11 of 2 timings required
    12 of 2 grids required
    10 of 1 starts required
    14 of 5 captains required

    Taylor, Henry       assigned to SPECIAL
    Thomas, Mia         assigned to SPECIAL
    Cruz, Layla         assigned to INSTRUCTOR
    Moreno, Abigail     assigned to INSTRUCTOR
    Smith, Olivia       assigned to INSTRUCTOR
    Brown, Oliver       assigned to INSTRUCTOR
    Phillips, Zoey      assigned to INSTRUCTOR
    Alexander, Amelia   assigned to INSTRUCTOR
    Nelson, Lily        assigned to TIMING
    Rogers, Sophia      assigned to TIMING
    Jordan, Charlotte   assigned to START
    Anderson, Lucas     assigned to CAPTAIN
    Graham, Mia         assigned to CAPTAIN
    Williams, Emma      assigned to CAPTAIN
    Alvarez, Grace      assigned to CAPTAIN
    Rodriguez, Sofia    assigned to CAPTAIN
    Walker, David       assigned to GRID
    Stewart, Isaac      assigned to GRID
    Wright, Victoria    assigned to WORKER
    Murphy, Oliver      assigned to WORKER
    King, Grace         assigned to WORKER
    Jimenez, Zoey       assigned to WORKER
    Ramos, Evelyn       assigned to WORKER
    Garcia, Liam        assigned to WORKER
    Martinez, Matthew   assigned to WORKER
    Scott, Leo          assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Cox, Abigail        assigned to WORKER
    Garcia, Emily       assigned to WORKER
    Tran, Avery         assigned to WORKER
    Young, Luna         assigned to WORKER
    Thompson, Daniel    assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Russell, Layla      assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Patel, Chloe        assigned to WORKER
    Gray, Avery         assigned to WORKER
    Morgan, James       assigned to WORKER
    Perry, Aria         assigned to WORKER
    Reed, Lucas         assigned to WORKER
    Simmons, Isabella   assigned to WORKER
    Bryant, Ella        assigned to WORKER
    Medina, David       assigned to WORKER
    Lopez, Charlotte    assigned to WORKER
    Baker, Jack         assigned to WORKER
    Murray, Luna        assigned to WORKER

  ---

  >>> Iteration 1 accepted <<<

  The following individuals have not checked in and are therefore excluded:

  - Simmons, Isabella
  - Parker, Aria
  - Castillo, Victoria

  Worker assignment sheet saved to autologic-export.csv

  Worker assignment printout saved to autologic-export.pdf
```

## Sample PDF output

![sample-report](./docs/images/sample-report.png)
