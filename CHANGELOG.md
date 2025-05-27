# CHANGELOG

## [Unreleased] - 2025-01-27

### Added
- **Multi-Stage Optimization System**
  - New `simple_solver.py`: Smart heat assignment with timing fairness optimization
  - New `role_optimizer.py`: Intelligent role assignment based on scarcity analysis
  - New `relaxed_solver.py`: Best-effort mode for workable solutions when constraints can't be perfectly met
  - New `timing_flexibility.py`: Allows timing workers to work in different heats than they race
  - New `compare_heats.py`: Automated comparison tool for 3 vs 4 heat configurations

- **Command Line Options**
  - `--timing-only`: Detailed timing analysis without full assignment
  - `--enforce-timing-fairness/--no-enforce-timing-fairness`: Control timing optimization
  - `--allow-timing-flexibility`: Enable timing workers to work in different heats
  - `--best-effort`: Provide solutions even when constraints can't be met
  - `--save-outputs` (compare_heats.py): Save output files for both configurations

- **Visual Improvements**
  - ASCII art at program start
  - Heat summaries with cycle times
  - Fairness indicators (✓/✗) for timing variance
  - Color-coded output for better readability

- **Comprehensive Test Suite**
  - `test_autologic.py`: Full test coverage for all major functionality
  - Tests for event loading, role optimization, constraint validation
  - Tests for timing flexibility and best-effort modes

### Changed
- **Heat Assignment Algorithm**
  - Replaced random assignment with smart timing-optimized approach
  - Categories now assigned to minimize cycle time variance (< 1.5 minutes)
  - Continues searching through iterations to find best valid solution
  - Default `heat-size-parity` increased from 25 to 50 for better balance

- **Role Assignment**
  - Now uses Hungarian algorithm variant for optimal assignment
  - Prioritizes scarce roles when assigning multi-qualified workers
  - Pre-validates feasibility before attempting assignment

- **Output Format**
  - Clearer, more informative output with visual indicators
  - Shows cycle times and timing fairness for each heat
  - Better error messages with specific remediation suggestions

### Fixed
- **Code Quality Issues**
  - Removed duplicate `heat_assignment` attribute in Category class
  - Replaced deprecated `parse_bool()` with Python's built-in `bool()`
  - Removed unused sorting functions in utils.py
  - Cleaned up unused imports

### Technical Details
- **Architecture Improvements**
  - Modular design with separate modules for each optimization stage
  - Clear separation of concerns between heat assignment and role assignment
  - Extensible framework for future enhancements

- **Algorithm Enhancements**
  - Categories assigned as groups to maintain class integrity
  - Smart role assignment using scarcity analysis
  - Timing optimization finds best solution across many iterations
  - Graceful degradation with best-effort mode

### Dependencies
- Added `requirements-minimal.txt` for runtime-only dependencies
- Updated `requirements.txt` with development dependencies