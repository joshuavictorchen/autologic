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

- See [sample.csv](./tests/sample.csv) for an example of the required input data structure. May change to accommodate different configurations. The `special` role is for VPs, worker coordinators, gate workers, etc. who should not be assigned to another role.

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
        grid:  7 / 3
       start:  5 / 3
     captain: 40 / 15

  ==================================================

  [Iteration 0]

  Heat size must be 33 +/- 4
  Novice count must be 7 +/- 3

  Heat 0 rejected: participant count of 39

  ==================================================

  [Iteration 1]

  Heat size must be 33 +/- 4
  Novice count must be 7 +/- 3

  Heat 0 (32 total, 7 novices)
  ----------------------------

    Car classes: [b, d, f, k, l, m, u]

    4 of 3 instructors required
    3 of 2 timings required
    2 of 1 grids required
    2 of 1 starts required
    12 of 5 captains required

    Zane Lee            assigned to INSTRUCTOR
    Isaac Perez         assigned to INSTRUCTOR
    Bob Martin          assigned to INSTRUCTOR
    Frank Jones         assigned to TIMING
    Alice Martinez      assigned to TIMING
    Paul Moore          assigned to GRID
    Hannah Hernandez    assigned to START
    Charlie Walker      assigned to CAPTAIN
    Mia Lopez           assigned to CAPTAIN
    Isabelle Williams   assigned to CAPTAIN
    Wendy Johnson       assigned to CAPTAIN
    Tina Rodriguez      assigned to CAPTAIN
    Eve Clark           assigned to WORKER-0
    Quinn Garcia        assigned to WORKER-1
    Henry Garcia        assigned to WORKER-2
    Hannah Hall         assigned to WORKER-3
    Liam Garcia         assigned to WORKER-4
    Xavier Clark        assigned to WORKER-0
    Isabelle Thompson   assigned to WORKER-1
    Ursula Lopez        assigned to WORKER-2
    Mia Lewis           assigned to WORKER-3
    Samuel Harris       assigned to WORKER-4
    Mia Miller          assigned to WORKER-0
    Paul Lewis          assigned to WORKER-1
    Sophia Gonzalez     assigned to WORKER-2
    Sophia White        assigned to WORKER-3
    Grace Johnson       assigned to WORKER-4
    Bob Lewis           assigned to WORKER-0
    Olivia Martin       assigned to WORKER-1
    Charlie Harris      assigned to WORKER-2
    Ursula Thompson     assigned to WORKER-3
    Samuel Martinez     assigned to WORKER-4

  Heat 1 (35 total, 8 novices)
  ----------------------------

    Car classes: [a, j, q, r, s, t, v]

    5 of 3 instructors required
    3 of 2 timings required
    2 of 1 grids required
    2 of 1 starts required
    15 of 5 captains required

    Rachel Smith        assigned to TIMING
    Katherine Robinson  assigned to TIMING
    Noah Moore          assigned to GRID
    Hannah Johnson      assigned to START
    Charlie Anderson    assigned to INSTRUCTOR
    Olivia Thompson     assigned to INSTRUCTOR
    David Garcia        assigned to INSTRUCTOR
    Hannah Jackson      assigned to CAPTAIN
    Jack Taylor         assigned to CAPTAIN
    Frank Williams      assigned to CAPTAIN
    Xavier Martinez     assigned to CAPTAIN
    Katherine Thompson  assigned to CAPTAIN
    Isaac Wilson        assigned to WORKER-0
    Zane Harris         assigned to WORKER-1
    Wendy Jackson       assigned to WORKER-2
    Frank Hall          assigned to WORKER-3
    Ursula Wilson       assigned to WORKER-4
    Alice Thomas        assigned to WORKER-0
    Henry Lopez         assigned to WORKER-1
    Liam Miller         assigned to WORKER-2
    Victor Taylor       assigned to WORKER-3
    Samuel Thomas       assigned to WORKER-4
    Mia Hall            assigned to WORKER-0
    Henry Wilson        assigned to WORKER-1
    Yvonne Davis        assigned to WORKER-2
    Jack Moore          assigned to WORKER-3
    Quinn Smith         assigned to WORKER-4
    Ursula Rodriguez    assigned to WORKER-0
    David Walker        assigned to WORKER-1
    Sophia Taylor       assigned to WORKER-2
    Sophia White        assigned to WORKER-3
    Noah Brown          assigned to WORKER-4
    Eve Miller          assigned to WORKER-0
    Eve Brown           assigned to WORKER-1
    Frank Williams      assigned to WORKER-2

  Heat 2 (33 total, 7 novices)
  ----------------------------

    Car classes: [c, e, g, h, i, p]

    5 of 3 instructors required
    3 of 2 timings required
    3 of 1 grids required
    1 of 1 starts required
    13 of 5 captains required

    Katherine Moore     assigned to START
    Yvonne White        assigned to TIMING
    David Brown         assigned to TIMING
    Grace Jones         assigned to INSTRUCTOR
    Ethan White         assigned to INSTRUCTOR
    Alice Anderson      assigned to INSTRUCTOR
    David Thomas        assigned to GRID
    Bob Davis           assigned to CAPTAIN
    Alice Jones         assigned to CAPTAIN
    Ethan Clark         assigned to CAPTAIN
    Liam Jones          assigned to CAPTAIN
    Charlie Thomas      assigned to CAPTAIN
    Jack Rodriguez      assigned to WORKER-0
    Jack Martin         assigned to WORKER-1
    Katherine Rodriguez assigned to WORKER-2
    Yvonne Walker       assigned to WORKER-3
    Isaac Davis         assigned to WORKER-4
    Eve Smith           assigned to WORKER-0
    Noah Lee            assigned to WORKER-1
    Grace Hernandez     assigned to WORKER-2
    Olivia Perez        assigned to WORKER-3
    Ethan Anderson      assigned to WORKER-4
    Samuel Taylor       assigned to WORKER-0
    Isaac Lee           assigned to WORKER-1
    Liam Jackson        assigned to WORKER-2
    Bob Gonzalez        assigned to WORKER-3
    Tina Anderson       assigned to WORKER-4
    Noah Jackson        assigned to WORKER-0
    Quinn Hernandez     assigned to WORKER-1
    Paul Hall           assigned to WORKER-2
    Tina Lopez          assigned to WORKER-3
    Isabelle Perez      assigned to WORKER-4
    Rachel Martin       assigned to WORKER-0

  ---

  >>> Iteration 1 accepted <<<
```
