import csv
import click
from pathlib import Path

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


def map_msr_export_work_assignments_to_autologic(name: str, assignments: list[str]):
    """
    Converts work assignments from an MSR export to the autologic member attribute names

    Args:
        name (str): The name of the registrant
        assignments (list[str]): A list of work assignments they've elected in MSR
    Returns:
        dict[str, str]: The autologic member attributes with their name and empty strings for unelected attributes
    """
    return {
        "name": name,
        "instructor": "",
        **{
            autologic_attribute_value: (
                "TRUE" if msr_assignment_key in assignments else ""
            )
            for msr_assignment_key, autologic_attribute_value in MSR_TO_AUTOLOGIC_MEMBER_ATTRIBUTE_MAP.items()
        },
    }


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


def load_msr_export(msr_export_path) -> dict[str, dict[str, str]]:
    """
    Loads the MSR export into a dictionary of Member # -> dictionary in the autologic member attribute row format
    Args:
        msr_export_path (Path): The path to the MSR export file, passed in by cli argument
    Returns:
        dict[str, dict[str, str]]: Format of Member # -> Dictionary of elected work assignments in the autologic member attribute row format
    """
    member_work_assignment_dictionary = {}
    with open(msr_export_path) as msr_export_file:
        for row in csv.DictReader(msr_export_file):
            member_work_assignment_elections = (
                row["Work Assignment"].split(",") if len(row["Work Assignment"]) else []
            )
            member_work_assignment_dictionary.setdefault(
                row["Member #"],
                map_msr_export_work_assignments_to_autologic(
                    row["Name"], member_work_assignment_elections
                ),
            )

    return member_work_assignment_dictionary


def load_member_attributes_csv(path) -> dict[str, dict[str, str]]:
    """
    Loads the autologic member attributes csv into a dictionary of member # -> dictionary in the autologic member attribute row format
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


def merge_member_attributes(
    member_msr_export_attributes: dict[str, str],
    member_attributes_dictionary: dict[str, str],
) -> dict[str, str]:
    """
    Consolidates the MSR export work assignment elections with current member attributes into one row, this will add new
    work attributes but not remove any existing ones.

    Args:
        member_msr_export_attributes (dict[str, str]): The MSR work assignment elections in autologic member attribute row format
        member_attributes_dictionary (dict[str, str]): The autologic member attribute row

    Returns:
        dict[str, str]: The updated autologic member attribute row
    """
    return {
        attribute_key: (
            "TRUE"
            if member_msr_export_attributes.get(attribute_key) == "TRUE"
            or member_attributes_dictionary.get(attribute_key) == "TRUE"
            else ""
        )
        for attribute_key in AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS
    }


@click.command(context_settings={"max_content_width": 120})
@click.option(
    "--msr_export_csv",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    required=True,
    help="Path to the MSR export csv file.",
)
@click.option(
    "--member_attributes_csv",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    required=True,
    help="Path to the member attributes csv file.",
)
def cli(msr_export_csv: Path, member_attributes_csv: Path):
    main(
        load_msr_export(msr_export_csv),
        load_member_attributes_csv(member_attributes_csv),
    )


def main(
    msr_export_dictionary: dict[str, dict[str, str]],
    member_attribute_dictionary: dict[str, dict[str, str]],
) -> None:
    updated_member_attributes_dictionary = {}
    all_member_ids = msr_export_dictionary.keys() | member_attribute_dictionary.keys()
    for member_id in all_member_ids:
        current_member_row = member_attribute_dictionary.get(
            member_id, {key: "" for key in AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS}
        )
        msr_export_row = msr_export_dictionary.get(
            member_id, {key: "" for key in AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS}
        )

        merged_member_attributes = merge_member_attributes(
            msr_export_row, current_member_row
        )
        updated_member_attributes_dictionary[member_id] = {
            "id": member_id,
            "name": current_member_row.get("name") or msr_export_row.get("name") or "",
            **{
                attribute_key: attribute_value
                for attribute_key, attribute_value in merged_member_attributes.items()
            },
        }

    with open(
        "private_updated_member_attributes.csv", "w"
    ) as updated_member_attributes_file:
        fields = ["id", "name"] + AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS
        writer = csv.DictWriter(updated_member_attributes_file, fieldnames=fields)
        writer.writeheader()

        for new_member_attributes in updated_member_attributes_dictionary.values():
            writer.writerow(new_member_attributes)


if __name__ == "__main__":
    cli()
