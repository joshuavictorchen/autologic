"""Simple proven heat assignment algorithm."""

import random
import math
from typing import Dict, List, Any
from collections import defaultdict


def assign_categories_to_heats(event: Any, number_of_heats: int, 
                              heat_size_parity: int, max_attempts: int = 1000,
                              optimize_timing: bool = True) -> bool:
    """
    Assign categories to heats ensuring role requirements are met.
    
    If optimize_timing is True, finds the assignment with the lowest timing variance.
    
    Returns True if successful, False otherwise.
    """
    # Calculate constraints once
    total_participants = sum(len(c.participants) for c in event.categories.values())
    mean_size = total_participants / number_of_heats
    max_delta = math.ceil(total_participants / heat_size_parity)
    
    # Debug first time
    if max_attempts > 10:
        print(f"\n  DEBUG: Heat assignment constraints:")
        print(f"    Total participants: {total_participants}")
        print(f"    Mean heat size: {mean_size:.1f}")
        print(f"    Max size delta: {max_delta}")
    
    # Pre-calculate role requirements per heat
    # These are minimums based on the standard rules
    required_roles = {
        'timing': 2,
        'grid': 2, 
        'start': 1,
        'captain': 5,  # Assuming 5 stations
        'instructor': 3  # Will be adjusted based on novices
    }
    
    # Track best solution for timing optimization
    best_solution = None
    best_variance = float('inf')
    
    for attempt in range(max_attempts):
        # Reset all category assignments
        for category in event.categories.values():
            category.heat = None
            
        # Group categories by critical roles - count how many of each role
        role_categories = defaultdict(list)
        cat_role_counts = {}
        
        for cat in event.categories.values():
            # Count each critical role in this category
            role_counts = {}
            for role in ['start', 'timing', 'grid', 'instructor']:
                role_counts[role] = sum(1 for p in cat.participants if getattr(p, role, False))
            cat_role_counts[cat.name] = role_counts
            
            # Find the scarcest role this category provides
            scarce_role = None
            for role in ['start', 'timing', 'grid']:  # Order by scarcity
                if role_counts[role] > 0:
                    scarce_role = role
                    break
                    
            if scarce_role:
                role_categories[scarce_role].append(cat)
            else:
                role_categories['other'].append(cat)
        
        # Try different orderings
        if attempt % 4 == 0:
            # Prioritize start workers (scarcest)
            ordered_categories = (
                role_categories['start'] + 
                role_categories['timing'] + 
                role_categories['grid'] + 
                role_categories['other']
            )
        elif attempt % 4 == 1:
            # Mix scarce roles
            ordered_categories = []
            # Interleave scarce role categories
            max_len = max(len(role_categories[r]) for r in ['start', 'timing', 'grid'])
            for i in range(max_len):
                for role in ['start', 'timing', 'grid']:
                    if i < len(role_categories[role]):
                        ordered_categories.append(role_categories[role][i])
            ordered_categories.extend(role_categories['other'])
        elif attempt % 4 == 2:
            # Random shuffle within groups
            ordered_categories = []
            for role in ['start', 'timing', 'grid', 'other']:
                cats = role_categories[role][:]
                random.shuffle(cats)
                ordered_categories.extend(cats)
        else:
            # Completely random
            ordered_categories = list(event.categories.values())
            random.shuffle(ordered_categories)
        
        # Track heat state
        heat_sizes = [0] * number_of_heats
        heat_roles = [defaultdict(int) for _ in range(number_of_heats)]
        heat_categories = [[] for _ in range(number_of_heats)]
        
        # Assign categories
        success = True
        for category in ordered_categories:
            cat_size = len(category.participants)
            
            # Count roles in this category
            cat_roles = defaultdict(int)
            for p in category.participants:
                for role in required_roles:
                    if getattr(p, role, False):
                        cat_roles[role] += 1
            
            # Find best heat considering both size and role needs
            best_heat = None
            best_score = float('-inf')
            
            for h in range(number_of_heats):
                new_size = heat_sizes[h] + cat_size
                
                # Check size constraint - allow going towards the mean
                if heat_sizes[h] > 0:  # Don't check for empty heats
                    current_delta = abs(heat_sizes[h] - mean_size)
                    new_delta = abs(new_size - mean_size)
                    
                    # Allow if we're moving closer to the mean or within tolerance
                    if new_delta > current_delta and new_delta > max_delta:
                        continue
                
                # Calculate score based on role needs
                score = 0
                
                # Check each role - prioritize critical roles
                role_weights = {'start': 50, 'timing': 40, 'grid': 30, 'instructor': 20, 'captain': 10}
                for role, required in required_roles.items():
                    current = heat_roles[h][role]
                    provided = cat_roles[role]
                    weight = role_weights.get(role, 10)
                    
                    if current < required and provided > 0:
                        # This category helps meet an unmet need
                        score += min(provided, required - current) * weight
                    elif current >= required and provided > 0:
                        # Already met, slight penalty for excess
                        score -= provided * 0.1
                
                # Size balance factor
                score -= abs(new_size - mean_size) * 0.5
                
                if score > best_score:
                    best_score = score
                    best_heat = h
            
            if best_heat is None:
                success = False
                if attempt < 5:  # Debug first few attempts
                    print(f"\n  DEBUG: Could not place category {category.name} (size={cat_size})")
                    print(f"    Heat sizes: {heat_sizes}")
                    print(f"    Scores were: ", end="")
                    for h in range(number_of_heats):
                        new_size = heat_sizes[h] + cat_size
                        size_ok = heat_sizes[h] <= mean_size / 2 or abs(new_size - mean_size) <= max_delta
                        print(f"H{h}:{'OK' if size_ok else 'size'} ", end="")
                    print()
                break
                
            # Assign category
            category.set_heat(best_heat)
            heat_sizes[best_heat] += cat_size
            heat_categories[best_heat].append(category)
            
            # Update role counts
            for role, count in cat_roles.items():
                heat_roles[best_heat][role] += count
        
        if not success:
            continue
            
        # Verify each heat has minimum required roles
        valid = True
        for h in range(number_of_heats):
            for role, required in required_roles.items():
                if role == 'instructor':
                    # Adjust instructor requirement based on novices
                    novice_count = sum(
                        len([p for p in cat.participants if getattr(p, 'novice', False)])
                        for cat in heat_categories[h]
                    )
                    required = max(1, (novice_count + 2) // 3)  # 1 instructor per 3 novices
                    
                if heat_roles[h][role] < required:
                    valid = False
                    break
                    
            if not valid:
                break
                
        if valid:
            # Calculate timing variance for this solution
            min_cycle = min(heat_sizes) * 45 / 60  # 45 seconds per run
            max_cycle = max(heat_sizes) * 45 / 60
            variance = max_cycle - min_cycle
            
            if optimize_timing:
                # Save this solution if it's the best so far
                if variance < best_variance:
                    best_variance = variance
                    # Save the current assignments
                    best_solution = {}
                    for category in event.categories.values():
                        best_solution[category.name] = category.heat
                    
                    if attempt < 10 or attempt % 1000 == 0:  # Debug periodically
                        print(f"\n  Found better solution (attempt {attempt + 1}):")
                        print(f"    Heat sizes: {heat_sizes}")
                        print(f"    Cycle variance: {variance:.1f} minutes")
                        if attempt >= 10:
                            # Also show role distribution for debugging
                            for h in range(number_of_heats):
                                print(f"    Heat {h}: ", end="")
                                for role in ['instructor', 'timing', 'grid', 'start', 'captain']:
                                    print(f"{role}={heat_roles[h].get(role, 0)}", end=" ")
                                print()
                    
                    # Continue searching even with good solutions to ensure we find one that works
            else:
                # Not optimizing, just return the first valid solution
                return True
    
    # Apply the best solution if we found one
    if best_solution is not None:
        for cat_name, heat_num in best_solution.items():
            event.categories[cat_name].set_heat(heat_num)
        
        if best_variance < float('inf'):
            print(f"\n  Best solution found with {best_variance:.1f} minutes variance")
        
        return True
    
    # Debug: print why we failed
    if attempt == max_attempts - 1:
        print(f"\n  DEBUG: Failed after {max_attempts} attempts")
        print(f"  Last attempt role counts by heat:")
        for h in range(number_of_heats):
            print(f"    Heat {h}: ", end="")
            for role in ['timing', 'grid', 'start']:
                print(f"{role}={heat_roles[h][role]}", end=" ")
            print()
            
    return False


def randomize_heats(event: Any, number_of_heats: int) -> None:
    """Randomly assign categories to heats."""
    categories = list(event.categories.values())
    random.shuffle(categories)
    
    for i, category in enumerate(categories):
        category.set_heat(i % number_of_heats)