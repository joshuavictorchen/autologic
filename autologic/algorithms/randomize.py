import random
from autologic import utils

from autologic.algorithms import HeatGenerator, register

# =============================================================================
# TODO: refactor for sanity and flexibility
#       this should be split out into separate functions
#       left as-is for quick prototype development
# =============================================================================


@register
class Randomizer(HeatGenerator):

    def __init__(self):
        super().__init__()

    def generate(self, event):
        """
        Randomly assign categories (car classes) to heats.
        """

        # keep randomizing heats until all criteria are met (lol)
        rules_satisfied = False
        iteration = -1
        rejection_reasons = {}
        self._notify("start", {"max_iterations": event.max_iterations})

        def record_rejection_reason(reason: str) -> None:
            """Track how often each rejection reason occurs.

            Args:
                reason: Short description of why the iteration failed.
            """
            if reason not in rejection_reasons:
                rejection_reasons[reason] = 0
            rejection_reasons[reason] += 1

        while not rules_satisfied and iteration < event.max_iterations:

            iteration += 1
            rules_satisfied = True
            skip_iteration = False
            print(
                f"\n  ==================================================\n\n  [Iteration {iteration}]"
            )
            self._notify("iteration_start", {"iteration": iteration})

            event.verbose = False
            print()
            self.randomize_heats(event)
            event.verbose = True

            print(
                f"\n  Heat size must be {event.mean_heat_size} +/- {event.max_heat_size_delta}"
            )
            print(
                f"  Novice count must be {event.mean_heat_novice_count} +/- {event.max_heat_novice_delta}"
            )

            # clear assignments from the previous iteration
            # TODO: make a p.clear_assignment() function that handles this and other logic trees
            for p in event.participants:
                p.assignment = p.special_assignment if p.special_assignment else None

            # check if heat constraints are satisfied (size, role fulfillments)
            for h in event.heats:

                # skip this loop if a prior heat failed checks
                if skip_iteration:
                    break

                # check total heat size constraints
                heat_size = len(h.participants)
                if not h.valid_size:
                    rules_satisfied = False
                    skip_iteration = True
                    reason = "heat size out of bounds"
                    record_rejection_reason(reason)
                    print(f"\n    Heat {h} rejected: {reason}")
                    self._notify(
                        "heat_rejected",
                        {"iteration": iteration, "heat": h.number, "reason": reason},
                    )
                    break

                # check heat novice count constraints
                novice_count = len(h.get_participants_by_attribute("novice"))
                if not h.valid_novice_count:
                    rules_satisfied = False
                    skip_iteration = True
                    reason = "novice count out of bounds"
                    record_rejection_reason(reason)
                    print(f"\n    Heat {h} rejected: {reason}")
                    self._notify(
                        "heat_rejected",
                        {"iteration": iteration, "heat": h.number, "reason": reason},
                    )
                    break

                header = f"Heat {h} ({heat_size} total, {novice_count} novices)"
                print(f"\n  {header}")
                print(f"  {'-' * len(header)}\n")
                print(f"    Car classes: {h.categories}\n")

                # check if number of qualified participants for each role exceed the minima required
                complimentary_novice_count = len(
                    h.compliment.get_participants_by_attribute("novice")
                )
                role_extras = {}
                for role, minimum in utils.roles_and_minima(
                    number_of_stations=event.number_of_stations,
                    number_of_novices=complimentary_novice_count,
                    novice_denominator=event.novice_denominator,
                ).items():
                    qualified = len(h.get_participants_by_attribute(role))
                    role_extras[role] = (
                        qualified - minimum
                    )  # used later to assign workers to roles based on need
                    print(f"    {qualified} of {minimum} {role}s required")
                    if qualified < minimum:
                        rules_satisfied = False
                        skip_iteration = True
                        reason = f"insufficient qualified {role}"
                        record_rejection_reason(reason)
                        print(
                            f"\n    Heat {h} rejected: unable to fill {role.upper()} role(s)"
                        )
                        self._notify(
                            "heat_rejected",
                            {
                                "iteration": iteration,
                                "heat": h.number,
                                "reason": f"unable to fill {role.upper()} role(s)",
                            },
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
                            number_of_stations=event.number_of_stations,
                            number_of_novices=complimentary_novice_count,
                            novice_denominator=event.novice_denominator,
                        )[role]
                        actual_required_count = (
                            baseline_required_count - pre_assigned_count
                        )

                        # fill the actual required slots for this role
                        for _ in range(actual_required_count):
                            available = h.get_available(role)
                            if not available:
                                rules_satisfied = False
                                reason = f"unable to assign {role}"
                                record_rejection_reason(reason)
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
            self._print_rejection_summary(iteration + 1, rejection_reasons)
            print(
                f"\n\n  Could not create heats in {event.max_iterations} iterations.\n"
            )
            self._notify(
                "max_iterations_exceeded",
                {"max_iterations": event.max_iterations},
            )
            exit(1)

        self._print_rejection_summary(iteration + 1, rejection_reasons)
        print(f"\n  ---\n\n  >>> Iteration {iteration} accepted <<<")
        self._notify("accepted", {"iteration": iteration})

    def randomize_heats(self, event):

        categories = list(event.categories.values())
        for c in categories:
            c.set_heat(random.choice(event.heats))

        # hotfix: make CAM classes run together, if any exist
        def cams_in_same_heat(categories):
            cams = {cat for cat in categories if cat.name.startswith("CAM-")}
            cam_heats = [c.heat.number for c in cams]
            return len(set(cam_heats)) <= 1

        def valid_heat_sizes(heats):
            return not any(not h.valid_size for h in heats)

        count = 0
        while not (cams_in_same_heat(categories) and valid_heat_sizes(event.heats)):
            for c in categories:
                c.set_heat(random.choice(event.heats))
            count += 1
            print(f"  Internal iteration: {count}", end="\r")

        print(f"  Internal iteration: {count}")

    def _print_rejection_summary(
        self, iterations_attempted: int, rejection_reasons: dict[str, int]
    ) -> None:
        """Print a summary table of rejection reasons.

        Args:
            iterations_attempted: Number of iterations attempted.
            rejection_reasons: Mapping of rejection reason to occurrence count.
        """
        if not rejection_reasons:
            return

        print("\n  Rejection summary")
        print("  -----------------")
        print(f"  Iterations attempted: {iterations_attempted}")

        sorted_reasons = sorted(
            rejection_reasons.items(),
            key=lambda item: (-item[1], item[0]),
        )
        for reason, count in sorted_reasons:
            print(f"  {str(count).rjust(4)}  {reason}")
