"""Event management for autocross heat assignment."""

import csv
import os
from typing import List
from collections import defaultdict

from Category import Category
from Group import Group
from Heat import Heat
from Participant import Participant


class Event(Group):
    """
    Represents the overall event, composed of participants, categories, and heats.
    
    Handles loading data from CSV, organizing participants into categories,
    and creating heats for the event.
    """

    def __init__(self):
        """Initialize an empty event."""
        super().__init__()
        self.participants = []
        self.categories = {}
        self.heats = []
        self.number_of_stations = 5  # Default value
        self._max_name_length = None

    @property
    def max_name_length(self) -> int:
        """Get the length of the longest participant name."""
        if self._max_name_length is None and self.participants:
            self._max_name_length = max(len(p.name) for p in self.participants)
        return self._max_name_length or 0

    def load_participants(self, csv_file: str) -> None:
        """
        Load participants from a CSV file with comprehensive validation.
        
        Args:
            csv_file: Path to the CSV file
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If the CSV format is invalid or data is malformed
        """
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
            
        if not csv_file.lower().endswith('.csv'):
            raise ValueError(f"File must be a CSV: {csv_file}")
            
        participants = []
        seen_name_category = set()  # Track name+category combinations
        
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # Validate required columns
                if reader.fieldnames is None:
                    raise ValueError("CSV file is empty or invalid")
                    
                required_columns = {'name', 'category', 'novice'}
                missing_columns = required_columns - set(reader.fieldnames)
                if missing_columns:
                    raise ValueError(f"CSV missing required columns: {missing_columns}")
                
                # Optional role columns
                role_columns = {'instructor', 'timing', 'grid', 'start', 'captain', 'special'}
                available_roles = role_columns & set(reader.fieldnames)
                
                # Read each row
                for row_num, row in enumerate(reader, start=2):
                    # Validate name
                    name = row.get('name', '').strip()
                    if not name:
                        raise ValueError(f"Row {row_num}: Empty name field")
                    
                    # Validate category
                    category = row.get('category', '').strip().lower()
                    if not category:
                        raise ValueError(f"Row {row_num}: Empty category for '{name}'")
                        
                    if not category.isalnum():
                        raise ValueError(f"Row {row_num}: Invalid category '{category}' for '{name}'")
                        
                    # Check for duplicate name+category combination
                    name_cat_key = (name, category)
                    if name_cat_key in seen_name_category:
                        raise ValueError(f"Row {row_num}: Duplicate entry for '{name}' in category '{category}'")
                    seen_name_category.add(name_cat_key)
                    
                    # Parse novice status
                    novice = bool(row.get('novice', ''))
                    
                    # Parse role attributes for kwargs
                    role_kwargs = {}
                    for role in available_roles:
                        role_kwargs[role] = bool(row.get(role, ''))
                    
                    # Create participant with ID and all roles
                    participant_id = len(participants)
                    participant = Participant(
                        event=self,
                        id=participant_id,
                        name=name,
                        category_string=category,
                        novice=novice,
                        **role_kwargs
                    )
                    
                    participants.append(participant)
                    
        except csv.Error as e:
            raise ValueError(f"CSV parsing error: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"File encoding error: {e}. Try saving as UTF-8.")
            
        if not participants:
            raise ValueError("No participants found in CSV file")
            
        # Store participants and organize into categories
        self.participants = participants
        self._organize_categories()
        
    def _organize_categories(self) -> None:
        """Organize participants into categories."""
        category_map = defaultdict(list)
        
        for participant in self.participants:
            category_map[participant.category_string].append(participant)
            
        self.categories = {}
        for cat_name, participants in category_map.items():
            category = Category(self, cat_name)
            for participant in participants:
                category.add_participant(participant)
            self.categories[cat_name] = category
            
    def create_heats(self, number_of_heats: int) -> None:
        """
        Create the specified number of heats and distribute categories.
        
        Args:
            number_of_heats: Number of heats to create
            
        Raises:
            ValueError: If heat creation fails
        """
        if number_of_heats < 1:
            raise ValueError("Number of heats must be at least 1")
            
        if not self.categories:
            raise ValueError("No categories available to assign to heats")
            
        # Create heats
        self.heats = []
        for i in range(number_of_heats):
            self.heats.append(Heat(self, i))
            
        # Build heat assignments from category assignments
        for category in self.categories.values():
            if category.heat is not None:
                if 0 <= category.heat < number_of_heats:
                    self.heats[category.heat].add_category(category)
                else:
                    raise ValueError(
                        f"Category {category.name} has invalid heat assignment: "
                        f"{category.heat}"
                    )
                    
    def validate_heat_assignments(self) -> List[str]:
        """
        Validate that all categories are assigned to heats.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for cat_name, category in self.categories.items():
            if category.heat is None:
                errors.append(f"Category {cat_name} not assigned to any heat")
                
        # Check that all heats have at least one category
        for i, heat in enumerate(self.heats):
            if not heat.categories:
                errors.append(f"Heat {i} has no categories assigned")
                
        return errors
        
    def export_heats_by_name(self, filename: str) -> None:
        """Export heat assignments sorted by participant name."""
        try:
            with open(filename, 'w') as f:
                for i, heat in enumerate(self.heats):
                    f.write(f"Heat {i + 1}\n")
                    f.write("=" * 30 + "\n")
                    
                    participants = sorted(heat.participants, key=lambda p: p.name)
                    for p in participants:
                        f.write(f"{p.name} ({p.category_string.upper()})\n")
                    f.write("\n")
        except IOError as e:
            raise IOError(f"Failed to write file {filename}: {e}")
            
    def export_heats_by_car_class(self, filename: str) -> None:
        """Export heat assignments sorted by car class."""
        try:
            with open(filename, 'w') as f:
                for i, heat in enumerate(self.heats):
                    f.write(f"Heat {i + 1}\n")
                    f.write("=" * 30 + "\n")
                    
                    # Group by category
                    by_category = defaultdict(list)
                    for p in heat.participants:
                        by_category[p.category_string].append(p)
                        
                    # Sort categories and participants
                    for cat in sorted(by_category.keys()):
                        f.write(f"\nClass {cat.upper()}:\n")
                        for p in sorted(by_category[cat], key=lambda x: x.name):
                            f.write(f"  {p.name}\n")
                    f.write("\n")
        except IOError as e:
            raise IOError(f"Failed to write file {filename}: {e}")
            
    def export_workers(self, filename: str) -> None:
        """Export worker assignments."""
        try:
            with open(filename, 'w') as f:
                for i, heat in enumerate(self.heats):
                    f.write(f"Heat {i + 1} Workers\n")
                    f.write("=" * 30 + "\n")
                    
                    # Group by assignment
                    by_role = defaultdict(list)
                    for p in heat.participants:
                        if p.assignment:
                            by_role[p.assignment].append(p)
                            
                    # Define role order
                    role_order = ['timing', 'instructor', 'grid', 'start', 'captain']
                    
                    # Print special roles first
                    for role in role_order:
                        if role in by_role:
                            f.write(f"\n{role.upper()}:\n")
                            for p in sorted(by_role[role], key=lambda x: x.name):
                                f.write(f"  {p.name}\n")
                                
                    # Print general workers
                    worker_roles = sorted([r for r in by_role if r.startswith('worker-')])
                    if worker_roles:
                        f.write(f"\nGENERAL WORKERS:\n")
                        for role in worker_roles:
                            station = role.split('-')[1]
                            f.write(f"  Station {station}:\n")
                            for p in sorted(by_role[role], key=lambda x: x.name):
                                f.write(f"    {p.name}\n")
                    
                    f.write("\n")
        except IOError as e:
            raise IOError(f"Failed to write file {filename}: {e}")