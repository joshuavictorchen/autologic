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
(autologic) PS C:\codes\autologic> .\dist\autologic.exe --csv .\dist\sample.csv

  Role minimums
  -------------
  instructor: 14 / 9
      timing:  9 / 6
        grid: 11 / 6
       start:  5 / 3
     captain: 40 / 15

  ==================================================

  [Iteration 0]

  Heat size must be 33 +/- 4
  Novice count must be 7 +/- 3

  Heat 0 rejected: participant count of 25

  ==================================================

  [Iteration 1]

  Heat size must be 33 +/- 4
  Novice count must be 7 +/- 3

  Heat 0 (33 total, 8 novices)
  ----------------------------

    Car classes: [a, f, i, j, k, r, u]

    4 of 3 instructors required
    2 of 2 timings required
    6 of 2 grids required
    1 of 1 starts required
    13 of 5 captains required

    Rachel Smith        assigned to TIMING
    Alice Martinez      assigned to TIMING
    Hannah Hernandez    assigned to START
    Charlie Anderson    assigned to INSTRUCTOR
    Olivia Thompson     assigned to INSTRUCTOR
    Alice Anderson      assigned to INSTRUCTOR
    Zane Harris         assigned to GRID
    Paul Moore          assigned to GRID
    Charlie Walker      assigned to CAPTAIN
    Ethan Clark         assigned to CAPTAIN
    Liam Jones          assigned to CAPTAIN
    Mia Lopez           assigned to CAPTAIN
    Noah Moore          assigned to CAPTAIN
    Isaac Wilson        assigned to WORKER-0
    Ursula Lopez        assigned to WORKER-1
    Mia Lewis           assigned to WORKER-2
    Samuel Harris       assigned to WORKER-3
    Mia Miller          assigned to WORKER-4
    Noah Jackson        assigned to WORKER-0
    Quinn Hernandez     assigned to WORKER-1
    Wendy Jackson       assigned to WORKER-2
    Frank Hall          assigned to WORKER-3
    Paul Lewis          assigned to WORKER-4
    Sophia Gonzalez     assigned to WORKER-0
    Sophia White        assigned to WORKER-1
    Henry Lopez         assigned to WORKER-2
    Liam Miller         assigned to WORKER-3
    Victor Taylor       assigned to WORKER-4
    Samuel Thomas       assigned to WORKER-0
    Charlie Harris      assigned to WORKER-1
    Ursula Thompson     assigned to WORKER-2
    Samuel Martinez     assigned to WORKER-3
    Tina Rodriguez      assigned to WORKER-4

  Heat 1 (34 total, 8 novices)
  ----------------------------

    Car classes: [c, d, g, h, l, m, p]

    5 of 3 instructors required
    5 of 2 timings required
    3 of 2 grids required
    1 of 1 starts required
    12 of 5 captains required

    Wendy Johnson       assigned to START
    Yvonne White        assigned to GRID
    Isaac Lee           assigned to GRID
    Bob Martin          assigned to INSTRUCTOR
    Grace Jones         assigned to INSTRUCTOR
    Ethan White         assigned to INSTRUCTOR
    David Brown         assigned to TIMING
    Alice Jones         assigned to TIMING
    Bob Davis           assigned to CAPTAIN
    Isabelle Williams   assigned to CAPTAIN
    Frank Jones         assigned to CAPTAIN
    Charlie Thomas      assigned to CAPTAIN
    Rachel Martin       assigned to CAPTAIN
    Jack Rodriguez      assigned to WORKER-0
    Jack Martin         assigned to WORKER-1
    Katherine Rodriguez assigned to WORKER-2
    Yvonne Walker       assigned to WORKER-3
    Hannah Hall         assigned to WORKER-4
    Liam Garcia         assigned to WORKER-0
    Xavier Clark        assigned to WORKER-1
    Isabelle Thompson   assigned to WORKER-2
    Grace Hernandez     assigned to WORKER-3
    Olivia Perez        assigned to WORKER-4
    Ethan Anderson      assigned to WORKER-0
    Samuel Taylor       assigned to WORKER-1
    Liam Jackson        assigned to WORKER-2
    Bob Gonzalez        assigned to WORKER-3
    Tina Anderson       assigned to WORKER-4
    Grace Johnson       assigned to WORKER-0
    Bob Lewis           assigned to WORKER-1
    Olivia Martin       assigned to WORKER-2
    Paul Hall           assigned to WORKER-3
    Tina Lopez          assigned to WORKER-4
    Isabelle Perez      assigned to WORKER-0

  Heat 2 (33 total, 6 novices)
  ----------------------------

    Car classes: [b, e, q, s, t, v]

    5 of 3 instructors required
    2 of 2 timings required
    2 of 2 grids required
    3 of 1 starts required
    15 of 5 captains required

    Katherine Robinson  assigned to TIMING
    Katherine Thompson  assigned to TIMING
    David Thomas        assigned to GRID
    Xavier Martinez     assigned to GRID
    Zane Lee            assigned to INSTRUCTOR
    Isaac Perez         assigned to INSTRUCTOR
    David Garcia        assigned to INSTRUCTOR
    Katherine Moore     assigned to START
    Hannah Jackson      assigned to CAPTAIN
    Hannah Johnson      assigned to CAPTAIN
    Jack Taylor         assigned to CAPTAIN
    Frank Williams      assigned to CAPTAIN
    Sophia White        assigned to CAPTAIN
    Eve Clark           assigned to WORKER-0
    Quinn Garcia        assigned to WORKER-1
    Henry Garcia        assigned to WORKER-2
    Isaac Davis         assigned to WORKER-3
    Eve Smith           assigned to WORKER-4
    Noah Lee            assigned to WORKER-0
    Ursula Wilson       assigned to WORKER-1
    Alice Thomas        assigned to WORKER-2
    Mia Hall            assigned to WORKER-3
    Henry Wilson        assigned to WORKER-4
    Yvonne Davis        assigned to WORKER-0
    Jack Moore          assigned to WORKER-1
    Quinn Smith         assigned to WORKER-2
    Ursula Rodriguez    assigned to WORKER-3
    David Walker        assigned to WORKER-4
    Sophia Taylor       assigned to WORKER-0
    Noah Brown          assigned to WORKER-1
    Eve Miller          assigned to WORKER-2
    Eve Brown           assigned to WORKER-3
    Frank Williams      assigned to WORKER-4

  ---

  >>> Iteration 1 accepted <<<
```
