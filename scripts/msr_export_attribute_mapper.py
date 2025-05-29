import csv
import click
import re
from pathlib import Path

autologic_member_attribute_keys = ['instructor', 'timing', 'grid', 'start', 'captain', 'gate', 'special']

msr_to_autologic_member_attribute_map = {
   "Timing & Scoring": 'timing',
   "Grid": 'grid',
   "Starter": 'start',
   "Corner Captain": 'captain',
   "Gate": 'gate'
}

def get_formatted_member_number(member_number_string):
    return re.sub("[^0-9]", "", member_number_string)

def map_msr_export_work_assignments_to_autologic(assignments: list[str]):
    return {
        'instructor': '',
        **{autologic_attribute_value: "TRUE" if msr_assignment_key in assignments else ""
           for msr_assignment_key, autologic_attribute_value in msr_to_autologic_member_attribute_map.items()
        },
        'special': '',
    }

def map_member_attributes_row_to_dictionary(row: dict[str, str]):
    return {key: "TRUE" if row[key] else "" for key in autologic_member_attribute_keys}

def load_msr_export(msr_export_path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    member_work_assignment_dictionary = {}
    member_id_name_dictionary = {}
    with open(msr_export_path) as msr_export_file:
        for row in csv.DictReader(msr_export_file):
            member_work_assignment_elections = row["Work Assignment"].split(',') if len(row["Work Assignment"]) else []

            member_work_assignment_dictionary.setdefault(
                get_formatted_member_number(row["Member #"]),
                map_msr_export_work_assignments_to_autologic(member_work_assignment_elections)
            )

            member_id_name_dictionary.setdefault(get_formatted_member_number(row["Member #"]), row["Name"])

    return member_work_assignment_dictionary, member_id_name_dictionary

def load_member_attributes_csv(path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    member_attributes_dictionary = {}
    member_id_name_dictionary = {}
    with open(path) as member_attributes_file:
        for row in csv.DictReader(member_attributes_file):
            member_attributes_dictionary.setdefault(row["id"], map_member_attributes_row_to_dictionary(row))
            member_id_name_dictionary.setdefault(row["id"], row["name"])

    return member_attributes_dictionary, member_id_name_dictionary

def merge_member_attributes(member_msr_export_attributes: dict[str, str], member_attributes_dictionary: dict[str, str]) -> dict[str, str]:
    return {attribute_key: "TRUE" if member_msr_export_attributes.get(attribute_key) == "TRUE" or member_attributes_dictionary.get(attribute_key) == "TRUE" else ""
            for attribute_key in member_attributes_dictionary.keys()}


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
    help="Path to the MSR export csv file.",
)

def cli(msr_export_csv: Path, member_attributes_csv: Path):
    main(load_msr_export(msr_export_csv), load_member_attributes_csv(member_attributes_csv))

def main(msr_export_dictionaries: tuple[dict[str, dict[str, str]], dict[str, str]], member_attribute_dictionaries: tuple[dict[str, dict[str, str]], dict[str, str]]) -> None:
    msr_export_dictionary, msr_member_id_name_dictionary = msr_export_dictionaries
    member_attribute_dictionary, member_attribute_id_name_dictionary = member_attribute_dictionaries

    updated_member_attributes_dictionary = {}
    for member_id in msr_export_dictionary:
        current_member_row = member_attribute_dictionary.get(member_id, {key: '' for key in autologic_member_attribute_keys})
        msr_export_row = msr_export_dictionary.get(member_id)

        merged_member_attributes = merge_member_attributes(msr_export_row, current_member_row)
        updated_member_attributes_dictionary[member_id] = {
            'id': member_id,
            'name': msr_member_id_name_dictionary.get(member_id, member_attribute_id_name_dictionary.get(member_id)),
            **{attribute_key: attribute_value for attribute_key, attribute_value in merged_member_attributes.items()}
        }

    for key in updated_member_attributes_dictionary:
        print(f"{key}: {updated_member_attributes_dictionary[key]}")

    with open('private_updated_member_attributes.csv', 'w') as updated_member_attributes_file:
        fields = ['id', 'name'] + autologic_member_attribute_keys
        writer = csv.DictWriter(updated_member_attributes_file, fieldnames=fields)
        writer.writeheader()

        for new_member_attributes in updated_member_attributes_dictionary.values():
            writer.writerow(new_member_attributes)


if __name__ == "__main__":
    cli()