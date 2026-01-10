"""Tests for station assignment logic."""

import pytest
from autologic.stations import assign_stations, normalize_category


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


class TestNormalizeCategory:
    """Tests for category normalization."""

    def test_novice_prefix_stripped(self):
        # novice classes should be normalized to their base class
        assert normalize_category("NOVCS") == "CS"
        assert normalize_category("NOVGT") == "GT"
        assert normalize_category("NOVCST") == "CST"
        assert normalize_category("NOVAS") == "AS"

    def test_sr_prefix_normalized(self):
        # street-related classes should all normalize to SR
        assert normalize_category("SR1") == "SR"
        assert normalize_category("SR2") == "SR"
        assert normalize_category("SR") == "SR"

    def test_p_prefix_normalized(self):
        # prepared classes should all normalize to P
        assert normalize_category("P1") == "P"
        assert normalize_category("P2") == "P"
        assert normalize_category("P") == "P"

    def test_regular_category_unchanged(self):
        # standard categories should pass through unchanged
        assert normalize_category("CS") == "CS"
        assert normalize_category("GT") == "GT"
        assert normalize_category("CAM-C") == "CAM-C"
        assert normalize_category("AS") == "AS"

    def test_case_insensitive(self):
        # normalization should handle case variations
        assert normalize_category("novcs") == "CS"
        assert normalize_category("NovGT") == "GT"


