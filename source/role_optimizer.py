"""Optimized role assignment that handles multi-qualified participants."""

from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RoleAssignmentOptimizer:
    """
    Optimizes role assignments when participants are qualified for multiple roles.
    Uses a look-ahead approach to avoid creating scarcity issues.
    """
    
    def __init__(self, heat: Any, roles_and_minima: Dict[str, int]):
        self.heat = heat
        self.roles_and_minima = roles_and_minima
        self.participants = list(heat.participants)
        
        # Analyze participant qualifications
        self._analyze_qualifications()
        
    def _analyze_qualifications(self):
        """Build a map of participants and their qualifications."""
        self.participant_roles = defaultdict(set)
        self.role_participants = defaultdict(set)
        
        for p in self.participants:
            for role in self.roles_and_minima:
                if getattr(p, role, False):
                    self.participant_roles[p.name].add(role)
                    self.role_participants[role].add(p.name)
        
        # Calculate flexibility score for each participant
        self.flexibility = {}
        for p in self.participants:
            self.flexibility[p.name] = len(self.participant_roles[p.name])
    
    def assign_roles(self) -> Tuple[bool, Dict[str, str]]:
        """
        Assign roles optimally to avoid scarcity issues.
        
        Returns:
            (success, assignments) where assignments maps participant name to role
        """
        # Debug: Log initial state
        logger.debug(f"\nStarting role assignment for heat with {len(self.participants)} participants")
        logger.debug(f"Role requirements: {self.roles_and_minima}")
        
        # Debug: Check available resources
        for role, minimum in self.roles_and_minima.items():
            qualified = [p for p in self.participants if getattr(p, role, False)]
            logger.debug(f"  {role}: need {minimum}, have {len(qualified)} qualified")
            if len(qualified) < minimum:
                logger.warning(f"  WARNING: Not enough {role}s! Need {minimum}, only have {len(qualified)}")
        
        # First, identify critical assignments (people who MUST fill certain roles)
        critical_assignments = self._find_critical_assignments()
        logger.debug(f"Critical assignments found: {len(critical_assignments)}")
        
        # Try multiple strategies
        strategies = [
            ("lookahead", self._assign_with_lookahead),
            ("backtracking", self._assign_with_backtracking),
            ("greedy_smart", self._assign_greedy_smart)
        ]
        
        for strategy_name, strategy in strategies:
            logger.debug(f"\nTrying strategy: {strategy_name}")
            assignments = strategy(critical_assignments.copy())
            if assignments and self._validate_assignments(assignments):
                logger.debug(f"SUCCESS with {strategy_name}: {len(assignments)} assignments made")
                return True, assignments
            else:
                logger.debug(f"FAILED with {strategy_name}")
                if assignments:
                    # Debug why validation failed
                    role_counts = defaultdict(int)
                    for role in assignments.values():
                        role_counts[role] += 1
                    for role, minimum in self.roles_and_minima.items():
                        if role_counts[role] < minimum:
                            logger.debug(f"  Validation failed: {role} has {role_counts[role]}/{minimum}")
                
        logger.error("All strategies failed to find valid role assignments")
        return False, {}
    
    def _find_critical_assignments(self) -> Dict[str, str]:
        """Find participants who must be assigned to specific roles."""
        # For tight constraints, don't pre-assign critical roles
        # Let the optimization algorithms handle it
        return {}
    
    def _assign_with_lookahead(self, initial_assignments: Dict[str, str]) -> Dict[str, str]:
        """Assign roles considering future constraints."""
        assignments = initial_assignments.copy()
        assigned_participants = set(assignments.keys())
        
        # Calculate remaining needs
        remaining_needs = {}
        for role, minimum in self.roles_and_minima.items():
            already_assigned = sum(1 for r in assignments.values() if r == role)
            remaining_needs[role] = minimum - already_assigned
        
        # Define role priority (higher priority = lower number)
        role_priority = {
            'timing': 1,
            'instructor': 2, 
            'grid': 3,
            'start': 4,
            'captain': 5
        }
        
        # Sort roles by scarcity and priority
        role_scarcity = []
        for role, need in remaining_needs.items():
            if need > 0:
                available = len([p for p in self.participants 
                               if p.name not in assigned_participants 
                               and getattr(p, role, False)])
                scarcity = need / max(available, 0.1)  # Higher = more scarce
                priority = role_priority.get(role, 10)  # Default low priority
                # Combined score: prioritize by role importance, then by scarcity
                combined_score = (10 - priority) + scarcity
                role_scarcity.append((role, combined_score, need))
        
        role_scarcity.sort(key=lambda x: x[1], reverse=True)
        
        # Assign roles in order of scarcity
        for role, _, need in role_scarcity:
            # Find available participants for this role
            candidates = []
            for p in self.participants:
                if (p.name not in assigned_participants and 
                    getattr(p, role, False)):
                    # Calculate impact score (lower is better)
                    impact = self._calculate_assignment_impact(
                        p, role, assignments, assigned_participants
                    )
                    candidates.append((p, impact))
            
            # Sort by impact (assign those with least impact first)
            candidates.sort(key=lambda x: x[1])
            
            # Assign needed participants
            for i in range(min(need, len(candidates))):
                participant = candidates[i][0]
                assignments[participant.name] = role
                assigned_participants.add(participant.name)
                
        return assignments
    
    def _calculate_assignment_impact(self, participant: Any, role: str, 
                                   assignments: Dict[str, str], 
                                   assigned: Set[str]) -> float:
        """
        Calculate the impact of assigning a participant to a role.
        Lower impact is better.
        """
        impact = 0.0
        
        # Check how this assignment affects other roles
        for other_role in self.roles_and_minima:
            if other_role == role:
                continue
                
            # How many people are still available for this role?
            available = 0
            for p in self.participants:
                if (p.name not in assigned and 
                    p.name != participant.name and
                    getattr(p, other_role, False)):
                    available += 1
            
            # How many do we still need?
            already_assigned = sum(1 for r in assignments.values() if r == other_role)
            still_need = self.roles_and_minima[other_role] - already_assigned
            
            # If this participant could fill this role and we're tight on resources
            if getattr(participant, other_role, False) and still_need > 0:
                scarcity = still_need / max(available, 0.1)
                impact += scarcity
        
        # Prefer using less flexible people (save multi-qualified for later)
        impact -= self.flexibility[participant.name] * 0.1
        
        return impact
    
    def _assign_with_backtracking(self, initial_assignments: Dict[str, str]) -> Dict[str, str]:
        """Use backtracking to find a valid assignment."""
        assignments = initial_assignments.copy()
        assigned = set(assignments.keys())
        
        # Get unassigned participants sorted by flexibility (least flexible first)
        unassigned = sorted(
            [p for p in self.participants if p.name not in assigned],
            key=lambda p: self.flexibility[p.name]
        )
        
        # Try to assign remaining roles
        if self._backtrack(unassigned, 0, assignments):
            return assignments
        return {}
    
    def _backtrack(self, unassigned: List[Any], index: int, 
                   assignments: Dict[str, str]) -> bool:
        """Recursive backtracking to find valid assignments."""
        # Base case: all assigned
        if index >= len(unassigned):
            return self._validate_assignments(assignments)
        
        participant = unassigned[index]
        
        # Define role priority
        role_priority = {'timing': 1, 'instructor': 2, 'grid': 3, 'start': 4, 'captain': 5}
        
        # Get roles sorted by priority and scarcity
        role_options = []
        for role in self.roles_and_minima:
            if getattr(participant, role, False):
                assigned_count = sum(1 for r in assignments.values() if r == role)
                if assigned_count < self.roles_and_minima[role]:
                    # Count how many other unassigned people can do this role
                    others_available = sum(1 for i in range(index + 1, len(unassigned))
                                         if getattr(unassigned[i], role, False))
                    remaining_need = self.roles_and_minima[role] - assigned_count
                    scarcity = remaining_need / max(others_available + 1, 0.1)
                    priority = role_priority.get(role, 10)
                    # Combined score: prioritize by role importance, then by scarcity
                    combined_score = (10 - priority) + scarcity
                    role_options.append((role, combined_score))
        
        # Sort by combined score (try high priority + scarce roles first)
        role_options.sort(key=lambda x: x[1], reverse=True)
        
        # Try each role in order of scarcity
        for role, _ in role_options:
            assignments[participant.name] = role
            
            if self._backtrack(unassigned, index + 1, assignments):
                return True
            
            # Backtrack
            del assignments[participant.name]
        
        # No valid assignment found
        return False
    
    def _assign_greedy_smart(self, initial_assignments: Dict[str, str]) -> Dict[str, str]:
        """Greedy assignment with smart heuristics."""
        assignments = initial_assignments.copy()
        assigned = set(assignments.keys())
        
        # Sort participants by flexibility (least flexible first)
        participants = sorted(
            [p for p in self.participants if p.name not in assigned],
            key=lambda p: self.flexibility[p.name]
        )
        
        for participant in participants:
            # Find the best role for this participant
            best_role = None
            best_score = float('-inf')
            
            for role in self.roles_and_minima:
                if not getattr(participant, role, False):
                    continue
                    
                # Check if role needs more people
                assigned_count = sum(1 for r in assignments.values() if r == role)
                if assigned_count >= self.roles_and_minima[role]:
                    continue
                
                # Calculate score (higher is better)
                role_priority = {'timing': 1, 'instructor': 2, 'grid': 3, 'start': 4, 'captain': 5}
                priority = role_priority.get(role, 10)
                
                # Start with role priority
                score = 100 - priority * 10
                
                # Add scarcity bonus
                remaining_candidates = sum(1 for p in self.participants
                                         if p.name not in assigned
                                         and p.name != participant.name
                                         and getattr(p, role, False))
                remaining_need = self.roles_and_minima[role] - assigned_count
                if remaining_candidates > 0:
                    scarcity = remaining_need / remaining_candidates
                    score += scarcity * 5
                
                if score > best_score:
                    best_score = score
                    best_role = role
            
            if best_role:
                assignments[participant.name] = best_role
                assigned.add(participant.name)
                
        return assignments
    
    def _validate_assignments(self, assignments: Dict[str, str]) -> bool:
        """Check if assignments meet all role requirements."""
        role_counts = defaultdict(int)
        
        for role in assignments.values():
            role_counts[role] += 1
        
        for role, minimum in self.roles_and_minima.items():
            if role_counts[role] < minimum:
                return False
                
        return True