import math
import random

import utils
from Event import Event

# =============================================================================
# TODO: refactor for sanity and flexibility
#       this should be split out into separate functions and perhaps even modules
#       left as-is for quick prototype development ahead of a pilot event
#       this module is intended to house algorithms and algorithm-related functions
# =============================================================================


def randomize_heats(event, number_of_heats):
    """
    Randomly assign categories (car classes) to heats.

    TODO: This is overly restrictive! It works for now but should be updated in the future.
          Categories are EVENLY DISTRIBUTED across heats even though category size may vary significantly.
    """
    categories = list(event.categories.values())
    random.shuffle(categories)
    for i, c in enumerate(categories):
        c.set_heat(i % number_of_heats + 1)


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
    )

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
        # TODO: make a p.clear_assignment() function that handles this and other logic trees
        for p in event.participants:
            p.assignment = p.special_assignment if p.special_assignment else None

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
                # TODO: this is another thing that really needs to be split out
                print()

                # assign special assignments - redundant but is helpful for console output
                # TODO: remove this sloppiness
                for p in h.get_participants_by_attribute(
                    attribute="assignment", value="special"
                ):
                    p.set_assignment("special")

                for role in utils.sort_dict_by_value(role_extras):
                    if skip_iteration:
                        break

                    # calculate how many slots need to be filled for this role, accounting for custom pre-assignments
                    pre_assigned_participants = h.get_participants_by_attribute(
                        attribute="assignment", value=role
                    )
                    for p in pre_assigned_participants:
                        p.set_assignment(
                            role
                        )  # redundant but is helpful for console output
                    pre_assigned_count = len(pre_assigned_participants)
                    baseline_required_count = utils.roles_and_minima(
                        number_of_stations=number_of_stations,
                        number_of_novices=novice_count,
                        novice_denominator=novice_denominator,
                    )[role]
                    actual_required_count = baseline_required_count - pre_assigned_count

                    # fill the actual required slots for this role
                    for _ in range(actual_required_count):
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

                # now assign everyone else to worker role
                for worker in h.get_available(role=None):
                    worker.set_assignment("worker")

    if not rules_satisfied:
        print(f"\n\n  Could not create heats in {max_iterations} iterations.\n")
        exit(1)

    print(f"\n  ---\n\n  >>> Iteration {iteration} accepted <<<")

    # export data
    work_assignments = event.get_work_assignments()
    utils.autologic_event_to_csv(work_assignments)
    utils.autologic_event_to_pdf(work_assignments)
    print()
