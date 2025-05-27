"""
Efficient test suite for autologic heat assignment system.

Tests focus on core functionality with minimal overhead using 
parametrized tests and single comprehensive test methods.
"""

import pytest
import os
import sys

# Add the source directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from Event import Event
from utils import roles_and_minima
from autologic import validate_inputs

# Create a compatibility wrapper for the old validate_feasibility function
def validate_feasibility(event, number_of_heats, number_of_stations, novice_denominator):
    """Wrapper for validate_inputs that returns True/False instead of raising exceptions"""
    try:
        validate_inputs(event, number_of_heats, number_of_stations, 
                       heat_size_parity=50, novice_size_parity=10, 
                       novice_denominator=novice_denominator)
        return True
    except ValueError:
        raise  # Re-raise to maintain test compatibility

# Helper function to create and load an event
def create_event(csv_file, number_of_heats=3, number_of_stations=5):
    """Create an event and load participants from CSV file"""
    event = Event()
    event.load_participants(csv_file)
    event.number_of_stations = number_of_stations
    return event


class TestEventLoading:
    """Test CSV loading and initial event setup"""
    
    def test_event_loads_correctly(self):
        """Single comprehensive test for event loading to avoid repeated file I/O"""
        event = create_event("tests/sample.csv", 3, 5)
        
        # Verify basic loading worked
        assert len(event.participants) == 100  # sample.csv has 100 participants
        assert len(event.categories) > 0
        assert all(p.name and p.category_string for p in event.participants)
        
        # Check that most participants are unassigned initially 
        # (some may have special assignments from CSV)
        unassigned = [p for p in event.participants if p.assignment is None]
        assert len(unassigned) >= 90  # Most should be unassigned initially
        
        # Verify role attributes were parsed
        instructors = event.get_participants_by_attribute("instructor")
        assert len(instructors) > 0
        assert all(p.instructor for p in instructors)


class TestRoleRequirements:
    """Test role counting and requirements"""
    
    @pytest.mark.parametrize("role,min_expected", [
        ("instructor", 5),   # At least 5 instructors in sample data
        ("timing", 5),       # At least 5 timing qualified
        ("grid", 5),         # At least 5 grid qualified  
        ("start", 3),        # At least 3 start qualified
        ("captain", 10)      # At least 10 captains
    ])
    def test_role_minimums(self, role, min_expected):
        """Parametrized test to verify minimum role counts efficiently"""
        event = create_event("tests/sample.csv", 3, 5)
        qualified_count = len(event.get_participants_by_attribute(role))
        assert qualified_count >= min_expected, f"Expected at least {min_expected} {role}s, got {qualified_count}"


class TestFeasibilityValidation:
    """Test the new feasibility validation feature"""
    
    def test_valid_configuration_passes(self):
        """Test that a valid configuration passes validation"""
        event = create_event("tests/sample.csv", 3, 5)
        # This should not raise an exception
        assert validate_feasibility(event, 3, 5, 3) is True
        
    def test_invalid_configuration_raises(self):
        """Test that impossible configurations are caught early"""
        event = create_event("tests/sample.csv", 3, 5)
        
        # Try to create 10 heats (would need way more qualified people)
        with pytest.raises(ValueError) as excinfo:
            validate_feasibility(event, 10, 5, 3)
        
        # Verify we get a helpful error message
        assert "Not enough" in str(excinfo.value)
        assert "need" in str(excinfo.value)


