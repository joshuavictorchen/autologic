"""Simple timing flexibility module to allow timing workers to work in different heats."""

from typing import Dict, List, Set, Tuple, Any
import logging

logger = logging.getLogger(__name__)


def find_timing_relocations(event: Any, number_of_heats: int) -> List[Dict[str, Any]]:
    """
    Find timing workers who can be relocated to different heats to satisfy constraints.
    
    This allows timing workers to work timing in one heat while running in another,
    which is often necessary for 4-heat configurations.
    
    Returns:
        List of relocations, each containing:
        - participant: The participant object
        - from_heat: Heat they run in
        - to_heat: Heat they work timing in
        - name: Participant name
        - from_category: Their car category
    """
    relocations = []
    
    # First, analyze timing worker distribution across heats
    heat_timing_workers = {}
    timing_deficit = {}
    
    for h_idx in range(number_of_heats):
        heat = event.heats[h_idx]
        timing_workers = [p for p in heat.participants if getattr(p, 'timing', False)]
        heat_timing_workers[h_idx] = timing_workers
        
        # Check if this heat has enough timing workers (need 2 per heat)
        deficit = 2 - len(timing_workers)
        timing_deficit[h_idx] = deficit
        
        logger.debug(f"Heat {h_idx + 1}: {len(timing_workers)} timing workers, deficit: {deficit}")
    
    # Find heats that need timing workers
    deficit_heats = [h for h, d in timing_deficit.items() if d > 0]
    surplus_heats = [h for h, d in timing_deficit.items() if d < 0]
    
    if not deficit_heats:
        logger.debug("No timing relocations needed")
        return relocations
    
    logger.debug(f"Deficit heats: {deficit_heats}, Surplus heats: {surplus_heats}")
    
    # Try to relocate timing workers from surplus heats to deficit heats
    for deficit_heat in deficit_heats:
        needed = timing_deficit[deficit_heat]
        
        # First try to get from surplus heats
        for surplus_heat in surplus_heats:
            if needed <= 0:
                break
                
            available = heat_timing_workers[surplus_heat]
            # Take timing workers who aren't already assigned
            for worker in available:
                if needed <= 0:
                    break
                    
                # Check if this worker is already relocated
                if any(r['participant'].id == worker.id for r in relocations):
                    continue
                    
                # Create relocation
                relocations.append({
                    'participant': worker,
                    'from_heat': surplus_heat + 1,  # 1-indexed for display
                    'to_heat': deficit_heat + 1,
                    'name': worker.name,
                    'from_category': worker.category_string
                })
                
                needed -= 1
                timing_deficit[deficit_heat] -= 1
                timing_deficit[surplus_heat] += 1
                
        # If still need more, try any heat with timing workers
        if needed > 0:
            for source_heat in range(number_of_heats):
                if source_heat == deficit_heat or needed <= 0:
                    continue
                    
                available = heat_timing_workers[source_heat]
                # Only take if source heat will still have at least 1 timing worker
                if len(available) - len([r for r in relocations if r['from_heat'] == source_heat + 1]) > 1:
                    for worker in available:
                        if needed <= 0:
                            break
                            
                        # Check if this worker is already relocated
                        if any(r['participant'].id == worker.id for r in relocations):
                            continue
                            
                        relocations.append({
                            'participant': worker,
                            'from_heat': source_heat + 1,
                            'to_heat': deficit_heat + 1,
                            'name': worker.name,
                            'from_category': worker.category_string
                        })
                        
                        needed -= 1
    
    logger.info(f"Found {len(relocations)} timing relocations")
    return relocations


def apply_timing_relocations(event: Any, relocations: List[Dict[str, Any]]) -> None:
    """
    Apply timing relocations to make heat assignments valid.
    
    This modifies the heat participants to reflect where timing workers
    will actually work during their timing assignment.
    """
    # For now, we just note the relocations - actual implementation would
    # modify participant assignments or track them separately
    for relocation in relocations:
        logger.info(f"Timing relocation: {relocation['name']} from Heat {relocation['from_heat']} to Heat {relocation['to_heat']}")