# Autologic

Somewhat questionable Python program that takes an autocross event roster and generates heat + worker assignments.

It provides a rough framework that may be used to assign `Categories` (car classes) to `Heats`, and `Participants` to `Roles` (specialized work assignments).

The current "algorithm" loads an `Event`, randomly assigns `Categories` to `Heats`, checks against acceptance criteria (can all `Roles` be filled within each `Heat`?), and keeps iterating until all criteria are met.

Better documentation to come... if there is interest. A smarter algorithm may be implemented later. Tests may be implemented later.

## Retrieval and usage

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --axware-export .\path\to\file.tsv --member-attributes .\path\to\file.csv` to generate heat and worker assignments for a set of default parameters.

### Notes

- Run `autologic.exe --help` for more options (number of heats, number of worker stations, etc.).

- See [sample_axware_export.tsv](./tests/sample_axware_export.tsv) and [sample_member_attributes.csv](./tests/sample_member_attributes.csv) for examples of the required input data structures. May change to accommodate different configurations. The `special` role is for VPs, worker coordinators, tech inspectors, gate workers, etc. who should not be assigned to another role.

- The dictionary of roles and their minimum requirements per heat is semi-hardcoded in [utils.py](./source/utils.py)'s `roles_and_minima` definition.
  - The minimum number of instructors in a heat is equal to `number_of_novices` divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.
  - The minimum number of corner captains in a heat is equal to `number_of_stations`.

## Sample output

A CSV export function may be implemented later. For now, it's just this:

```powershell
(autologic) PS C:\codes\autologic> .\dist\autologic.exe --axware-export .\tests\sample_axware_export.tsv --member-attributes .\tests\sample_member_attributes.csv

  The following individuals have not checked in and will be omitted:

  - Isabella Simmons
  - Aria Parker
  - Victoria Castillo

  Role minimums
  -------------
  instructor: 17 / 15
      timing: 27 / 6
        grid: 32 / 6
       start: 26 / 3
     captain: 27 / 15

  ==================================================

  [Iteration 0]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 0 rejected: participant count of 48

  ==================================================

  [Iteration 2]

  Heat size must be 41 +/- 5
  Novice count must be 14 +/- 5

  Heat 0 (40 total, 13 novices)
  -----------------------------

    Car classes: [DS, DSP, BS, BST, HS, SST, DP, XA, FP, ESP]

    4 of 4 instructors required
    9 of 2 timings required
    11 of 2 grids required
    7 of 1 starts required
    9 of 5 captains required

    Lucas Hamilton     assigned to INSTRUCTOR
    Abigail Martin     assigned to INSTRUCTOR
    Elias Turner       assigned to INSTRUCTOR
    Olivia Smith       assigned to INSTRUCTOR
    Ella Robinson      assigned to CAPTAIN
    Penelope Myers     assigned to CAPTAIN
    Samuel Hughes      assigned to CAPTAIN
    Grace Alvarez      assigned to CAPTAIN
    Sofia Rodriguez    assigned to CAPTAIN
    Theodore Foster    assigned to START
    Henry Howard       assigned to TIMING
    Avery Gray         assigned to TIMING
    Hannah Reyes       assigned to GRID
    Evelyn Ramos       assigned to GRID
    Benjamin Peterson  assigned to WORKER-0
    Matthew Watson     assigned to WORKER-1
    Jackson Herrera    assigned to WORKER-2
    Victoria Wright    assigned to WORKER-3
    Joseph Ruiz        assigned to WORKER-4
    Ella Brooks        assigned to WORKER-0
    Isabella Martinez  assigned to WORKER-1
    Nathan Powell      assigned to WORKER-2
    Victoria Castillo  assigned to WORKER-3
    Elijah Miller      assigned to WORKER-4
    Abigail Cox        assigned to WORKER-0
    Emily Garcia       assigned to WORKER-1
    Avery Tran         assigned to WORKER-2
    William Vasquez    assigned to WORKER-3
    Jackson Chavez     assigned to WORKER-4
    Elijah Cook        assigned to WORKER-0
    Joseph Aguilar     assigned to WORKER-1
    Eleanor Edwards    assigned to WORKER-2
    Hannah Coleman     assigned to WORKER-3
    Chloe Green        assigned to WORKER-4
    Penelope Adams     assigned to WORKER-0
    William Rodriguez  assigned to WORKER-1
    Charlotte Cooper   assigned to WORKER-2
    Michael Harris     assigned to WORKER-3
    Isabella Ortiz     assigned to WORKER-4
    Mia Henderson      assigned to WORKER-0

  Heat 1 (39 total, 11 novices)
  -----------------------------

    Car classes: [EVX, CAM-T, ES, GS, EP, GST, AS, AST, SMF, CSM]

    6 of 4 instructors required
    7 of 2 timings required
    10 of 2 grids required
    10 of 1 starts required
    10 of 5 captains required

    Noah Johnson       assigned to INSTRUCTOR
    Evelyn White       assigned to INSTRUCTOR
    Elias Turner       assigned to INSTRUCTOR
    Benjamin Patterson assigned to INSTRUCTOR
    Sofia Gibson       assigned to TIMING
    Lily Nelson        assigned to TIMING
    Lucas Anderson     assigned to CAPTAIN
    Sophia Davis       assigned to CAPTAIN
    Mia Graham         assigned to CAPTAIN
    Samuel Hughes      assigned to CAPTAIN
    Luna Young         assigned to CAPTAIN
    Aiden Lewis        assigned to GRID
    William Gutierrez  assigned to GRID
    Theodore Foster    assigned to START
    Ava Jones          assigned to WORKER-0
    James Hernandez    assigned to WORKER-1
    Harper Jackson     assigned to WORKER-2
    Mia Kelly          assigned to WORKER-3
    Daniel Ward        assigned to WORKER-4
    Samuel Stevens     assigned to WORKER-0
    Oliver Murphy      assigned to WORKER-1
    Grace King         assigned to WORKER-2
    Zoey Jimenez       assigned to WORKER-3
    Sophia Rogers      assigned to WORKER-4
    Hannah Coleman     assigned to WORKER-0
    James Romero       assigned to WORKER-1
    David Mendoza      assigned to WORKER-2
    Amelia Wilson      assigned to WORKER-3
    Samuel Allen       assigned to WORKER-4
    Nathan Evans       assigned to WORKER-0
    Oliver Barnes      assigned to WORKER-1
    Matthew Hayes      assigned to WORKER-2
    Daniel Thompson    assigned to WORKER-3
    Benjamin Gonzalez  assigned to WORKER-4
    Charlotte Lopez    assigned to WORKER-0
    Jack Baker         assigned to WORKER-1
    Mia Thomas         assigned to WORKER-2
    Luna Murray        assigned to WORKER-3
    Alexander Moore    assigned to WORKER-4

  Heat 2 (44 total, 17 novices)
  -----------------------------

    Car classes: [CAM-C, CS, FS, EST, CST, SSC, DST, XB, SM]

    7 of 6 instructors required
    11 of 2 timings required
    11 of 2 grids required
    9 of 1 starts required
    8 of 5 captains required

    Oliver Brown       assigned to INSTRUCTOR
    Layla Cruz         assigned to INSTRUCTOR
    Henry Taylor       assigned to INSTRUCTOR
    Abigail Moreno     assigned to INSTRUCTOR
    Michael Wallace    assigned to INSTRUCTOR
    Zoey Phillips      assigned to INSTRUCTOR
    Henry Reynolds     assigned to CAPTAIN
    David Walker       assigned to CAPTAIN
    Emma Williams      assigned to CAPTAIN
    Charlotte Jordan   assigned to CAPTAIN
    Lucas Reed         assigned to CAPTAIN
    Evelyn Griffin     assigned to START
    Avery Gray         assigned to TIMING
    Theodore Carter    assigned to TIMING
    Isaac Stewart      assigned to GRID
    Evelyn Ramos       assigned to GRID
    Amelia Bailey      assigned to WORKER-0
    Elias Jenkins      assigned to WORKER-1
    Mia Morris         assigned to WORKER-2
    Jackson Clark      assigned to WORKER-3
    Jack Long          assigned to WORKER-4
    Eleanor Sullivan   assigned to WORKER-0
    Layla Russell      assigned to WORKER-1
    Eleanor Sullivan   assigned to WORKER-2
    Chloe Patel        assigned to WORKER-3
    James Morgan       assigned to WORKER-4
    Aria Perry         assigned to WORKER-0
    Liam Garcia        assigned to WORKER-1
    Matthew Martinez   assigned to WORKER-2
    Sophia Fisher      assigned to WORKER-3
    Elijah Miller      assigned to WORKER-4
    Leo Scott          assigned to WORKER-0
    Jackson Chavez     assigned to WORKER-1
    Grace Ford         assigned to WORKER-2
    Isabella Simmons   assigned to WORKER-3
    Amelia Alexander   assigned to WORKER-4
    Ella Bryant        assigned to WORKER-0
    David Medina       assigned to WORKER-1
    Joseph Hall        assigned to WORKER-2
    Daniel West        assigned to WORKER-3
    Emily Cole         assigned to WORKER-4
    Aiden Ellis        assigned to WORKER-0
    Emily Richardson   assigned to WORKER-1
    Isaac Stewart      assigned to WORKER-2

  ---

  >>> Iteration 1 accepted <<<
```
