import click
import pickle
import yaml

import autologic
from algorithms import get_algorithms

from pathlib import Path
from pydantic import BaseModel, Field, ValidationError


class Config(BaseModel):
    name: str = Field("autologic-event", description="Name of the autocross event.")
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
    help="Path to event configuration file.",
)
@click.option(
    "--algorithm",
    type=click.Choice(list(get_algorithms().keys())),
    default="randomize",
    help="Which heat generation algorithm to use.",
)
@click.option(
    "--load",
    "pickle_file",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to a previously-saved Event state.",
)
def cli(config: dict, algorithm: str, pickle_file: str):

    if config is None and pickle_file is None:
        raise click.BadParameter("Must supply either --config or --load.")
    if config is not None and pickle_file is not None:
        raise click.BadParameter("Cannot use --config and --load together.")

    if config:
        event = autologic.load_event(**config.model_dump())
        autologic.main(algorithm=algorithm, event=event)
        return

    # at this point, we're loading a file and doing things interactively
    with open(pickle_file, "rb") as f:
        event = pickle.load(f)

    print(f"\nEvent loaded: {event.name}")

    choices = {
        "1": "Move a Category to a different Heat",
        "2": "Rotate Heat run/work groups",
        "3": "Update a Participant assignment",
        "4": "Run Event validation checks",
        "5": "Export data",
        "Q": "Quit",
    }

    while True:

        print(f"\n---\n")
        for k, v in choices.items():
            print(f"[{k}] {v}")

        choice = click.prompt(
            "\nSelection",
            type=click.Choice(list(choices.keys()), case_sensitive=False),
            show_choices=False,
        )

        print(f"\n---")

        if choice == "1":

            category = click.prompt(
                f"\nClass",
                type=click.Choice(list(event.categories.keys()), case_sensitive=False),
                show_choices=False,
            ).upper()

            heat_number = click.prompt(
                f"Assign to Heat",
                type=click.Choice([h.name for h in event.heats]),
                show_choices=False,
            )

            print()
            event.categories[category].set_heat(
                event.get_heat(heat_number), verbose=True
            )

        if choice == "2":

            offset = click.prompt(
                f"\nApply a run/work group offset",
                type=int,
                show_choices=False,
            )

            # TODO: make the run/work groups attributes of Heat
            offset = offset % event.number_of_heats
            event.heats[:] = event.heats[-offset:] + event.heats[:-offset]

            print()
            event.get_heat_assignments(verbose=True)

        if choice == "3":

            # TODO: use questionary
            participant = click.prompt(
                f"\nParticipant",
                type=click.Choice(list(event.participants), case_sensitive=False),
                show_choices=False,
            ).name.upper()

            role = click.prompt(
                f"Assign to role",
                type=click.Choice(
                    [
                        "special",
                        "instructor",
                        "timing",
                        "grid",
                        "start",
                        "captain",
                        "worker",
                    ],
                    case_sensitive=False,
                ),  # TODO: clean
                show_choices=False,
            ).lower()

            print()
            event.get_participant_by_name(participant).set_assignment(
                role, show_previous=True, manual_override=True
            )

        if choice == "4":

            event.validate()

        if choice == "5":

            print(f"\nFiles with the same Event name will be overwritten!")
            new_name = input("\nSave Event as: ")

            event.name = new_name

            event.to_csv()
            event.to_pdf()
            event.to_pickle()
            print()
            return

        if choice.lower() == "q":
            print(f"\nProgram terminated.\n")
            return


if __name__ == "__main__":
    cli()
