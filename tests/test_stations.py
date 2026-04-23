"""Tests for station assignment logic."""

from autologic.stations import assign_stations


class MockParticipant:
    """Minimal participant for testing station assignment."""

    def __init__(self, name: str, assignment: str, category_string: str):
        self.name = name
        self.assignment = assignment
        self.category_string = category_string
        self.station = None


class MockHeat:
    """Minimal heat for testing station assignment."""

    def __init__(self, participants: list):
        self.participants = participants


class TestAssignStations:
    """Tests for station assignment algorithm."""

    def test_non_station_roles_get_none(self):
        # instructor, timing, grid, start, special should not get stations
        participants = [
            MockParticipant("Alice", "instructor", "CS"),
            MockParticipant("Bob", "timing", "CAM-T"),
            MockParticipant("Carol", "grid", "AS"),
            MockParticipant("Dave", "start", "BS"),
            MockParticipant("Eve", "special", "ES"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        assert participants[0].station is None  # instructor
        assert participants[1].station is None  # timing
        assert participants[2].station is None  # grid
        assert participants[3].station is None  # start
        assert participants[4].station is None  # special

    def test_same_category_grouped_together(self):
        # participants from the same category should be at the same station
        # novices should be grouped with their base class when capacity allows
        # use 4 workers across 2 stations (2 per station) so grouping is possible
        participants = [
            MockParticipant("Alice", "worker", "CS"),
            MockParticipant("Bob", "worker", "NOVCS"),
            MockParticipant("Carol", "worker", "CAM-T"),
            MockParticipant("Dave", "worker", "CAM-T"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        # CS and NOVCS should be at same station (both normalize to "CS")
        assert participants[0].station == participants[1].station
        # CAM-T workers should be at same station
        assert participants[2].station == participants[3].station

    def test_even_distribution_priority(self):
        # even distribution should take priority over class grouping
        # 6 workers across 3 stations with different categories
        participants = [
            MockParticipant(f"P{i}", "worker", f"C{i % 2}") for i in range(6)
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 3)

        station_counts = {1: 0, 2: 0, 3: 0}
        for p in participants:
            station_counts[p.station] += 1

        # should be exactly 2 per station
        assert station_counts == {1: 2, 2: 2, 3: 2}

    def test_uneven_distribution_allowed_for_grouping(self):
        # small imbalances are acceptable to keep classes together
        # 5 workers: 3 in one category, 2 in another, 2 stations
        participants = [
            MockParticipant("A1", "worker", "CS"),
            MockParticipant("A2", "worker", "CS"),
            MockParticipant("A3", "worker", "CS"),
            MockParticipant("B1", "worker", "CAM-T"),
            MockParticipant("B2", "worker", "CAM-T"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        # CS should all be together
        cs_stations = {p.station for p in participants[:3]}
        assert len(cs_stations) == 1

        # CAM-T should all be together
        gt_stations = {p.station for p in participants[3:]}
        assert len(gt_stations) == 1

    def test_clears_stations_for_non_worker_roles(self):
        # if a participant had a station but now has a different role, clear it
        alice = MockParticipant("Alice", "instructor", "CS")
        alice.station = 1  # previously had a station
        heat = MockHeat([alice])
        assign_stations(heat, 3)

        # station should be cleared for non-worker/captain roles
        assert alice.station is None

    def test_large_category_distribution(self):
        # 10 workers across 4 stations: capacities should be [3, 3, 2, 2]
        participants = [
            # 8 CS participants
            *[MockParticipant(f"CS{i}", "worker", "CS") for i in range(8)],
            # 2 CAM-T participants
            MockParticipant("CAM-T1", "worker", "CAM-T"),
            MockParticipant("CAM-T2", "worker", "CAM-T"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 4)

        # CAM-T should be at the same station (closest fit for capacity 2)
        gt_stations = {p.station for p in participants[8:]}
        assert len(gt_stations) == 1

        # verify max delta = 1
        station_counts = {}
        for p in participants:
            station_counts[p.station] = station_counts.get(p.station, 0) + 1

        max_count = max(station_counts.values())
        min_count = min(station_counts.values())
        assert max_count - min_count <= 1

    def test_max_delta_one(self):
        """Worker distribution should have max delta of 1 between stations."""
        # test various worker/station combinations
        test_cases = [(23, 5), (17, 4), (10, 3), (7, 7), (11, 3), (8, 5)]
        for num_workers, num_stations in test_cases:
            participants = [
                MockParticipant(f"W{i}", "worker", f"C{i % 3}")
                for i in range(num_workers)
            ]
            heat = MockHeat(participants)
            assign_stations(heat, num_stations)

            station_counts = {}
            for p in participants:
                station_counts[p.station] = station_counts.get(p.station, 0) + 1

            max_count = max(station_counts.values())
            min_count = min(station_counts.values())
            assert max_count - min_count <= 1, (
                f"{num_workers} workers / {num_stations} stations: "
                f"delta {max_count - min_count} > 1, counts={station_counts}"
            )

    def test_captain_swap_optimization(self):
        """Captains should be swapped to stations with class mates when possible."""
        # setup: force captains to be assigned to mismatched stations initially
        # by controlling category grouping through worker assignment
        participants = [
            MockParticipant("Cap_CS", "captain", "CS"),
            MockParticipant("Cap_CAM-T", "captain", "CAM-T"),
            # CAM-T workers will fill one station
            MockParticipant("W1", "worker", "CAM-T"),
            MockParticipant("W2", "worker", "CAM-T"),
            # CS workers will fill the other station
            MockParticipant("W3", "worker", "CS"),
            MockParticipant("W4", "worker", "CS"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        cap_cs = participants[0]
        cap_gt = participants[1]

        # after optimization, each captain should be with their class mates
        cs_workers_at_cap_cs_station = sum(
            1
            for p in participants[2:]
            if p.station == cap_cs.station and p.category_string == "CS"
        )
        gt_workers_at_cap_gt_station = sum(
            1
            for p in participants[2:]
            if p.station == cap_gt.station and p.category_string == "CAM-T"
        )

        # both captains should have class mates after swap optimization
        assert cs_workers_at_cap_cs_station > 0, "CS captain should have CS class mates"
        assert (
            gt_workers_at_cap_gt_station > 0
        ), "CAM-T captain should have CAM-T class mates"

    def test_captain_swap_respects_existing_class_mates(self):
        """Captains with class mates should not be displaced by swaps."""
        # captain at station 1 has class mates, captain at station 2 does not
        # swap should NOT occur because it would displace a happy captain
        participants = [
            MockParticipant("Cap_CS", "captain", "CS"),
            MockParticipant("Cap_CAM-T", "captain", "CAM-T"),
            # station 1: CS workers (matches Cap_CS)
            MockParticipant("W1", "worker", "CS"),
            MockParticipant("W2", "worker", "CS"),
            # station 2: AS workers (matches neither captain)
            MockParticipant("W3", "worker", "AS"),
            MockParticipant("W4", "worker", "AS"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        cap_cs = participants[0]
        cap_gt = participants[1]

        # CS workers should be grouped together at one station
        cs_workers = [
            p
            for p in participants
            if p.category_string == "CS" and p.assignment == "worker"
        ]
        cs_station = cs_workers[0].station

        # CS captain should be at the station with CS workers
        # (either through initial assignment or swap)
        assert cap_cs.station == cs_station, "CS captain should be with CS workers"

        # CAM-T captain should be at the other station (no CAM-T workers available)
        assert (
            cap_gt.station != cs_station
        ), "CAM-T captain should be at the other station"
