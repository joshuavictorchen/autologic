#!/usr/bin/env python3
"""
Relaxed constraint solver for AutoLogic.

This module provides "best effort" solutions that work even when strict
constraints cannot be met, documenting all deviations for coordinator review.
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class RelaxedSolution:
    """Container for a solution with documented constraint violations."""
    
    def __init__(self):
        self.success = True  # Always "succeeds" but documents issues
        self.violations = []
        self.suggestions = []
        self.heat_assignments = {}
        self.role_assignments = {}
        self.metrics = {}
        
    def add_violation(self, heat: int, role: str, severity: str, 
                     description: str, mitigation: Optional[str] = None):
        """Add a constraint violation with optional mitigation suggestion."""
        violation = {
            'heat': heat,
            'role': role,
            'severity': severity,  # 'critical', 'moderate', 'minor'
            'description': description,
            'mitigation': mitigation
        }
        self.violations.append(violation)
        
    def add_suggestion(self, suggestion: str):
        """Add a general suggestion for the coordinator."""
        self.suggestions.append(suggestion)


def find_best_effort_solution(event: Any, number_of_heats: int, 
                            roles_and_minima: Dict[str, int],
                            allow_partial_qualifications: bool = True) -> RelaxedSolution:
    """
    Find the best possible solution even if constraints can't be perfectly met.
    
    Args:
        event: Event object with participants and heats
        number_of_heats: Number of heats to create
        roles_and_minima: Minimum role requirements
        allow_partial_qualifications: Whether to suggest partially qualified workers
        
    Returns:
        RelaxedSolution with assignments and documented violations
    """
    solution = RelaxedSolution()
    
    # Analyze role availability across all heats
    total_role_counts = defaultdict(int)
    for role in roles_and_minima:
        total_role_counts[role] = len(event.get_participants_by_attribute(role))
    
    # Check each heat and assign roles with relaxed constraints
    for h_idx in range(number_of_heats):
        heat = event.heats[h_idx]
        heat_assignments = {}
        
        # Count available qualified workers in this heat
        role_availability = {}
        for role in roles_and_minima:
            qualified = [p for p in heat.participants if getattr(p, role, False)]
            role_availability[role] = qualified
        
        # Try to assign each role
        assigned_participants = set()
        
        for role, minimum in roles_and_minima.items():
            available = [p for p in role_availability[role] 
                        if p.name not in assigned_participants]
            assigned_count = 0
            
            # Assign as many as we can
            for participant in available[:minimum]:
                heat_assignments[participant.name] = role
                assigned_participants.add(participant.name)
                assigned_count += 1
            
            # Document shortfalls
            if assigned_count < minimum:
                shortfall = minimum - assigned_count
                severity = 'critical' if role in ['timing', 'start'] else 'moderate'
                
                # Look for specific mitigation options
                mitigation = None
                
                if role == 'timing':
                    # Check if timing workers from other heats could help
                    total_timing = total_role_counts['timing']
                    if total_timing >= number_of_heats * minimum:
                        mitigation = "Consider timing flexibility - allow timing workers to work in different heats"
                    else:
                        # Look for people with related experience
                        mitigation = "Need to recruit additional timing workers or train qualified participants"
                
                elif role == 'instructor':
                    novice_count = len([p for p in heat.participants if p.novice])
                    if novice_count > 0:
                        mitigation = f"With {novice_count} novices, consider pairing them or having experienced drivers help"
                
                elif role == 'captain':
                    mitigation = "Consider having experienced workers cover multiple stations"
                
                solution.add_violation(
                    heat=h_idx + 1,
                    role=role,
                    severity=severity,
                    description=f"Heat {h_idx + 1} has {assigned_count}/{minimum} {role} workers",
                    mitigation=mitigation
                )
        
        solution.heat_assignments[h_idx] = heat_assignments
    
    # Add general analysis
    _add_general_analysis(solution, event, number_of_heats, roles_and_minima, total_role_counts)
    
    return solution


def _add_general_analysis(solution: RelaxedSolution, event: Any, 
                         number_of_heats: int, roles_and_minima: Dict[str, int],
                         total_role_counts: Dict[int, int]):
    """Add overall analysis and suggestions to the solution."""
    
    # Check if timing flexibility would help
    total_timing_needed = number_of_heats * roles_and_minima.get('timing', 2)
    total_timing_available = total_role_counts.get('timing', 0)
    
    if total_timing_available >= total_timing_needed:
        solution.add_suggestion(
            "Timing flexibility could solve timing constraints - "
            f"you have {total_timing_available} timing workers for {total_timing_needed} slots"
        )
    
    # Check for multi-qualified workers who could help
    multi_qualified = []
    for p in event.participants:
        qual_count = sum(1 for role in roles_and_minima if getattr(p, role, False))
        if qual_count >= 2:
            roles = [role for role in roles_and_minima if getattr(p, role, False)]
            multi_qualified.append((p.name, roles))
    
    if multi_qualified:
        solution.add_suggestion(
            f"You have {len(multi_qualified)} multi-qualified workers who could fill critical gaps"
        )
    
    # Check for potential cross-training opportunities
    for role in ['timing', 'grid', 'start']:
        if total_role_counts.get(role, 0) < number_of_heats * roles_and_minima.get(role, 0):
            solution.add_suggestion(
                f"Consider training additional {role} workers before the event"
            )


def format_relaxed_solution(solution: RelaxedSolution, event: Any, 
                          number_of_heats: int) -> str:
    """Format the relaxed solution for display."""
    output = []
    
    # Header
    output.append("\nBEST EFFORT SOLUTION")
    output.append("=" * 60)
    
    # Summary of violations
    if solution.violations:
        critical = [v for v in solution.violations if v['severity'] == 'critical']
        moderate = [v for v in solution.violations if v['severity'] == 'moderate']
        
        output.append(f"\nConstraint Violations: {len(critical)} critical, {len(moderate)} moderate")
        output.append("-" * 40)
        
        # Group by heat
        for h_idx in range(number_of_heats):
            heat_violations = [v for v in solution.violations if v['heat'] == h_idx + 1]
            if heat_violations:
                output.append(f"\nHeat {h_idx + 1}:")
                for v in heat_violations:
                    icon = "🔴" if v['severity'] == 'critical' else "🟡"
                    output.append(f"  {icon} {v['description']}")
                    if v['mitigation']:
                        output.append(f"     → {v['mitigation']}")
    
    # Suggestions
    if solution.suggestions:
        output.append("\n\nSUGGESTIONS FOR COORDINATOR")
        output.append("-" * 40)
        for i, suggestion in enumerate(solution.suggestions, 1):
            output.append(f"{i}. {suggestion}")
    
    # Specific workarounds
    output.append("\n\nPOTENTIAL WORKAROUNDS")
    output.append("-" * 40)
    
    # Check for timing flexibility potential
    timing_violations = [v for v in solution.violations if v['role'] == 'timing']
    if timing_violations:
        output.append("\nTiming Coverage:")
        output.append("  • Allow timing workers to work in different heats than they race")
        output.append("  • Consider having experienced participants help with timing")
        output.append("  • Ensure timing workers understand they may need to work multiple heats")
    
    # Check for instructor issues
    instructor_violations = [v for v in solution.violations if v['role'] == 'instructor']
    if instructor_violations:
        output.append("\nInstructor Coverage:")
        output.append("  • Pair novices so one instructor can supervise multiple")
        output.append("  • Have experienced non-instructor drivers provide informal guidance")
        output.append("  • Consider running a novice meeting before the event")
    
    return "\n".join(output)


def try_relaxed_assignment(event: Any, number_of_heats: int,
                         roles_and_minima: Dict[str, int]) -> Tuple[bool, Optional[RelaxedSolution]]:
    """
    Attempt to create a workable assignment with relaxed constraints.
    
    Returns:
        (success, solution) - success is True if a workable solution was found
    """
    try:
        solution = find_best_effort_solution(event, number_of_heats, roles_and_minima)
        
        # Add heat cycle time analysis
        heat_sizes = []
        for h_idx in range(number_of_heats):
            heat_sizes.append(len(event.heats[h_idx].participants))
        
        cycle_times = [size * 45 / 60 for size in heat_sizes]  # 45 seconds per run
        solution.metrics['heat_sizes'] = heat_sizes
        solution.metrics['cycle_times'] = cycle_times
        solution.metrics['timing_variance'] = max(cycle_times) - min(cycle_times)
        
        return True, solution
        
    except Exception as e:
        logger.error(f"Error in relaxed assignment: {e}")
        return False, None