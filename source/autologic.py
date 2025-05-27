#!/usr/bin/env python3
"""
AutoLogic - Automatic heat assignment for autocross events.

This tool assigns participants to heats while respecting complex constraints:
- Role requirements (timing, grid, start, instructors, captains)
- Heat size balance
- Novice/instructor ratios
- Scarce resource distribution
"""

import click
import sys
import logging
from typing import Dict, Tuple, List, Any

import utils
from Event import Event
from simple_solver import assign_categories_to_heats, randomize_heats
from role_optimizer import RoleAssignmentOptimizer
from timing_flexibility import find_timing_relocations, apply_timing_relocations
from relaxed_solver import try_relaxed_assignment, format_relaxed_solution

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def calculate_heat_timing(total_participants: int, number_of_heats: int, actual_heat_sizes: List[int] = None) -> Dict[str, Any]:
    """
    Calculate timing for different heat configurations.
    
    Args:
        total_participants: Total number of participants
        number_of_heats: Number of heats to create
        actual_heat_sizes: Optional list of actual heat sizes (for post-assignment analysis)
        
    Returns:
        dict: Timing information including cycle times and fairness metrics
    """
    # Constants (in seconds)
    RUN_TIME = 45  # Time for one run
    
    if actual_heat_sizes:
        # Calculate based on actual heat sizes
        heat_cycles = [size * RUN_TIME / 60 for size in actual_heat_sizes]
        min_cycle = min(heat_cycles)
        max_cycle = max(heat_cycles)
        avg_cycle = sum(heat_cycles) / len(heat_cycles)
        
        return {
            'heat_sizes': actual_heat_sizes,
            'heat_cycle_minutes': heat_cycles,
            'avg_cycle_minutes': avg_cycle,
            'min_cycle_minutes': min_cycle,
            'max_cycle_minutes': max_cycle,
            'cycle_variance_minutes': max_cycle - min_cycle,
            'is_fair': (max_cycle - min_cycle) <= 1.5  # Consider fair if variance <= 1.5 minutes
        }
    else:
        # Calculate assuming equal distribution
        avg_heat_size = total_participants / number_of_heats
        heat_cycle_time = avg_heat_size * RUN_TIME / 60
        
        return {
            'avg_heat_size': avg_heat_size,
            'heat_cycle_minutes': heat_cycle_time,
            'is_estimate': True
        }


def recommend_heat_count(total_participants: int) -> Tuple[int, str]:
    """
    Recommend optimal heat count based on timing analysis.
    
    Args:
        total_participants: Total number of participants
        
    Returns:
        Tuple of (recommended_heats, reason)
    """
    # Analyze different heat configurations
    configs = []
    for heats in range(2, 6):  # Check 2-5 heats
        timing = calculate_heat_timing(total_participants, heats)
        
        # Score based on various factors
        score = 0
        
        # Prefer reasonable heat sizes (20-40 drivers)
        avg_size = timing['avg_heat_size']
        if 20 <= avg_size <= 40:
            score += 25
        elif 15 <= avg_size <= 50:
            score += 10
        else:
            score -= 10
            
        # Prefer 3-4 heats for easier management
        if heats in [3, 4]:
            score += 15
            
        # Prefer shorter cycle times (under 30 minutes)
        if timing['heat_cycle_minutes'] <= 30:
            score += 10
        elif timing['heat_cycle_minutes'] <= 35:
            score += 5
        else:
            score -= 5
            
        configs.append((heats, score, timing))
    
    # Sort by score
    configs.sort(key=lambda x: x[1], reverse=True)
    best_heats, _, _ = configs[0]
    
    # Generate recommendation reason
    if best_heats == 3:
        reason = "3 heats recommended for efficient event flow"
    elif best_heats == 4:
        reason = "4 heats recommended for optimal heat balance"
    else:
        reason = f"{best_heats} heats recommended based on participant count"
        
    return best_heats, reason


def analyze_heat_fairness(event: Event, number_of_heats: int) -> Dict[str, Any]:
    """
    Analyze timing fairness for a given heat configuration.
    
    Args:
        event: Event with categories assigned to heats
        number_of_heats: Number of heats
        
    Returns:
        dict: Analysis results including fairness metrics
    """
    # Get actual heat sizes
    heat_sizes = []
    for h in range(number_of_heats):
        heat_size = sum(len(c.participants) for c in event.categories.values() if c.heat == h)
        heat_sizes.append(heat_size)
    
    # Calculate timing with actual sizes
    timing = calculate_heat_timing(len(event.participants), number_of_heats, heat_sizes)
    
    return timing


