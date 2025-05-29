# Autologic

Somewhat questionable Python program that takes an autocross event roster and generates heat + worker assignments.

It provides a rough framework that may be used to assign `Categories` (car classes) to `Heats`, and `Participants` to `Roles` (specialized work assignments).

The current "algorithm" loads an `Event`, randomly assigns `Categories` to `Heats`, checks against acceptance criteria (can all `Roles` be filled within each `Heat` / do all `Heats` contain a similar number of `Participants` / are Novices evenly distributed / etc.), and keeps iterating until all criteria are met.

Better documentation to come... if there is interest. A smarter algorithm may be implemented later. Tests may be implemented later.

## Retrieval and usage

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --config .\path\to\config_file.yaml` to generate heat and worker assignments for a set of configured parameters.

### Notes

- See [sample_event_config.yaml](./tests/sample_event_config.yaml) for an example of a configuration file.

- See [sample_axware_export.tsv](./tests/sample_axware_export.tsv) and [sample_member_attributes.csv](./tests/sample_member_attributes.csv) for examples of the expected input data structures. May change to accommodate different configurations.

- The dictionary of roles and their minimum requirements per heat is semi-hardcoded in [utils.py](./source/utils.py)'s `roles_and_minima` definition.
  - The minimum number of instructors in a heat is equal to `number_of_novices` divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.
  - The minimum number of corner captains in a heat is equal to `number_of_stations`.

## Sample output

A CSV export function may be implemented later. For now, it's just this:

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

  Heat 0 (45 total, 14 novices)
  -----------------------------

    Car classes: [CAM-C, DS, GST, BST, HS, SSC, SMF, XB, SM, ESP]

    4 of 5 instructors required

    Heat 0 rejected: unable to fill INSTRUCTOR role(s)

  ==================================================

  [Iteration 20]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 0 (37 total, 12 novices)
  -----------------------------

    Car classes: [EVX, CAM-T, DSP, EP, GST, AS, CST, HS, XB, CSM]

    7 of 4 instructors required
    8 of 2 timings required
    7 of 2 grids required
    5 of 1 starts required
    6 of 5 captains required

    Taylor, Henry       assigned to SPECIAL
    Anderson, Lucas     assigned to CAPTAIN
    Davis, Sophia       assigned to CAPTAIN
    Jordan, Charlotte   assigned to CAPTAIN
    Edwards, Eleanor    assigned to CAPTAIN
    Hall, Joseph        assigned to CAPTAIN
    Johnson, Noah       assigned to INSTRUCTOR (custom assignment)
    Turner, Elias       assigned to INSTRUCTOR
    Patterson, Benjamin assigned to INSTRUCTOR
    Evans, Nathan       assigned to INSTRUCTOR
    Lewis, Aiden        assigned to START
    Hayes, Matthew      assigned to GRID
    Gray, Avery         assigned to GRID
    Allen, Samuel       assigned to TIMING
    Ellis, Aiden        assigned to TIMING
    Jones, Ava          assigned to WORKER
    Foster, Theodore    assigned to WORKER
    Hernandez, James    assigned to WORKER
    Wright, Victoria    assigned to WORKER
    Coleman, Hannah     assigned to WORKER
    Romero, James       assigned to WORKER
    Mendoza, David      assigned to WORKER
    Wilson, Amelia      assigned to WORKER
    Hughes, Samuel      assigned to WORKER
    Barnes, Oliver      assigned to WORKER
    Moreno, Abigail     assigned to WORKER
    Scott, Leo          assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Vasquez, William    assigned to WORKER
    Chavez, Jackson     assigned to WORKER
    Cook, Elijah        assigned to WORKER
    Aguilar, Joseph     assigned to WORKER
    Coleman, Hannah     assigned to WORKER
    West, Daniel        assigned to WORKER
    Cole, Emily         assigned to WORKER
    Richardson, Emily   assigned to WORKER
    Moore, Alexander    assigned to WORKER

  Heat 1 (40 total, 10 novices)
  -----------------------------

    Car classes: [DS, GS, BS, SSC, AST, SMF, DP, SM, XA, ESP]

    3 of 3 instructors required
    8 of 2 timings required
    12 of 2 grids required
    6 of 1 starts required
    8 of 5 captains required

    Thomas, Mia         assigned to SPECIAL
    Hamilton, Lucas     assigned to INSTRUCTOR
    Martin, Abigail     assigned to INSTRUCTOR
    Wallace, Michael    assigned to INSTRUCTOR
    Robinson, Ella      assigned to CAPTAIN
    Myers, Penelope     assigned to CAPTAIN
    Graham, Mia         assigned to CAPTAIN
    Hughes, Samuel      assigned to CAPTAIN
    Young, Luna         assigned to CAPTAIN
    Rogers, Sophia      assigned to START
    Nelson, Lily        assigned to TIMING
    Howard, Henry       assigned to TIMING
    Reyes, Hannah       assigned to GRID
    Ramos, Evelyn       assigned to GRID
    Foster, Theodore    assigned to WORKER
    Peterson, Benjamin  assigned to WORKER
    Watson, Matthew     assigned to WORKER
    Herrera, Jackson    assigned to WORKER
    Murphy, Oliver      assigned to WORKER
    King, Grace         assigned to WORKER
    Jimenez, Zoey       assigned to WORKER
    Ruiz, Joseph        assigned to WORKER
    Brooks, Ella        assigned to WORKER
    Martinez, Isabella  assigned to WORKER
    Turner, Elias       assigned to WORKER
    Powell, Nathan      assigned to WORKER
    Castillo, Victoria  assigned to WORKER
    Miller, Elijah      assigned to WORKER
    Ford, Grace         assigned to WORKER
    Thompson, Daniel    assigned to WORKER
    Gonzalez, Benjamin  assigned to WORKER
    Lopez, Charlotte    assigned to WORKER
    Baker, Jack         assigned to WORKER
    Murray, Luna        assigned to WORKER
    Adams, Penelope     assigned to WORKER
    Rodriguez, William  assigned to WORKER
    Stewart, Isaac      assigned to WORKER
    Cooper, Charlotte   assigned to WORKER
    Harris, Michael     assigned to WORKER
    Henderson, Mia      assigned to WORKER

  Heat 2 (46 total, 19 novices)
  -----------------------------

    Car classes: [CAM-C, CS, ES, FS, EST, BST, DST, SST, FP]

    6 of 6 instructors required
    10 of 2 timings required
    12 of 2 grids required
    13 of 1 starts required
    12 of 5 captains required

    Clark, Jackson      assigned to SPECIAL
    Brown, Oliver       assigned to INSTRUCTOR
    White, Evelyn       assigned to INSTRUCTOR
    Cruz, Layla         assigned to INSTRUCTOR
    Smith, Olivia       assigned to INSTRUCTOR
    Phillips, Zoey      assigned to INSTRUCTOR
    Alexander, Amelia   assigned to INSTRUCTOR
    Reynolds, Henry     assigned to CAPTAIN
    Walker, David       assigned to CAPTAIN
    Gibson, Sofia       assigned to CAPTAIN
    Williams, Emma      assigned to CAPTAIN
    Alvarez, Grace      assigned to CAPTAIN
    Carter, Theodore    assigned to TIMING
    Bryant, Ella        assigned to TIMING
    Stewart, Isaac      assigned to GRID
    Gray, Avery         assigned to GRID
    Griffin, Evelyn     assigned to START
    Bailey, Amelia      assigned to WORKER
    Jenkins, Elias      assigned to WORKER
    Morris, Mia         assigned to WORKER
    Long, Jack          assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Russell, Layla      assigned to WORKER
    Sullivan, Eleanor   assigned to WORKER
    Patel, Chloe        assigned to WORKER
    Morgan, James       assigned to WORKER
    Perry, Aria         assigned to WORKER
    Jackson, Harper     assigned to WORKER
    Gutierrez, William  assigned to WORKER
    Kelly, Mia          assigned to WORKER
    Ward, Daniel        assigned to WORKER
    Stevens, Samuel     assigned to WORKER
    Ramos, Evelyn       assigned to WORKER
    Garcia, Liam        assigned to WORKER
    Martinez, Matthew   assigned to WORKER
    Fisher, Sophia      assigned to WORKER
    Miller, Elijah      assigned to WORKER
    Cox, Abigail        assigned to WORKER
    Garcia, Emily       assigned to WORKER
    Rodriguez, Sofia    assigned to WORKER
    Tran, Avery         assigned to WORKER
    Reed, Lucas         assigned to WORKER
    Simmons, Isabella   assigned to WORKER
    Medina, David       assigned to WORKER
    Green, Chloe        assigned to WORKER
    Ortiz, Isabella     assigned to WORKER

  ---

  >>> Iteration 1 accepted <<<

  The following individuals have not checked in and are therefore excluded:

  - Simmons, Isabella
  - Parker, Aria
  - Castillo, Victoria

  Worker assignment sheet saved to autologic-export.csv

  Worker assignment printout saved to autologic-export.pdf
```
