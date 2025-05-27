import click
import math
import random

import utils
from Event import Event


def randomize_heats(event, number_of_heats):
    """
    Randomly assign categories (car classes) to heats.

    TODO: This is overly restrictive! It works for now but should be updated in the future.
          Categories are EVENLY DISTRIBUTED across heats even though category size may vary significantly.
    """
    categories = list(event.categories.values())
    random.shuffle(categories)
    for i, c in enumerate(categories):
        c.set_heat(i % number_of_heats)


@click.command(context_settings={"max_content_width": 120})
@click.option(
    "--msr-export",
    "msr_export_filename",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to input MSR export CSV file.",
)
@click.option(
    "--member-attributes",
    "member_attributes_filename",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to member attribute CSV file.",
)
@click.option(
    "--heats",
    "number_of_heats",
    default=3,
    show_default=True,
    type=int,
    help="Number of heats to divide participants into.",
)
@click.option(
    "--stations",
    "number_of_stations",
    default=5,
    show_default=True,
    type=int,
    help="Number of worker stations for the course.",
)
@click.option(
    "--heat-size-parity",
    default=25,
    show_default=True,
    type=int,
    help="Smaller values enforce tighter heat size balance.",
)
@click.option(
    "--novice-size-parity",
    default=10,
    show_default=True,
    type=int,
    help="Smaller values enforce tighter novice balance across heats.",
)
@click.option(
    "--novice-denominator",
    default=3,
    show_default=True,
    type=int,
    help="The minimum number of instructors in a heat is equal to the number of novices in the heat divided by this value.",
)
@click.option(
    "--max-iterations",
    default=10000,
    show_default=True,
    type=int,
    help="Maximum number of tries before the program gives up.",
)
def main(
    msr_export_filename,
    member_attributes_filename,
    number_of_heats,
    number_of_stations,
    heat_size_parity,
    novice_size_parity,
    novice_denominator,
    max_iterations,
):
    """Parse event participants and generate heat assignments with role coverage and balanced sizes."""

    # TODO: refactor for sanity and flexibility

    event = Event(msr_export_filename, member_attributes_filename, number_of_heats, number_of_stations)

    # check if the event has enough qualified participants to fill each role
    print("\n  Role minimums")
    print("  -------------")
    insufficient = False
    role_ratios = {}
    for role, minimum in utils.roles_and_minima(
        number_of_stations=number_of_stations,
        number_of_novices=len(event.get_participants_by_attribute("novice"))
        / number_of_heats,
        novice_denominator=novice_denominator,
    ).items():
        qualified = len(event.get_participants_by_attribute(role))
        required = minimum * number_of_heats
        role_ratios[role] = (
            qualified / required if required > 0 else 100
        )  # arbitrarily large
        warning = " <-- NOT ENOUGH QUALIFIED WORKERS" if qualified < required else ""
        if qualified < required:
            insufficient = True
        print(f"  {role.rjust(10)}: {str(qualified).rjust(2)} / {required}{warning}")
    if insufficient:
        raise ValueError("Not enough qualified workers for role(s).")

    # calculate heat size restrictions for total participants and novices
    mean_group_size = round(len(event.participants) / number_of_heats)
    max_group_delta = math.ceil(len(event.participants) / heat_size_parity)
    mean_novice_count = round(
        len(event.get_participants_by_attribute("novice")) / number_of_heats
    )
    max_novice_delta = math.ceil(
        len(event.get_participants_by_attribute("novice")) / novice_size_parity
    )

    # keep randomizing heats until all criteria are met (lol)
    rules_satisfied = False
    iteration = -1
    while not rules_satisfied and iteration < max_iterations:

        iteration += 1
        rules_satisfied = True
        skip_iteration = False
        print(
            f"\n  ==================================================\n\n  [Iteration {iteration}]"
        )

        randomize_heats(event, number_of_heats)

        print(f"\n  Heat size must be {mean_group_size} +/- {max_group_delta}")
        print(f"  Novice count must be {mean_novice_count} +/- {max_novice_delta}")

        # clear assignments from the previous iteration
        for p in event.participants:
            p.assignment = None

        # check if heat constraints are satisfied (size, role fulfillments)
        for h in event.heats.values():

            # skip this loop if a prior heat failed checks
            if skip_iteration:
                break

            # check total heat size constraints
            heat_size = len(h.participants)
            if abs(mean_group_size - heat_size) > max_group_delta:
                rules_satisfied = False
                skip_iteration = True
                print(f"\n  Heat {h} rejected: participant count of {heat_size}")
                break

            # check heat novice count constraints
            novice_count = len(h.get_participants_by_attribute("novice"))
            if abs(mean_novice_count - novice_count) > max_novice_delta:
                rules_satisfied = False
                skip_iteration = True
                print(f"\n  Heat {h} rejected: novice count of {novice_count}")
                break

            header = f"Heat {h} ({heat_size} total, {novice_count} novices)"
            print(f"\n  {header}")
            print(f"  {'-' * len(header)}\n")
            print(f"    Car classes: {h.categories}\n")

            # check if number of qualified participants for each role exceed the minima required
            role_extras = {}
            for role, minimum in utils.roles_and_minima(
                number_of_stations=number_of_stations,
                number_of_novices=novice_count,
                novice_denominator=novice_denominator,
            ).items():
                qualified = len(h.get_participants_by_attribute(role))
                role_extras[role] = (
                    qualified - minimum
                )  # used later to assign workers to roles based on need
                print(f"    {qualified} of {minimum} {role}s required")
                if qualified < minimum:
                    rules_satisfied = False
                    skip_iteration = True
                    print(
                        f"\n    Heat {h} rejected: unable to fill {role.upper()} role(s)"
                    )
                    break

            if rules_satisfied:
                # just because qualified >= minimum doesn't mean we're in the clear
                # some participants are qualified for multiple roles, but can only fulfill one for their heat
                # try to assign roles now
                # start with roles that have the smallest delta between qualified participants and minimum requirements
                print()
                for role in utils.sort_dict_by_value(role_extras):
                    if skip_iteration:
                        break
                    for _ in range(
                        utils.roles_and_minima(
                            number_of_stations=number_of_stations,
                            number_of_novices=novice_count,
                            novice_denominator=novice_denominator,
                        )[role]
                    ):
                        available = h.get_available(role)
                        if not available:
                            rules_satisfied = False
                            print(
                                f"\n  Heat {h} rejected: unable to fill {role} role(s)"
                            )
                            skip_iteration = True
                            break
                        else:
                            available[0].set_assignment(role)

                # now assign everyone else to worker stations
                for i, worker in enumerate(h.get_available(role=None)):
                    worker.set_assignment(f"worker-{i % number_of_stations}")

    if not rules_satisfied:
        print(f"\n\n  Could not create heats in {max_iterations} iterations.")
        exit(1)

    print(f"\n  ---\n\n  >>> Iteration {iteration} accepted <<<\n")


if __name__ == "__main__":
    main()
