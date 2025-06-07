import click
import csv
import yaml

import autologic
import utils

from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional


class Config(BaseModel):
    axware_export_tsv: Path = Field(..., description="Path to AXWare export TSV file.")
    member_attributes_csv: Path = Field(
        ..., description="Path to member attribute CSV file."
    )
    number_of_heats: int = Field(
        3, description="Number of heats to divide participants into."
    )
    number_of_stations: int = Field(
        5, description="Number of worker stations for the course."
    )
    custom_assignments: dict[str | int, str | list[str]] = Field(
        default_factory=dict,
        description="A dictionary of member IDs to their custom role assignments.",
    )
    heat_size_parity: int = Field(
        25, description="Smaller values enforce tighter heat size balance."
    )
    novice_size_parity: int = Field(
        10, description="Smaller values enforce tighter novice balance across heats."
    )
    novice_denominator: int = Field(
        3, description="Min instructors in heat = novices / denominator."
    )
    max_iterations: int = Field(
        10000, description="Max number of attempts before giving up."
    )

    def validate_paths(self):
        """Ensure all paths exist and are files."""
        for path_attr in ["axware_export_tsv", "member_attributes_csv"]:
            p = getattr(self, path_attr)
            if not p.exists():
                raise FileNotFoundError(f"{path_attr} does not exist: {p}")
            if not p.is_file():
                raise ValueError(f"{path_attr} is not a file: {p}")


def load_config(ctx, param, value: Path) -> Config:
    if value is None:
        return None
    try:
        with open(value, "r") as f:
            data = yaml.safe_load(f)
        config = Config(**data)
        config.validate_paths()
        return config
    except (ValidationError, FileNotFoundError, ValueError) as e:
        raise click.BadParameter(f"Invalid config: {e}")
    except Exception as e:
        raise click.BadParameter(f"Failed to load config: {e}")


@click.command(context_settings={"max_content_width": 120})
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    callback=load_config,
    required=False,
    help="Path to event configuration file.",
)
@click.option(
    "--to-pdf",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    required=False,
    help="Path to autologic-export.csv file for conversion to PDF. Useful for making manual tweaks and then printing.",
)
def cli(config: Optional[dict], to_pdf: Optional[Path]):

    if not config and not to_pdf:
        raise click.UsageError("You must provide either --config or --to-pdf.")
    if config and to_pdf:
        raise click.UsageError("Only one of --config or --to-pdf can be used.")

    if config:
        autologic.main(**config.model_dump())
    elif to_pdf:
        with open(to_pdf, newline="", encoding="utf-8-sig") as file:

            # TODO: save heats to yaml and load heats from yaml
            heats = [
                ["Running 1 | Working 3", "this is a placeholder"],
                ["Running 2 | Working 4", "it needs to be implemented"],
                ["Running 3 | Working 1", "this is what you're seeing for now"],
                ["Running 4 | Working 2", "shame shame shame"],
            ]

            rows = csv.DictReader(file)
            utils.autologic_event_to_pdf(rows, heats)
            print()


if __name__ == "__main__":
    cli()
