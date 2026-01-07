import random
from autologic.algorithms import get_algorithms
from autologic.event import Event
from autologic.utils import normalize_custom_assignments


def main(algorithm, event, observer=None, export=True):
    """Parse event participants and generate heat assignments with role coverage and balanced sizes.

    Args:
        algorithm: Algorithm name to run.
        event: Event instance to mutate.
        observer: Optional callback for algorithm progress updates.
        export: Whether to write CSV/PDF/PKL outputs after validation.
    """

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

    if export:
        # export data
        if event.no_shows:
            print(
                "\n  The following individuals have not checked in and are therefore excluded:\n"
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
    seed: int | None = None,
):
    """Build an Event with optional deterministic seeding.

    Args:
        name: Event name.
        axware_export_tsv: Path to the AXWare TSV export.
        member_attributes_csv: Path to the member attributes CSV.
        number_of_heats: Number of heats to schedule.
        custom_assignments: Mapping of member IDs to assignment strings or records.
        number_of_stations: Number of worker stations for the course.
        heat_size_parity: Heat size balance control value.
        novice_size_parity: Novice balance control value.
        novice_denominator: Novices per instructor ratio.
        max_iterations: Max number of algorithm iterations.
        seed: Optional RNG seed for deterministic assignments.

    Returns:
        Event: The initialized event instance.
    """

    if seed is not None:
        random.seed(seed)

    active_assignments, assignment_records = normalize_custom_assignments(
        custom_assignments
    )

    event = Event(
        name=name,
        axware_export_tsv=axware_export_tsv,
        member_attributes_csv=member_attributes_csv,
        custom_assignments=active_assignments,
        number_of_heats=number_of_heats,
        number_of_stations=number_of_stations,
        heat_size_parity=heat_size_parity,
        novice_size_parity=novice_size_parity,
        novice_denominator=novice_denominator,
        max_iterations=max_iterations,
    )
    # store a config snapshot so GUI loads can repopulate inputs from pickles
    event.config_snapshot = {
        "name": name,
        "axware_export_tsv": str(axware_export_tsv),
        "member_attributes_csv": str(member_attributes_csv),
        "custom_assignments": assignment_records,
        "number_of_heats": number_of_heats,
        "number_of_stations": number_of_stations,
        "heat_size_parity": heat_size_parity,
        "novice_size_parity": novice_size_parity,
        "novice_denominator": novice_denominator,
        "max_iterations": max_iterations,
    }
    return event
