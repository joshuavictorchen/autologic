# Autologic

Somewhat questionable Python program that takes an autocross event roster and generates heat + worker assignments.

It provides a rough framework that may be used to assign `Categories` (car classes) to `Heats`, and `Participants` to `Roles` (specialized work assignments).

The current "algorithm" loads an `Event`, randomly assigns `Categories` to `Heats`, checks against acceptance criteria (can all `Roles` be filled within each `Heat`?), and keeps iterating until all criteria are met.

Better documentation to come... if there is interest. A smarter algorithm may be implemented later. Tests may be implemented later.

## Retrieval and usage

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --csv .\path\to\file.csv` to generate heat and worker assignments.
    - Run `autologic.exe --help` for more options.
    - See [sample.csv](./tests/sample.csv) for an example of the required input data structure. May change upon request.
        - Mostly self-explanatory. The `special` role is for VPs, worker coordinators, etc. who should not be assigned to another role.
    - The dictionary of roles (specialized worker assignments) and their minimum requirements per heat is semi-hardcoded in [utils.py](./source/utils.py)'s `roles_and_minima` definition.
        - The minimum number of instructors in a heat is equal to `number_of_novices` divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.
        - The minimum number of corner captains in a heat is equal to `number_of_stations`.
