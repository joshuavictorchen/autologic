"""Station assignment logic for workers and captains."""

from collections import defaultdict


def normalize_category(category_string: str) -> str:
    """Normalize category to base class for station grouping.

    Strips NOV*, P*, SR* prefixes so participants from related classes
    can be grouped together at the same station.

    TODO: move these prefixes to a constants module

    Args:
        category_string: The participant's category string (e.g., "NOVCS", "SR1").

    Returns:
        str: Normalized base category (e.g., "CS", "SR").
    """
    upper = category_string.upper()
    # novice classes share stations with their base class
    if upper.startswith("NOV"):
        return upper[3:]
    # senior racer classes are grouped together
    if upper.startswith("SR"):
        return "SR"
    # pro classes are grouped together
    if upper.startswith("P"):
        return "P"
    return category_string


def assign_stations(heat, number_of_stations: int) -> None:
    """Assign station numbers to workers and captains in a heat.

    Captains are assigned first (exactly 1 per station), then workers are
    distributed to achieve even counts (max delta = 1) while keeping
    same-category workers together when possible.

    The algorithm uses closest-fit selection: for each station, it picks
    the category whose size is closest to the remaining slots, with smaller
    categories winning ties.

    Args:
        heat: Heat object containing participants to assign.
        number_of_stations: Number of worker stations (1 through N).
    """
    if number_of_stations < 1:
        return

    # separate captains and workers, clear stations for other roles
    captains = []
    workers = []
    for participant in heat.participants:
        if participant.assignment == "captain":
            captains.append(participant)
        elif participant.assignment == "worker":
            workers.append(participant)
        else:
            # clear station for non-station roles (instructor, timing, etc.)
            participant.station = None

    # assign captains first: exactly 1 per station (round-robin if more captains)
    for i, captain in enumerate(captains):
        captain.station = (i % number_of_stations) + 1

    if not workers:
        return

    # calculate station capacities (guarantees max delta = 1)
    # first 'remainder' stations get one extra worker
    base_capacity = len(workers) // number_of_stations
    remainder = len(workers) % number_of_stations
    station_capacities = {
        i: base_capacity + (1 if i <= remainder else 0)
        for i in range(1, number_of_stations + 1)
    }

    # group workers by normalized category
    by_category = defaultdict(list)
    for worker in workers:
        normalized = normalize_category(worker.category_string)
        by_category[normalized].append(worker)

    # fill each station using closest-fit selection
    for station, capacity in station_capacities.items():
        assigned = 0

        while assigned < capacity and by_category:
            remaining_slots = capacity - assigned

            # find category closest to remaining slots (smaller wins ties)
            # key: (distance from remaining slots, category size)
            best_category = min(
                by_category.keys(),
                key=lambda k: (
                    abs(len(by_category[k]) - remaining_slots),
                    len(by_category[k]),
                ),
            )
            pool = by_category[best_category]

            # assign workers from this category until station full or category exhausted
            while assigned < capacity and pool:
                worker = pool.pop(0)
                worker.station = station
                assigned += 1

            # remove exhausted category
            if not pool:
                del by_category[best_category]

    # optimize captain placement by swapping isolated captains
    _optimize_captain_placement(captains, workers, number_of_stations)


def _optimize_captain_placement(
    captains: list, workers: list, number_of_stations: int
) -> None:
    """Swap captains to maximize class mate proximity.

    For each captain with no class mates at their station, attempt to swap
    with another captain whose station has class mates for both captains.
    Only swaps if the target station's captain also has no class mates there.

    Args:
        captains: List of captain participants with station assignments.
        workers: List of worker participants with station assignments.
        number_of_stations: Number of worker stations (1 through N).
    """
    if len(captains) < 2:
        return

    # build lookup: station -> captain
    captain_by_station = {c.station: c for c in captains}

    # build lookup: station -> list of worker categories (normalized)
    workers_by_station: dict[int, list[str]] = {}
    for worker in workers:
        station = worker.station
        if station not in workers_by_station:
            workers_by_station[station] = []
        workers_by_station[station].append(normalize_category(worker.category_string))

    def count_class_mates(captain, station):
        """Count workers at station with same normalized category as captain."""
        captain_category = normalize_category(captain.category_string)
        return workers_by_station.get(station, []).count(captain_category)

    # iterate through captains looking for swap opportunities
    for captain in captains:
        if count_class_mates(captain, captain.station) > 0:
            continue  # captain already has class mates, skip

        # find best swap target
        best_target_station = None
        best_class_mate_count = 0

        for target_station in range(1, number_of_stations + 1):
            if target_station == captain.station:
                continue

            target_captain = captain_by_station.get(target_station)
            if not target_captain:
                continue

            # target station ineligible if its captain already has class mates
            if count_class_mates(target_captain, target_station) > 0:
                continue

            # count class mates for our captain at target station
            class_mates_at_target = count_class_mates(captain, target_station)
            if class_mates_at_target > best_class_mate_count:
                best_class_mate_count = class_mates_at_target
                best_target_station = target_station

        # perform swap if beneficial
        if best_target_station and best_class_mate_count > 0:
            target_captain = captain_by_station[best_target_station]
            # swap stations
            captain.station, target_captain.station = (
                target_captain.station,
                captain.station,
            )
            # update lookup
            captain_by_station[captain.station] = captain
            captain_by_station[target_captain.station] = target_captain
