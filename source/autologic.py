import questionary
from event import Event
from algorithms import get_algorithms


def main(algorithm, event, interactive=False, observer=None):
    """Parse event participants and generate heat assignments with role coverage and balanced sizes."""

    if interactive:

        choice = questionary.select(
            "\nAction:",
            choices=["Continue", "Quit"],
            qmark="",
            instruction=" ",
        ).ask()

        if choice != "Continue":
            print()
            return

    # get the algorithms
    algos = get_algorithms()
    if algorithm not in algos:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    this_algorithm = algos[algorithm]()  # instantiate
    if observer and hasattr(this_algorithm, "add_observer"):
        this_algorithm.add_observer(observer)
    this_algorithm.generate(event)

    # run checks
    is_valid = event.validate()
    if not is_valid:
        raise ValueError(
            f"Invalid event configuration. See console output for details."
        )

    # export data
    if event.no_shows:
        print(
            f"\n  The following individuals have not checked in and are therefore excluded:\n"
        )
        [print(f"  - {i}") for i in event.no_shows]

    event.to_csv()
    event.to_pdf()
    event.to_pickle()
    print()


def load_event(
    name,
    axware_export_tsv,
    member_attributes_csv,
    number_of_heats,
    custom_assignments,
    number_of_stations,
    heat_size_parity,
    novice_size_parity,
    novice_denominator,
    max_iterations,
):

    return Event(
        name=name,
        axware_export_tsv=axware_export_tsv,
        member_attributes_csv=member_attributes_csv,
        custom_assignments={
            str(key): value for key, value in custom_assignments.items()
        },  # ensure all keys are str
        number_of_heats=number_of_heats,
        number_of_stations=number_of_stations,
        heat_size_parity=heat_size_parity,
        novice_size_parity=novice_size_parity,
        novice_denominator=novice_denominator,
        max_iterations=max_iterations,
    )