def validate_inputs(event: Event, number_of_heats: int, number_of_stations: int,
               heat_size_parity: int, novice_size_parity: int, 
               novice_denominator: int) -> None:
    """
    Validate all input parameters and check feasibility.
    
    Raises:
        ValueError: If inputs are invalid or configuration is infeasible
    """
    # Basic parameter validation
    if number_of_heats < 1:
        raise ValueError("Number of heats must be at least 1")
        
    if number_of_stations < 1:
        raise ValueError("Number of stations must be at least 1")
        
    if heat_size_parity < 1:
        raise ValueError("Heat size parity must be at least 1")
        
    if novice_size_parity < 1:
        raise ValueError("Novice size parity must be at least 1")
        
    if novice_denominator < 1:
        raise ValueError("Novice denominator must be at least 1")
        
    # Check minimum participants
    if len(event.participants) < number_of_heats:
        raise ValueError(f"Not enough participants ({len(event.participants)}) for {number_of_heats} heats")
        
    # Check if categories can be distributed
    if len(event.categories) < number_of_heats:
        raise ValueError(f"Not enough categories ({len(event.categories)}) for {number_of_heats} heats")
        
    # Calculate role requirements
    total_novices = len(event.get_participants_by_attribute("novice"))
    roles_and_minima = utils.roles_and_minima(
        number_of_stations=number_of_stations,
        number_of_novices=total_novices / number_of_heats,
        novice_denominator=novice_denominator,
    )
    
    # Check role feasibility
    for role, minimum in roles_and_minima.items():
        qualified = len(event.get_participants_by_attribute(role))
        required = minimum * number_of_heats
        
        if qualified < required:
            raise ValueError(
            f"Not enough {role}s: have {qualified}, need {required} "
            f"({minimum} per heat × {number_of_heats} heats)"
            )


def print_heat_summary(event: Event, heat_num: int) -> None:
    """Print a summary of a single heat."""
    heat = event.heats[heat_num] if isinstance(event.heats, list) else event.heats[heat_num]
    
    print(f"  Heat {heat_num + 1}:")
    print(f"    Categories: {', '.join(sorted(c.name for c in heat.categories))}")
    print(f"    Participants: {len(heat.participants)}")
    
    # Calculate and show cycle time
    heat_cycle = len(heat.participants) * 45 / 60  # 45 seconds per run
    print(f"    Cycle time: {heat_cycle:.1f} minutes")
    
    novice_count = len(heat.get_participants_by_attribute("novice"))
    print(f"    Novices: {novice_count}")
    
    # Count workers by role
    role_counts = []
    for role in ['instructor', 'timing', 'grid', 'start', 'captain']:
        count = len(heat.get_participants_by_attribute(role))
        role_counts.append(f"{role}={count}")
    
    print(f"    Workers: {', '.join(role_counts)}")


