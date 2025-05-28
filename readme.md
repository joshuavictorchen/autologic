# Autologic

Somewhat questionable Python program that takes an autocross event roster and generates heat + worker assignments.

It provides a rough framework that may be used to assign `Categories` (car classes) to `Heats`, and `Participants` to `Roles` (specialized work assignments).

The current "algorithm" loads an `Event`, randomly assigns `Categories` to `Heats`, checks against acceptance criteria (can all `Roles` be filled within each `Heat`?), and keeps iterating until all criteria are met.

Better documentation to come... if there is interest. A smarter algorithm may be implemented later. Tests may be implemented later.

## Retrieval and usage

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --csv .\path\to\file.csv` to generate heat and worker assignments for a set of default parameters.

### Notes

- Run `autologic.exe --help` for more options (number of heats, number of worker stations, etc.).

- See [sample_msr_export.csv](./tests/sample_msr_export.csv) and [sample_member_attributes.csv](./tests/sample_member_attributes.csv) for examples of the required input data structures. May change to accommodate different configurations. The `special` role is for VPs, worker coordinators, tech inspectors, gate workers, etc. who should not be assigned to another role.

- The dictionary of roles and their minimum requirements per heat is semi-hardcoded in [utils.py](./source/utils.py)'s `roles_and_minima` definition.
  - The minimum number of instructors in a heat is equal to `number_of_novices` divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.
  - The minimum number of corner captains in a heat is equal to `number_of_stations`.

## Sample output

A CSV export function may be implemented later. For now, it's just this:

```powershell
(autologic) PS C:\codes\autologic> .\dist\autologic.exe --msr-export .\dist\sample_msr_export.csv --member-attributes .\dist\sample_member_attributes.csv

  Role minimums
  -------------
  instructor: 16 / 15
      timing: 26 / 6
        grid: 31 / 6
       start: 25 / 3
     captain: 27 / 15

  ==================================================

  [Iteration 0]

  Heat size must be 42 +/- 6
  Novice count must be 14 +/- 5

  Heat 0 rejected: participant count of 35

  ==================================================

  [Iteration 1]

  Heat size must be 42 +/- 6
  Novice count must be 14 +/- 5

  Heat 0 (39 total, 11 novices)
  -----------------------------

    Car classes: [CAM-C, SR, DSP, FS, EST, GST, CST, CAM-T, XB, SST, SM]

    4 of 4 instructors required
    8 of 2 timings required
    8 of 2 grids required
    6 of 1 starts required
    5 of 5 captains required

    Layla Cruz         assigned to INSTRUCTOR
    Henry Taylor       assigned to INSTRUCTOR
    Abigail Moreno     assigned to INSTRUCTOR
    Noah Johnson       assigned to INSTRUCTOR
    Emma Williams      assigned to CAPTAIN
    Charlotte Jordan   assigned to CAPTAIN
    Sophia Davis       assigned to CAPTAIN
    Joseph Hall        assigned to CAPTAIN
    Chloe Green        assigned to CAPTAIN
    Aiden Lewis        assigned to START
    Theodore Carter    assigned to TIMING
    Samuel Allen       assigned to TIMING
    Matthew Hayes      assigned to GRID
    Emily Cole         assigned to GRID
    Amelia Bailey      assigned to WORKER-0
    Elias Jenkins      assigned to WORKER-1
    Mia Morris         assigned to WORKER-2
    Jackson Clark      assigned to WORKER-3
    Jack Long          assigned to WORKER-4
    Evelyn Griffin     assigned to WORKER-0
    Victoria Wright    assigned to WORKER-1
    Evelyn Ramos       assigned to WORKER-2
    Liam Garcia        assigned to WORKER-3
    Matthew Martinez   assigned to WORKER-4
    Sophia Fisher      assigned to WORKER-0
    Elijah Miller      assigned to WORKER-1
    Hannah Coleman     assigned to WORKER-2
    James Romero       assigned to WORKER-3
    David Mendoza      assigned to WORKER-4
    Amelia Wilson      assigned to WORKER-0
    Leo Scott          assigned to WORKER-1
    Jackson Chavez     assigned to WORKER-2
    Ava Jones          assigned to WORKER-3
    Theodore Foster    assigned to WORKER-4
    James Hernandez    assigned to WORKER-0
    Daniel West        assigned to WORKER-1
    Aiden Ellis        assigned to WORKER-2
    Emily Richardson   assigned to WORKER-3
    Isaac Stewart      assigned to WORKER-4

  Heat 1 (43 total, 18 novices)
  -----------------------------

    Car classes: [P, BS, AS, CS, DST, DP, XA, FP, CSM, ESP]

    8 of 6 instructors required
    9 of 2 timings required
    9 of 2 grids required
    8 of 1 starts required
    9 of 5 captains required

    Elias Turner       assigned to INSTRUCTOR
    Benjamin Patterson assigned to INSTRUCTOR
    Michael Wallace    assigned to INSTRUCTOR
    Nathan Evans       assigned to INSTRUCTOR
    Oliver Brown       assigned to INSTRUCTOR
    Zoey Phillips      assigned to INSTRUCTOR
    Henry Reynolds     assigned to CAPTAIN
    Samuel Hughes      assigned to CAPTAIN
    David Walker       assigned to CAPTAIN
    Lucas Reed         assigned to CAPTAIN
    David Medina       assigned to CAPTAIN
    Henry Howard       assigned to TIMING
    Amelia Alexander   assigned to TIMING
    Evelyn Ramos       assigned to GRID
    Isaac Stewart      assigned to GRID
    Benjamin Gonzalez  assigned to START
    Joseph Ruiz        assigned to WORKER-0
    Ella Brooks        assigned to WORKER-1
    Isabella Martinez  assigned to WORKER-2
    Elias Turner       assigned to WORKER-3
    Nathan Powell      assigned to WORKER-4
    Victoria Castillo  assigned to WORKER-0
    Elijah Miller      assigned to WORKER-1
    Samuel Hughes      assigned to WORKER-2
    Oliver Barnes      assigned to WORKER-3
    Eleanor Sullivan   assigned to WORKER-4
    Layla Russell      assigned to WORKER-0
    Eleanor Sullivan   assigned to WORKER-1
    Chloe Patel        assigned to WORKER-2
    Avery Gray         assigned to WORKER-3
    James Morgan       assigned to WORKER-4
    Aria Perry         assigned to WORKER-0
    Isabella Simmons   assigned to WORKER-1
    Ella Bryant        assigned to WORKER-2
    Aria Parker        assigned to WORKER-3
    Penelope Adams     assigned to WORKER-4
    William Rodriguez  assigned to WORKER-0
    Charlotte Cooper   assigned to WORKER-1
    Michael Harris     assigned to WORKER-2
    Victoria Castillo  assigned to WORKER-3
    Isabella Ortiz     assigned to WORKER-4
    Alexander Moore    assigned to WORKER-0
    Mia Henderson      assigned to WORKER-1

  Heat 2 (44 total, 13 novices)
  -----------------------------

    Car classes: [EVX, DS, ES, GS, BST, HS, AST, SMF, SSC, FSP]

    4 of 4 instructors required
    9 of 2 timings required
    14 of 2 grids required
    11 of 1 starts required
    13 of 5 captains required

    Lucas Hamilton     assigned to INSTRUCTOR
    Abigail Martin     assigned to INSTRUCTOR
    Evelyn White       assigned to INSTRUCTOR
    Olivia Smith       assigned to INSTRUCTOR
    Ella Robinson      assigned to TIMING
    Penelope Myers     assigned to TIMING
    Lucas Anderson     assigned to CAPTAIN
    Sofia Gibson       assigned to CAPTAIN
    Mia Graham         assigned to CAPTAIN
    Grace Alvarez      assigned to CAPTAIN
    Sofia Rodriguez    assigned to CAPTAIN
    William Gutierrez  assigned to START
    Hannah Reyes       assigned to GRID
    Sophia Rogers      assigned to GRID
    Theodore Foster    assigned to WORKER-0
    Benjamin Peterson  assigned to WORKER-1
    Matthew Watson     assigned to WORKER-2
    Jackson Herrera    assigned to WORKER-3
    Harper Jackson     assigned to WORKER-4
    Mia Kelly          assigned to WORKER-0
    Daniel Ward        assigned to WORKER-1
    Samuel Stevens     assigned to WORKER-2
    Oliver Murphy      assigned to WORKER-3
    Grace King         assigned to WORKER-4
    Lily Nelson        assigned to WORKER-0
    Zoey Jimenez       assigned to WORKER-1
    Abigail Cox        assigned to WORKER-2
    Emily Garcia       assigned to WORKER-3
    Avery Tran         assigned to WORKER-4
    William Vasquez    assigned to WORKER-0
    Avery Gray         assigned to WORKER-1
    Jackson Chavez     assigned to WORKER-2
    Elijah Cook        assigned to WORKER-3
    Joseph Aguilar     assigned to WORKER-4
    Eleanor Edwards    assigned to WORKER-0
    Hannah Coleman     assigned to WORKER-1
    Luna Young         assigned to WORKER-2
    Daniel Thompson    assigned to WORKER-3
    Charlotte Lopez    assigned to WORKER-4
    Jack Baker         assigned to WORKER-0
    Mia Thomas         assigned to WORKER-1
    Luna Murray        assigned to WORKER-2
    Grace Ford         assigned to WORKER-3
    Isabella Simmons   assigned to WORKER-4

  ---

  >>> Iteration 1 accepted <<<
```
