import csv

AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS = [
    "instructor",
    "timing",
    "grid",
    "start",
    "captain",
    "gate",
]

MSR_TO_AUTOLOGIC_MEMBER_ATTRIBUTE_MAP = {
    "Timing & Scoring": "timing",
    "Grid": "grid",
    "Starter": "start",
    "Corner Captain": "captain",
    "Gate": "gate",
}


def load_member_attributes_csv(path) -> dict[str, dict[str, str]]:
    """
    Loads an autologic member attributes csv into a dictionary of member # -> dictionary in the autologic member attribute row format
    Args:
        path (Path): The path to the autologic member attribute csv file passed in by cli argument
    Returns:
        dict[str, dict[str, str]] of member # -> dictionary in the autologic member attribute row format
    """
    member_attributes_dictionary = {}
    with open(path) as member_attributes_file:
        for row in csv.DictReader(member_attributes_file):
            member_attributes_dictionary.setdefault(
                row["id"], map_member_attributes_row_to_dictionary(row)
            )

    return member_attributes_dictionary


def map_member_attributes_row_to_dictionary(row: dict[str, str]):
    """
    Converts an autologic member attribute row to a dictionary
    Args:
        row (dict[str, str]): The autologic member attribute row
    Returns:
        dict[str, str]: The autologic member attribute dictionary
    """
    return {
        "name": row["name"],
        **{key: "TRUE" if row[key] else "" for key in AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS},
    }