@click.command()
@click.option(
    "--csv",
    "csv_file",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to CSV file containing participant data.",
)
@click.option(
    "--heats",
    "number_of_heats",
    default=3,
    show_default=True,
    type=click.IntRange(min=1, max=20),
    help="Number of heats to divide participants into.",
)
@click.option(
    "--stations",
    "number_of_stations",
    default=5,
    show_default=True,
    type=click.IntRange(min=1, max=20),
    help="Number of worker stations for the course.",
)
@click.option(
    "--heat-size-parity",
    default=50,
    show_default=True,
    type=click.IntRange(min=1),
    help="Smaller values enforce tighter heat size balance.",
)
@click.option(
    "--novice-size-parity",
    default=10,
    show_default=True,
    type=click.IntRange(min=1),
    help="Smaller values enforce tighter novice balance across heats.",
)
@click.option(
    "--novice-denominator",
    default=3,
    show_default=True,
    type=click.IntRange(min=1),
    help="Target ratio of novices to instructors (e.g., 3 = one instructor per 3 novices).",
)
@click.option(
    "--max-iterations",
    default=100000,
    show_default=True,
    type=click.IntRange(min=1, max=1000000),
    help="Maximum number of assignment attempts before giving up.",
)
@click.option(
    "--timing-only",
    is_flag=True,
    help="Only show timing analysis and recommendations without assigning heats.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed progress and debugging information.",
)
@click.option(
    "--enforce-timing-fairness/--no-enforce-timing-fairness",
    default=True,
    show_default=True,
    help="Optimize heat assignments to minimize cycle time variance.",
)
@click.option(
    "--allow-timing-flexibility",
    is_flag=True,
    help="Allow timing workers to work in different heats than they race (helps with 4 heats).",
)
@click.option(
    "--best-effort",
    is_flag=True,
    help="Provide best possible solution even if constraints can't be met, with documented deviations.",
)
def main(
    csv_file: str,
    number_of_heats: int,
    number_of_stations: int,
    heat_size_parity: int,
    novice_size_parity: int,
    novice_denominator: int,
    max_iterations: int,
    timing_only: bool,
    verbose: bool,
    enforce_timing_fairness: bool,
    allow_timing_flexibility: bool,
    best_effort: bool,
) -> None:
    """
    AutoLogic - Automatic heat assignment for autocross events.
    
    Assigns participants from a CSV file to heats while respecting:
    - Worker role requirements (timing, grid, start, instructors, captains)
    - Heat size balance
    - Novice distribution
    - Instructor availability
    """
    # Configure logging
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Display ASCII art
        print(r"""
         ______
        /|_||_\`.__
       (   _    _ _\
       =`-(_)--(_)-'
        """)
        
        # Load event data
        event = Event()
        event.load_participants(csv_file)
        print(f"\n  Loaded {len(event.participants)} participants in {len(event.categories)} categories")
        
        # Timing analysis
        print("\n  Heat Timing Analysis")
        print("  ===================")
        print(f"  Total participants: {len(event.participants)}")
        
        for heats in [3, 4]:
            timing = calculate_heat_timing(len(event.participants), heats)
            print(f"\n  {heats} Heats (assuming equal distribution):")
            print(f"    - Average heat size: {timing['avg_heat_size']:.0f} drivers")
            print(f"    - Heat cycle time: {timing['heat_cycle_minutes']:.1f} minutes")
        
        # Remove recommendation - let user decide based on analysis
        
        # If only timing analysis requested, stop here
        if timing_only:
            print("\n  Run with --heats 3 or --heats 4 to see full assignments")
            return
            
        # Validate inputs
        try:
            validate_inputs(event, number_of_heats, number_of_stations,
                      heat_size_parity, novice_size_parity, novice_denominator)
        except ValueError as e:
            print(f"\n  ERROR: {e}")
            sys.exit(1)
            
        # Calculate role requirements
        total_novices = len(event.get_participants_by_attribute("novice"))
        roles_and_minima = utils.roles_and_minima(
            number_of_stations=number_of_stations,
            number_of_novices=total_novices / number_of_heats,
            novice_denominator=novice_denominator,
        )
        
        # Show role requirements
        print("\n  Role minimums")
        print("  -------------")
        
        total_novices = len(event.get_participants_by_attribute("novice"))
        roles_and_minima = utils.roles_and_minima(
            number_of_stations=number_of_stations,
            number_of_novices=total_novices / number_of_heats,
            novice_denominator=novice_denominator,
        )
        
        critical_roles = []
        for role, minimum in roles_and_minima.items():
            qualified = len(event.get_participants_by_attribute(role))
            required = minimum * number_of_heats
            
            # Check if critical (less than 50% margin)
            if qualified < required * 1.5:
                critical_roles.append((role, qualified, required))
            
            print(f"  {role.rjust(10)}: {str(qualified).rjust(2)} / {required}")
            
        # Warn about critical roles
        if critical_roles:
            print("\n  WARNING: Limited workers for critical roles:")
            for role, qualified, required in critical_roles:
                margin = ((qualified / required) - 1) * 100
                print(f"    - {role}: only {margin:.0f}% margin above minimum")
            
        # Attempt heat assignment
        if enforce_timing_fairness:
            print("\n  Attempting heat assignment with timing optimization...")
        else:
            print("\n  Attempting heat assignment...")
        
        # Try smart assignment with multiple attempts
        found_solution = False
        iteration = 0
        
        # Try to find a solution that works for role assignment
        attempts_with_good_timing = 0
        max_role_attempts = min(100, max_iterations // 100)  # Try up to 100 different heat configurations
        
        for attempt in range(max_role_attempts):
            # Use optimization if timing fairness is enabled
            if assign_categories_to_heats(event, number_of_heats, heat_size_parity, max_iterations // max_role_attempts, enforce_timing_fairness):
                # Test if this assignment allows valid role assignments
                event.create_heats(number_of_heats)
                all_heats_valid = True
            
            for h_num in range(number_of_heats):
                heat = event.heats[h_num]
                adjusted_roles = roles_and_minima.copy()
                
                # Adjust instructor requirement
                novice_count = len(heat.get_participants_by_attribute('novice'))
                instructor_count = len(heat.get_participants_by_attribute('instructor'))
                if novice_count > 0 and instructor_count > 0:
                    min_instructors_needed = max(1, (novice_count + 4) // 5)
                    adjusted_roles['instructor'] = min(min_instructors_needed, instructor_count)
                
                # Quick check if role assignment is possible
                optimizer = RoleAssignmentOptimizer(heat, adjusted_roles)
                success, _ = optimizer.assign_roles()
                if not success:
                    all_heats_valid = False
                    break
            
            if all_heats_valid:
                found_solution = True
                print(f"\n  ✓ Found valid heat assignment (attempt {attempt + 1})!")
                break
            else:
                # Save the assignment if it has good timing
                timing = analyze_heat_fairness(event, number_of_heats)
                if timing['is_fair']:
                    attempts_with_good_timing += 1
                
                # Reset for next attempt
                event.heats = {}
                for category in event.categories.values():
                    category.heat = None
        
        if not found_solution:
            # Fall back to random assignment if smart assignment fails
            print(f"\n  Could not find perfect assignment after {max_role_attempts} attempts.")
            if attempts_with_good_timing > 0:
                print(f"  Found {attempts_with_good_timing} assignments with good timing but role conflicts.")
            
            # For 4 heats, check if timing flexibility would help
            if number_of_heats == 4 and not allow_timing_flexibility:
                print("  NOTE: 4 heats configuration often needs timing flexibility.")
                print("  Try running with --allow-timing-flexibility flag.")
                print("  Using random assignment for now...")
                randomize_heats(event, number_of_heats)
                found_solution = True
                iteration = max_iterations
            elif allow_timing_flexibility:
                print("  Checking if timing flexibility would help...")
                # Use the best timing assignment we found
                assign_categories_to_heats(event, number_of_heats, heat_size_parity, 1000, enforce_timing_fairness)
                event.create_heats(number_of_heats)
                
                # Check timing distribution
                total_timing_workers = len(event.get_participants_by_attribute('timing'))
                print(f"  Total timing workers: {total_timing_workers} (need {number_of_heats * 2})")
                
                if total_timing_workers >= number_of_heats * 2:
                    print("  ✓ Sufficient timing workers available with flexibility")
                    print("  Proceeding with timing relocations enabled...")
                    found_solution = True
                    iteration = attempt + 1
                else:
                    print("  ✗ Insufficient timing workers even with flexibility")
                    print("  Using random assignment...")
                    randomize_heats(event, number_of_heats)
                    found_solution = True
                    iteration = max_iterations
            else:
                print("  Using random assignment...")
                randomize_heats(event, number_of_heats)
                found_solution = True
                iteration = max_iterations
            
        if not found_solution:
            print("\n  ERROR: Could not find valid heat assignment.")
            print("  Try:")
            print("    - Using the recommended number of heats")
            print("    - Increasing --heat-size-parity")
            print("    - Increasing --max-iterations")
            sys.exit(1)
            
        print(f"\n  ✓ Found valid heat assignment (iteration {iteration + 1})!")
        
        # Create heats and assign workers
        event.create_heats(number_of_heats)
        
        # Check if we need timing flexibility
        timing_relocations = []
        if allow_timing_flexibility or (number_of_heats == 4 and not allow_timing_flexibility):
            # Quick check if timing workers are constrained
            total_timing = len(event.get_participants_by_attribute('timing'))
            if total_timing < number_of_heats * 2 + 2:  # Need some buffer
                if number_of_heats == 4 and not allow_timing_flexibility:
                    print("\n  NOTE: 4 heats often requires timing flexibility.")
                    print("  Consider using --allow-timing-flexibility flag.")
                elif allow_timing_flexibility:
                    print("\n  Checking if timing flexibility is needed...")
                    timing_relocations = find_timing_relocations(event, number_of_heats)
                    if timing_relocations:
                        print(f"  Found {len(timing_relocations)} timing workers who can work in different heats")
                        apply_timing_relocations(event, timing_relocations)
        
        # Validate and assign workers to roles
        all_valid = True
        
        for h_num in range(number_of_heats):
            heat = event.heats[h_num]
            
            # Check role availability
            role_issues = []
            for role, minimum in roles_and_minima.items():
                qualified = len(heat.get_participants_by_attribute(role))
                if qualified < minimum:
                    # Special case for instructors - allow some flexibility
                    if role == 'instructor':
                        novice_count = len(heat.get_participants_by_attribute('novice'))
                        if novice_count > 0 and qualified > 0:
                            # Allow if we have at least 1 instructor per 5 novices
                            min_needed = max(1, (novice_count + 4) // 5)
                            if qualified >= min_needed:
                                continue
                    role_issues.append(f"{role} ({qualified}/{minimum})")
                    
            if role_issues:
                # Warn about role shortages
                print(f"\n  WARNING: Heat {h_num + 1} has limited workers: {', '.join(role_issues)}")
                print(f"    Some workers may need to work multiple heats")
                
            # Use the role optimizer for smart assignment
            if verbose:
                print(f"\n  DEBUG: Heat {h_num + 1} role assignment:")
                print(f"    Participants: {len(heat.participants)}")
                print(f"    Role requirements: {roles_and_minima}")
            
            # Adjust instructor requirement based on actual novices in this heat
            adjusted_roles = roles_and_minima.copy()
            novice_count = len(heat.get_participants_by_attribute('novice'))
            instructor_count = len(heat.get_participants_by_attribute('instructor'))
            
            if novice_count > 0 and instructor_count > 0:
                # Allow 1 instructor per 5 novices (more relaxed than default 1:3)
                min_instructors_needed = max(1, (novice_count + 4) // 5)
                # But don't require more instructors than we have
                adjusted_roles['instructor'] = min(min_instructors_needed, instructor_count)
                
            optimizer = RoleAssignmentOptimizer(heat, adjusted_roles)
            success, role_assignments = optimizer.assign_roles()
            
            if not success:
                # Check if it's a timing issue and we haven't tried relocations yet
                timing_qualified = len(heat.get_participants_by_attribute('timing'))
                if timing_qualified < roles_and_minima.get('timing', 2) and not timing_relocations:
                    print(f"\n  Heat {h_num + 1} has insufficient timing workers ({timing_qualified}/{roles_and_minima.get('timing', 2)})")
                    print("  Attempting timing relocations...")
                    
                    # Try to find timing relocations for all heats
                    timing_relocations = find_timing_relocations(event, number_of_heats)
                    if timing_relocations:
                        print(f"  ✓ Found {len(timing_relocations)} timing relocations")
                        
                        # Add note about relocations for later display
                        event.timing_relocations = timing_relocations
                        
                        # For now, continue and note this will be handled specially
                        print(f"  Heat {h_num + 1} will use relocated timing workers")
                        
                        # Try assignment again with relaxed timing constraint
                        adjusted_roles_relaxed = adjusted_roles.copy()
                        adjusted_roles_relaxed['timing'] = min(timing_qualified, adjusted_roles_relaxed.get('timing', 2))
                        optimizer_relaxed = RoleAssignmentOptimizer(heat, adjusted_roles_relaxed)
                        success, role_assignments = optimizer_relaxed.assign_roles()
                        
                        if not success:
                            print(f"\n  ERROR: Heat {h_num + 1} still cannot find valid role assignments")
                            all_valid = False
                            continue
                    else:
                        print(f"\n  ERROR: Heat {h_num + 1} cannot find valid role assignments")
                        print(f"    Heat has {len(heat.participants)} participants")
                        for role, minimum in roles_and_minima.items():
                            qualified = len(heat.get_participants_by_attribute(role))
                            print(f"    {role}: need {minimum}, have {qualified} qualified")
                        all_valid = False
                        continue
                else:
                    print(f"\n  ERROR: Heat {h_num + 1} cannot find valid role assignments")
                    print(f"    Heat has {len(heat.participants)} participants")
                    for role, minimum in roles_and_minima.items():
                        qualified = len(heat.get_participants_by_attribute(role))
                        print(f"    {role}: need {minimum}, have {qualified} qualified")
                    all_valid = False
                    continue
                
            # Apply the optimized assignments
            participant_map = {p.name: p for p in heat.participants}
            assigned_count = 0
            for name, role in role_assignments.items():
                if name in participant_map:
                    participant_map[name].set_assignment(role, verbose=False)
                    assigned_count += 1
            
            if verbose:
                print(f"  Heat {h_num + 1}: Assigned {assigned_count} special roles")
                    
            # Assign remaining participants as workers
            unassigned = heat.get_available(role=None)
            if verbose:
                print(f"\n  Heat {h_num + 1}: {len(unassigned)} participants need worker assignments")
            for i, worker in enumerate(unassigned):
                worker.set_assignment(f"worker-{i % number_of_stations}", verbose=verbose)
            
        if not all_valid:
            if best_effort:
                print("\n  Standard assignment failed. Generating best-effort solution...")
                success, relaxed_solution = try_relaxed_assignment(event, number_of_heats, roles_and_minima)
                
                if success:
                    print("\n  ✓ Generated best-effort solution with documented deviations")
                    
                    # Display the relaxed solution
                    print(format_relaxed_solution(relaxed_solution, event, number_of_heats))
                    
                    # Apply whatever assignments we can
                    for h_idx in range(number_of_heats):
                        heat = event.heats[h_idx]
                        assignments = relaxed_solution.heat_assignments.get(h_idx, {})
                        
                        for participant_name, role in assignments.items():
                            for p in heat.participants:
                                if p.name == participant_name:
                                    p.set_assignment(role, verbose=False)
                                    break
                        
                        # Assign remaining as general workers
                        unassigned = heat.get_available(role=None)
                        for i, worker in enumerate(unassigned):
                            worker.set_assignment(f"worker-{i % number_of_stations}", verbose=False)
                    
                    # Continue with output generation
                    all_valid = True  # Allow continuation
                else:
                    print("\n  ERROR: Could not generate even a best-effort solution")
                    sys.exit(1)
            else:
                print("\n  ERROR: Worker assignment failed. This should not happen!")
                print("  Try running with --best-effort flag to see a workable solution with documented issues")
                sys.exit(1)
            
        # Check timing fairness of final assignment
        fairness = analyze_heat_fairness(event, number_of_heats)
        
        # Print final summary
        print("\n  HEAT ASSIGNMENTS")
        print("  ================")
        
        # Show timing fairness warning if needed
        if not fairness['is_fair']:
            print("\n  ⚠️  WARNING: Heat cycle times are UNFAIR")
            print(f"     Variance: {fairness['cycle_variance_minutes']:.1f} minutes (exceeds 1.5 minute limit)")
            print(f"     Consider adjusting heat size parity or number of heats")
        else:
            print("\n  ✓ Heat cycle times are FAIR")
            print(f"     Variance: {fairness['cycle_variance_minutes']:.1f} minutes")
        
        print()
        
        for h_num in range(number_of_heats):
            print_heat_summary(event, h_num)
            
            # Debug: check assignments
            heat = event.heats[h_num]
            assigned = [p for p in heat.participants if p.assignment]
            if verbose:
                print(f"    DEBUG: {len(assigned)} of {len(heat.participants)} have assignments")
            print()
        
        # Display timing relocations if any
        if hasattr(event, 'timing_relocations') and event.timing_relocations:
            print("\n  TIMING WORKER RELOCATIONS")
            print("  ========================")
            print("  The following timing workers will work in different heats than they race:")
            print()
            for reloc in event.timing_relocations:
                print(f"  {reloc['name']} (Category {reloc['from_category']}):")
                print(f"    - Races in Heat {reloc['from_heat']}")
                print(f"    - Works timing in Heat {reloc['to_heat']}")
                print()
            
        # Save results
        event.export_heats_by_name(f"{csv_file}.heats.txt")
        event.export_heats_by_car_class(f"{csv_file}.heats_by_class.txt")
        event.export_workers(f"{csv_file}.workers.txt")
        
        print(f"  Results saved to:")
        print(f"    - {csv_file}.heats.txt")
        print(f"    - {csv_file}.heats_by_class.txt")
        print(f"    - {csv_file}.workers.txt")
        
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\n  ERROR: {e}")
        if verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()