class TestAssignStations:
    """Tests for station assignment algorithm."""

    def test_workers_get_stations(self):
        # all workers should receive station assignments
        participants = [
            MockParticipant("Alice", "worker", "CS"),
            MockParticipant("Bob", "worker", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        assert participants[0].station is not None
        assert participants[1].station is not None
        assert participants[0].station in (1, 2)
        assert participants[1].station in (1, 2)

    def test_captains_get_stations(self):
        # captains should also receive station assignments
        participants = [
            MockParticipant("Alice", "captain", "CS"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 3)

        assert participants[0].station in (1, 2, 3)

    def test_non_station_roles_get_none(self):
        # instructor, timing, grid, start, special should not get stations
        participants = [
            MockParticipant("Alice", "instructor", "CS"),
            MockParticipant("Bob", "timing", "GT"),
            MockParticipant("Carol", "grid", "AS"),
            MockParticipant("Dave", "start", "BS"),
            MockParticipant("Eve", "special", "ES"),
            MockParticipant("Frank", "worker", "FS"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        assert participants[0].station is None  # instructor
        assert participants[1].station is None  # timing
        assert participants[2].station is None  # grid
        assert participants[3].station is None  # start
        assert participants[4].station is None  # special
        assert participants[5].station is not None  # worker gets station

    def test_same_category_grouped_together(self):
        # participants from the same category should be at the same station
        participants = [
            MockParticipant("Alice", "worker", "CS"),
            MockParticipant("Bob", "worker", "CS"),
            MockParticipant("Carol", "worker", "GT"),
            MockParticipant("Dave", "worker", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        # CS participants should be at same station
        assert participants[0].station == participants[1].station
        # GT participants should be at same station
        assert participants[2].station == participants[3].station

    def test_novice_grouped_with_base_class(self):
        # novices should be grouped with their base class when capacity allows
        # use 4 workers across 2 stations (2 per station) so grouping is possible
        participants = [
            MockParticipant("Alice", "worker", "CS"),
            MockParticipant("Bob", "worker", "NOVCS"),
            MockParticipant("Carol", "worker", "GT"),
            MockParticipant("Dave", "worker", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        # CS and NOVCS should be at same station (both normalize to "CS")
        assert participants[0].station == participants[1].station
        # GT workers should be at same station
        assert participants[2].station == participants[3].station

    def test_even_distribution_priority(self):
        # even distribution should take priority over class grouping
        # 6 workers across 3 stations with different categories
        participants = [MockParticipant(f"P{i}", "worker", f"C{i}") for i in range(6)]
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
            MockParticipant("B1", "worker", "GT"),
            MockParticipant("B2", "worker", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        # CS should all be together
        cs_stations = {p.station for p in participants[:3]}
        assert len(cs_stations) == 1

        # GT should all be together
        gt_stations = {p.station for p in participants[3:]}
        assert len(gt_stations) == 1

    def test_empty_heat(self):
        # should handle empty heat without error
        heat = MockHeat([])
        assign_stations(heat, 3)  # should not raise

    def test_zero_stations(self):
        # should handle zero stations gracefully
        participants = [MockParticipant("Alice", "worker", "CS")]
        heat = MockHeat(participants)
        assign_stations(heat, 0)  # should not raise
        assert participants[0].station is None

    def test_mixed_workers_and_captains(self):
        # captains are assigned first (1 per station), workers distributed separately
        participants = [
            MockParticipant("Alice", "worker", "CS"),
            MockParticipant("Bob", "captain", "CS"),
            MockParticipant("Carol", "worker", "GT"),
            MockParticipant("Dave", "captain", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 2)

        # all should have stations
        for p in participants:
            assert p.station is not None
            assert p.station in (1, 2)

        # captains should be on different stations (1 per station)
        bob_captain = participants[1]
        dave_captain = participants[3]
        assert bob_captain.station != dave_captain.station

    def test_one_captain_per_station(self):
        # exactly 1 captain should be assigned to each station
        participants = [
            MockParticipant("Cap1", "captain", "CS"),
            MockParticipant("Cap2", "captain", "GT"),
            MockParticipant("Cap3", "captain", "AS"),
            MockParticipant("Cap4", "captain", "BS"),
            MockParticipant("W1", "worker", "CS"),
            MockParticipant("W2", "worker", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 4)

        # captains should be assigned to stations 1, 2, 3, 4 (one each)
        captain_stations = [p.station for p in participants[:4]]
        assert sorted(captain_stations) == [1, 2, 3, 4]

        # workers should also have stations
        for p in participants[4:]:
            assert p.station is not None
            assert p.station in (1, 2, 3, 4)

    def test_single_station(self):
        # all participants should go to station 1
        participants = [
            MockParticipant("Alice", "worker", "CS"),
            MockParticipant("Bob", "worker", "GT"),
            MockParticipant("Carol", "captain", "AS"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 1)

        for p in participants:
            assert p.station == 1

    def test_many_stations_few_participants(self):
        # participants should still get assigned even with more stations than people
        participants = [
            MockParticipant("Alice", "worker", "CS"),
            MockParticipant("Bob", "worker", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 10)

        assert participants[0].station is not None
        assert participants[1].station is not None
        # should be distributed to different stations
        assert participants[0].station != participants[1].station

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
            # 2 GT participants
            MockParticipant("GT1", "worker", "GT"),
            MockParticipant("GT2", "worker", "GT"),
        ]
        heat = MockHeat(participants)
        assign_stations(heat, 4)

        # GT should be at the same station (closest fit for capacity 2)
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
            MockParticipant("Cap_GT", "captain", "GT"),
            # GT workers will fill one station
            MockParticipant("W1", "worker", "GT"),
            MockParticipant("W2", "worker", "GT"),
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
            if p.station == cap_gt.station and p.category_string == "GT"
        )

        # both captains should have class mates after swap optimization
        assert cs_workers_at_cap_cs_station > 0, "CS captain should have CS class mates"
        assert gt_workers_at_cap_gt_station > 0, "GT captain should have GT class mates"

    def test_captain_swap_respects_existing_class_mates(self):
        """Captains with class mates should not be displaced by swaps."""
        # captain at station 1 has class mates, captain at station 2 does not
        # swap should NOT occur because it would displace a happy captain
        participants = [
            MockParticipant("Cap_CS", "captain", "CS"),
            MockParticipant("Cap_GT", "captain", "GT"),
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

        # GT captain should be at the other station (no GT workers available)
        assert cap_gt.station != cs_station, "GT captain should be at the other station"
