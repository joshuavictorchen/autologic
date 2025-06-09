from Event import Event
from algorithms import get_algorithms


def main(
    algorithm,
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
    """Parse event participants and generate heat assignments with role coverage and balanced sizes."""

    event = Event(
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

    # get the algorithms
    algos = get_algorithms()
    if algorithm not in algos:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    this_algorithm = algos[algorithm]()  # instantiate
    this_algorithm.generate(event)

    # run checks
    event.validate()

    # export data
    if event.no_shows:
        print(
            f"\n  The following individuals have not checked in and are therefore excluded:\n"
        )
        [print(f"  - {i}") for i in event.no_shows]

    event.to_csv()
    event.to_pdf()
    print()
