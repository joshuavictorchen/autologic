import csv
import click
from pathlib import Path
from datetime import datetime
from script_utils import load_member_attributes_csv, AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS


def merge_member_attributes(
    autologic_diff_dictionary: dict[str, str],
    member_attributes_dictionary: dict[str, str],
) -> dict[str, str]:
    """
    Consolidates the accepted autologic diff rows with current member attributes into one row, this will add new
    work attributes but not remove any existing ones.

    Args:
        autologic_diff_dictionary (dict[str, str]): The MSR work assignment elections in autologic member attribute row format from the autologic diff
        member_attributes_dictionary (dict[str, str]): The autologic member attribute row

    Returns:
        dict[str, str]: The updated autologic member attribute row
    """
    return {
        attribute_key: (
            "TRUE"
            if autologic_diff_dictionary.get(attribute_key) == "TRUE"
            or member_attributes_dictionary.get(attribute_key) == "TRUE"
            else ""
        )
        for attribute_key in AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS
    }


@click.command(context_settings={"max_content_width": 120})
@click.option(
    "--attribute_diff_csv",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    required=True,
    help="Path to the autologic attribute diff csv file.",
)
@click.option(
    "--member_attributes_csv",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    required=True,
    help="Path to the member attributes csv file.",
)
def cli(attribute_diff_csv: Path, member_attributes_csv: Path):
    main(
        load_member_attributes_csv(attribute_diff_csv),
        load_member_attributes_csv(member_attributes_csv),
    )


def main(
    autologic_diff_dictionary: dict[str, dict[str, str]],
    member_attribute_dictionary: dict[str, dict[str, str]],
) -> None:
    updated_member_attributes_dictionary = {}
    all_member_ids = (
        autologic_diff_dictionary.keys() | member_attribute_dictionary.keys()
    )

    for member_id in all_member_ids:
        current_member_row = member_attribute_dictionary.get(
            member_id, {key: "" for key in AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS}
        )
        autologic_diff_row = autologic_diff_dictionary.get(
            member_id, {key: "" for key in AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS}
        )

        merged_member_attributes = merge_member_attributes(
            autologic_diff_row, current_member_row
        )
        updated_member_attributes_dictionary[member_id] = {
            "id": member_id,
            "name": current_member_row.get("name")
            or autologic_diff_row.get("name")
            or "",
            **{
                attribute_key: attribute_value
                for attribute_key, attribute_value in merged_member_attributes.items()
            },
        }

    with open(
        f"{datetime.now().strftime("%m%d%Y")}_private_updated_member_attributes.csv",
        "w",
    ) as updated_member_attributes_file:
        fields = ["id", "name"] + AUTOLOGIC_MEMBER_ATTRIBUTE_KEYS
        writer = csv.DictWriter(updated_member_attributes_file, fieldnames=fields)
        writer.writeheader()

        for new_member_attributes in updated_member_attributes_dictionary.values():
            writer.writerow(new_member_attributes)


if __name__ == "__main__":
    cli()