class TestCLIIntegration:
    """Test the command line interface"""
    
    def test_main_algorithm_completes(self, tmp_path):
        """Integration test - verify algorithm finds solution with simple data"""
        from autologic import main
        from click.testing import CliRunner
        
        # Create test data with many small categories to work with smart algorithm
        csv_path = tmp_path / "simple.csv"
        with open(csv_path, 'w') as f:
            f.write("name,category,novice,instructor,timing,grid,start,captain,special\n")
            # Create 30 participants across 10 categories (3 per category)
            # This prevents the smart algorithm from putting all of one category in one heat
            for i in range(30):
                cat = f"cat{i//3}"  # 10 categories, 3 people each
                # Spread roles across people and categories
                person_in_cat = i % 3
                is_novice = "TRUE" if i < 9 else ""  # First 9 are novices
                # Ensure each role has enough qualified people spread across categories
                is_instructor = "TRUE" if (i % 10) < 5 else ""  # ~15 instructors
                is_timing = "TRUE" if (i % 5) == 0 else ""  # 6 timing
                is_grid = "TRUE" if (i % 5) == 1 else ""  # 6 grid  
                is_start = "TRUE" if (i % 10) == 2 else ""  # 3 start
                is_captain = "TRUE" if (i % 2) == 0 else ""  # 15 captains
                f.write(f"P{i},{cat},{is_novice},{is_instructor},{is_timing},{is_grid},{is_start},{is_captain},\n")
        
        runner = CliRunner()
        result = runner.invoke(main, [
            '--csv', str(csv_path),
            '--heats', '3',
            '--max-iterations', '100'
        ])
        
        # Should complete successfully  
        assert result.exit_code == 0, f"Algorithm failed. Output:\n{result.output}"
        assert "accepted" in result.output
        
        # Should show role minimums
        assert "Role minimums" in result.output
        
    def test_impossible_configuration_exits_early(self):
        """Test that impossible configurations exit with clear error"""
        from autologic import main
        from click.testing import CliRunner
        
        runner = CliRunner()
        # Try 10 heats which should be impossible
        result = runner.invoke(main, [
            '--csv', 'tests/sample.csv',
            '--heats', '10'
        ])
        
        # Should exit with error
        assert result.exit_code == 1
        assert "Configuration Error" in result.output
        assert "Not enough" in result.output


class TestCaching:
    """Test that caching improves performance"""
    
    def test_repeated_lookups_are_cached(self):
        """Verify that repeated attribute lookups use cache"""
        event = create_event("tests/sample.csv", 3, 5)
        
        # First call populates cache
        instructors1 = event.get_participants_by_attribute("instructor")
        
        # Second call should return same object (cached)
        instructors2 = event.get_participants_by_attribute("instructor") 
        
        # Due to caching, these should be the exact same tuple object
        assert instructors1 is instructors2
        
        # Verify the cache is working by checking the internal cache
        assert len(event._attribute_cache) > 0  # Should have cached entries
        assert ('instructor', True) in event._attribute_cache  # Should have this specific entry


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.parametrize("participants,heats,should_fail", [
        (10, 1, False),   # All participants in one heat
        (10, 10, True),   # One participant per heat - not enough qualified workers
        (10, 11, True),   # More heats than participants
        (300, 3, False),  # Large event
        (15, 3, False),   # Perfectly divisible
        (16, 3, False),   # Not perfectly divisible
    ])
    def test_extreme_configurations(self, tmp_path, participants, heats, should_fail):
        """Test various extreme participant/heat configurations"""
        # Generate minimal valid CSV
        csv_path = tmp_path / "test.csv"
        with open(csv_path, 'w') as f:
            f.write("name,category,novice,instructor,timing,grid,start,captain,special\n")
            for i in range(participants):
                # Create varied roles: every 3rd is novice, every 5th is instructor, etc.
                f.write(f"P{i},cat{i%3},{i%3==0},{i%5==0},{i%7==0},{i%7==1},{i%7==2},{i%5==1},\n")
        
        if should_fail:
            with pytest.raises(ValueError):
                event = create_event(str(csv_path), heats, 5)
                validate_feasibility(event, heats, 5, 3)
        else:
            event = create_event(str(csv_path), heats, 5)
            assert validate_feasibility(event, heats, 5, 3)
    
    def test_all_novices_scenario(self, tmp_path):
        """Test when everyone is a novice (requires many instructors)"""
        csv_path = tmp_path / "all_novices.csv"
        with open(csv_path, 'w') as f:
            f.write("name,category,novice,instructor,timing,grid,start,captain,special\n")
            # 30 novices with sufficient qualified workers for all roles
            for i in range(30):
                # Ensure we have enough of each role
                f.write(f"Novice{i},a,TRUE,{i<10},{i<6},{i<6},{i<3},{i<15},\n")
        
        event = create_event(str(csv_path), 3, 5)
        # Should work: 10 novices per heat needs 3-4 instructors, we have 10 total
        assert validate_feasibility(event, 3, 5, 3)
    
    def test_no_qualified_workers(self, tmp_path):
        """Test when no one is qualified for required roles"""
        csv_path = tmp_path / "unqualified.csv"
        with open(csv_path, 'w') as f:
            f.write("name,category,novice,instructor,timing,grid,start,captain,special\n")
            # 30 people but no one qualified for anything
            for i in range(30):
                f.write(f"Person{i},a,,,,,,,\n")
        
        event = create_event(str(csv_path), 3, 5)
        with pytest.raises(ValueError) as exc:
            validate_feasibility(event, 3, 5, 3)
        # Should fail on one of the required roles
        assert "not enough" in str(exc.value).lower()
    
    def test_single_category_distribution(self, tmp_path):
        """Test when all participants are in one category"""
        csv_path = tmp_path / "single_category.csv"
        with open(csv_path, 'w') as f:
            f.write("name,category,novice,instructor,timing,grid,start,captain,special\n")
            # 30 people all in category 'a' with varied roles
            for i in range(30):
                f.write(f"Person{i},a,{i<6},{i%5==0},{i%4==0},{i%3==0},{i%7==0},{i%2==0},\n")
        
        event = create_event(str(csv_path), 3, 5)
        # This should work - the algorithm should handle single category
        assert len(event.categories) == 1
        assert validate_feasibility(event, 3, 5, 3)


