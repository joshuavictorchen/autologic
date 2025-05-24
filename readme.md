# Autologic

Somewhat questionable Python program that takes an autocross event roster and generates heat + worker assignments.

Tests may be implemented later.

## Retrieval and usage

1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).

2. Open a terminal window and execute `.\path\to\autologic.exe --csv .\path\to\file.csv` to generate heat and worker assignments.
    - Run `autologic.exe --help` for more options.
    - See [sample.csv](./tests/sample.csv) for an example of the required input data structure. May change upon request.


The dictionary of roles (specialized worker assignments) and their minimum requirements per heat is semi-hardcoded in [utils.py](./source/utils.py)'s `roles_and_minima` definition. The minimum number of instructors in a heat is equal to `number_of_novices` divided `novice_denominator`, or `MIN_INSTRUCTOR_PER_HEAT`, whichever is greater.
