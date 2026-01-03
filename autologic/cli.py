import click
import pickle
import questionary
import yaml

from autologic.algorithms import get_algorithms
from autologic.app import load_event, main

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
    "--seed",
    type=int,
    default=None,
    help="Optional RNG seed for deterministic assignments.",
)
@click.option(
    "--load",
    "pickle_file",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to a previously-saved Event state.",
)
@click.option(
    "--interactive",
    type=click.BOOL,
    default=True,
    help="Enable interactive mode for main function.",
)
def cli(
    config: dict, algorithm: str, seed: int | None, pickle_file: str, interactive: bool
):

    if config is None and pickle_file is None:
        raise click.BadParameter("Must supply either --config or --load.")
    if config is not None and pickle_file is not None:
        raise click.BadParameter("Cannot use --config and --load together.")

    # =============================================================================
    # TODO: refactor for sanity and flexibility
    #       this should be split out into separate functions
    #       left as-is for quick prototype development
    # =============================================================================

    if config:
        event = load_event(**config.model_dump(), seed=seed)
        main(algorithm=algorithm, event=event, interactive=interactive)
        return

    # at this point, we're loading a file and doing things interactively
    with open(pickle_file, "rb") as f:
        event = pickle.load(f)

    print(f"\nEvent loaded: {event.name}")

    choices = [
        "Move a Category to a different Heat",
        "Rotate Heat run/work groups",
        "Update a Participant assignment",
        "Run Event validation checks",
        "Export data",
        "Quit",
    ]

    while True:

        print(f"\n---")

        choice = questionary.select(
            "\nAction:",
            choices=choices,
            qmark="",
            instruction=" ",
        ).ask()

        if choice == "Move a Category to a different Heat":

            category = (
                questionary.autocomplete(
                    "\nClass:",
                    choices=list(event.categories.keys()),
                    qmark="",
                    ignore_case=True,
                )
                .ask()
                .upper()
            )

            heat_number = questionary.select(
                "\nAssign to Heat",
                choices=[str(h.number) for h in event.heats],
                qmark="",
                instruction=" ",
            ).ask()
            heat_number = int(heat_number)

            print()
            event.categories[category].set_heat(
                event.get_heat(heat_number), verbose=True
            )

        if choice == "Rotate Heat run/work groups":

            offset_str = questionary.text(
                "\nApply a run/work group offset:",
                qmark="",
                validate=lambda val: val.isdigit(),
            ).ask()

            # TODO: make the run/work groups attributes of Heat
            offset = int(offset_str) % event.number_of_heats
            event.heats[:] = event.heats[-offset:] + event.heats[:-offset]

            print()
            event.get_heat_assignments(verbose=True)

        if choice == "Update a Participant assignment":
            participant_names = [p.name for p in event.participants]
            participant = (
                questionary.autocomplete(
                    "\nParticipant:",
                    choices=participant_names,
                    qmark="",
                    ignore_case=True,
                )
                .ask()
                .upper()
            )

            role = (
                questionary.select(
                    "\nAssign to role:",
                    choices=[
                        "special",
                        "instructor",
                        "timing",
                        "grid",
                        "start",
                        "captain",
                        "worker",
                    ],
                    qmark="",
                    instruction=" ",
                )
                .ask()
                .lower()
            )

            print()
            event.get_participant_by_name(participant).set_assignment(
                role, show_previous=True, manual_override=True
            )

        if choice == "Run Event validation checks":

            event.validate()

        if choice == "Export data":

            print(f"\nFiles with the same Event name will be overwritten!")
            new_name = input("\nSave Event as: ")

            event.name = new_name

            event.to_csv()
            event.to_pdf()
            event.to_pickle()
            print()
            return

        if choice == "Quit":
            print(f"\nProgram terminated.\n")
            return


if __name__ == "__main__":
    cli()
