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
    Jones, Ava          assigned to WORKER-0
    Foster, Theodore    assigned to WORKER-1
    Hernandez, James    assigned to WORKER-2
    Wright, Victoria    assigned to WORKER-3
    Coleman, Hannah     assigned to WORKER-4
    Romero, James       assigned to WORKER-0
    Mendoza, David      assigned to WORKER-1
    Wilson, Amelia      assigned to WORKER-2
    Hughes, Samuel      assigned to WORKER-3
    Barnes, Oliver      assigned to WORKER-4
    Moreno, Abigail     assigned to WORKER-0
    Scott, Leo          assigned to WORKER-1
    Chavez, Jackson     assigned to WORKER-2
    Vasquez, William    assigned to WORKER-3
    Chavez, Jackson     assigned to WORKER-4
    Cook, Elijah        assigned to WORKER-0
    Aguilar, Joseph     assigned to WORKER-1
    Coleman, Hannah     assigned to WORKER-2
    West, Daniel        assigned to WORKER-3
    Cole, Emily         assigned to WORKER-4
    Richardson, Emily   assigned to WORKER-0
    Moore, Alexander    assigned to WORKER-1

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
    Foster, Theodore    assigned to WORKER-0
    Peterson, Benjamin  assigned to WORKER-1
    Watson, Matthew     assigned to WORKER-2
    Herrera, Jackson    assigned to WORKER-3
    Murphy, Oliver      assigned to WORKER-4
    King, Grace         assigned to WORKER-0
    Jimenez, Zoey       assigned to WORKER-1
    Ruiz, Joseph        assigned to WORKER-2
    Brooks, Ella        assigned to WORKER-3
    Martinez, Isabella  assigned to WORKER-4
    Turner, Elias       assigned to WORKER-0
    Powell, Nathan      assigned to WORKER-1
    Castillo, Victoria  assigned to WORKER-2
    Miller, Elijah      assigned to WORKER-3
    Ford, Grace         assigned to WORKER-4
    Thompson, Daniel    assigned to WORKER-0
    Gonzalez, Benjamin  assigned to WORKER-1
    Lopez, Charlotte    assigned to WORKER-2
    Baker, Jack         assigned to WORKER-3
    Murray, Luna        assigned to WORKER-4
    Adams, Penelope     assigned to WORKER-0
    Rodriguez, William  assigned to WORKER-1
    Stewart, Isaac      assigned to WORKER-2
    Cooper, Charlotte   assigned to WORKER-3
    Harris, Michael     assigned to WORKER-4
    Henderson, Mia      assigned to WORKER-0

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
    Bailey, Amelia      assigned to WORKER-0
    Jenkins, Elias      assigned to WORKER-1
    Morris, Mia         assigned to WORKER-2
    Long, Jack          assigned to WORKER-3
    Sullivan, Eleanor   assigned to WORKER-4
    Russell, Layla      assigned to WORKER-0
    Sullivan, Eleanor   assigned to WORKER-1
    Patel, Chloe        assigned to WORKER-2
    Morgan, James       assigned to WORKER-3
    Perry, Aria         assigned to WORKER-4
    Jackson, Harper     assigned to WORKER-0
    Gutierrez, William  assigned to WORKER-1
    Kelly, Mia          assigned to WORKER-2
    Ward, Daniel        assigned to WORKER-3
    Stevens, Samuel     assigned to WORKER-4
    Ramos, Evelyn       assigned to WORKER-0
    Garcia, Liam        assigned to WORKER-1
    Martinez, Matthew   assigned to WORKER-2
    Fisher, Sophia      assigned to WORKER-3
    Miller, Elijah      assigned to WORKER-4
    Cox, Abigail        assigned to WORKER-0
    Garcia, Emily       assigned to WORKER-1
    Rodriguez, Sofia    assigned to WORKER-2
    Tran, Avery         assigned to WORKER-3
    Reed, Lucas         assigned to WORKER-4
    Simmons, Isabella   assigned to WORKER-0
    Medina, David       assigned to WORKER-1
    Green, Chloe        assigned to WORKER-2
    Ortiz, Isabella     assigned to WORKER-3

  ---

  >>> Iteration 1 accepted <<<

  The following individuals have not checked in and are therefore excluded:

  - Simmons, Isabella
  - Parker, Aria
  - Castillo, Victoria

  Worker assignment sheet saved to autologic-export.csv
```
