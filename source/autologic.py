from Event import Event


def main(
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
    )

    # TODO: add hooks here and have the algorithm module supplied as an arg
    # for now, just hard-code as if it's a regular import
    from algorithms import randomize

    randomize.generate_heats(event, max_iterations)

    # export data
    if event.no_shows:
        print(
            f"\n  The following individuals have not checked in and are therefore excluded:\n"
        )
        [print(f"  - {i}") for i in event.no_shows]

    event.to_csv()
    event.to_pdf()
    print()