class TestCSVValidation:
    """Test CSV file validation and error handling"""
    
    def test_missing_csv_file(self):
        """Test handling of non-existent CSV file"""
        with pytest.raises(FileNotFoundError) as exc:
            create_event("nonexistent.csv", 3, 5)
        assert "CSV file not found" in str(exc.value)
    
    def test_empty_csv_file(self, tmp_path):
        """Test handling of empty CSV file"""
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        
        with pytest.raises(ValueError) as exc:
            create_event(str(csv_path), 3, 5)
        assert "empty or has no headers" in str(exc.value)
    
    def test_missing_required_columns(self, tmp_path):
        """Test CSV missing required columns"""
        csv_path = tmp_path / "missing_cols.csv"
        # Missing 'category' column
        csv_path.write_text("name,novice\nJohn,TRUE\n")
        
        with pytest.raises(ValueError) as exc:
            create_event(str(csv_path), 3, 5)
        assert "missing required columns" in str(exc.value).lower()
        assert "category" in str(exc.value)
    
    def test_missing_participant_name(self, tmp_path):
        """Test CSV with missing participant names"""
        csv_path = tmp_path / "missing_name.csv"
        csv_path.write_text("name,category,novice\n,a,TRUE\n")
        
        with pytest.raises(ValueError) as exc:
            create_event(str(csv_path), 3, 5)
        assert "Row 2" in str(exc.value)
        assert "Missing participant name" in str(exc.value)
    
    def test_missing_category(self, tmp_path):
        """Test CSV with missing category"""
        csv_path = tmp_path / "missing_cat.csv"
        csv_path.write_text("name,category,novice\nJohn,,TRUE\n")
        
        with pytest.raises(ValueError) as exc:
            create_event(str(csv_path), 3, 5)
        assert "Row 2" in str(exc.value)
        assert "Missing category" in str(exc.value)
    
    def test_whitespace_handling(self, tmp_path):
        """Test that whitespace is properly stripped"""
        csv_path = tmp_path / "whitespace.csv"
        csv_path.write_text("name,category,novice\n  John Doe  ,  a  ,TRUE\n")
        
        event = create_event(str(csv_path), 1, 5)
        assert event.participants[0].name == "John Doe"
        assert event.participants[0].category_string == "a"


# Optional: Performance benchmark (not run by default)
@pytest.mark.skip(reason="Performance test - run manually if needed")
def test_performance_improvement():
    """Manual test to verify performance improvement from caching"""
    import time
    
    event = create_event("tests/sample.csv", 3, 5)
    
    # Time 1000 lookups
    start = time.time()
    for _ in range(1000):
        event.get_participants_by_attribute("instructor")
        event.get_participants_by_attribute("timing")
        event.get_participants_by_attribute("novice")
    elapsed = time.time() - start
    
    print(f"\n1000 lookups took {elapsed:.3f} seconds")
    cache_info = event.get_participants_by_attribute.cache_info()
    print(f"Cache hits: {cache_info.hits}, misses: {cache_info.misses}")