# Autologic

         ______
        /|_||_\`.__
       (   _    _ _\
       =`-(_)--(_)-'

A Python program that takes an autocross event roster and generates fair heat + worker assignments.
Updates by Steve Dock

It assigns `Categories` (car classes) to `Heats`, and `Participants` to `Roles` (specialized work assignments) while ensuring:
- All cars in the same class run in the same heat
- Heat cycle times are fair (differ by no more than 1.5 minutes)
- All required worker roles are filled in each heat
- Participants with multiple qualifications are optimally assigned

The algorithm uses intelligent category grouping, timing fairness constraints, and role optimization to create balanced heat assignments.

## Installation

### Option 1: Download Pre-built Release (Windows)
1. Download `autologic.exe` from the latest release on the [releases page](https://github.com/joshuavictorchen/autologic/releases/).
2. Open a terminal window and execute `.\path\to\autologic.exe --csv .\path\to\file.csv`

### Option 2: Run from Source (All Platforms)
1. Ensure Python 3.7+ is installed
2. Clone the repository
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the program:
   ```bash
   python source/autologic.py --csv path/to/file.csv
   ```

## Key Features

- **Timing Fairness**: Optimizes heat assignments to minimize cycle time variance for fair driver wait times
- **Smart Assignment**: Uses role scarcity analysis to optimally assign multi-qualified participants
- **Heat Comparison**: Automatic comparison tool runs both 3 and 4 heat configurations side-by-side
- **Best-Effort Mode**: Provides workable solutions even when constraints can't be met, with clear documentation of violations
- **Timing Flexibility**: Optional mode allows timing workers to work in different heats than they race (useful for 4-heat configurations)
- **Complete Output**: Each run produces full heat assignments and worker lists for evaluation
- **Visual Feedback**: Shows heat cycle times and fairness status in the output

## Usage

### Quick Start
```bash
# Basic usage - automatically selects optimal heat count
python source/autologic.py --csv path/to/file.csv

# Compare 3 vs 4 heats automatically
python source/compare_heats.py --csv path/to/file.csv
```

### Advanced Options
```bash
# Run specific heat configurations
python source/autologic.py --csv path/to/file.csv --heats 3
python source/autologic.py --csv path/to/file.csv --heats 4

# For 4 heats with limited timing workers, allow timing flexibility
python source/autologic.py --csv path/to/file.csv --heats 4 --allow-timing-flexibility

# Get best-effort solution with documented constraint violations
python source/autologic.py --csv path/to/file.csv --heats 4 --best-effort

# Disable timing optimization
python source/autologic.py --csv path/to/file.csv --no-enforce-timing-fairness

# Show detailed progress
python source/autologic.py --csv path/to/file.csv --verbose

# See timing analysis only
python source/autologic.py --csv path/to/file.csv --timing-only
```

Run `python source/autologic.py --help` for all options.

### Input Format

See [sample.csv](./tests/sample.csv) for the required CSV format:
- `name`: Participant name
- `category`: Car class (single letter)
- `novice`: Whether the participant is a novice (any non-empty value = true)
- `instructor`, `timing`, `grid`, `start`, `captain`, `special`: Worker qualifications

The `special` role is for VPs, worker coordinators, gate workers, etc. who should not be assigned to another role.

### Configuration

Role minimum requirements per heat are defined in [utils.py](./source/utils.py):
- **Instructors**: `max(3, novices/3)` - at least 1 instructor per 3 novices
- **Timing**: 2 workers minimum
- **Grid**: 2 workers minimum  
- **Start**: 1 worker minimum
- **Captains**: Equal to number of corner stations (default: 5)

## Heat Comparison Tool

The comparison tool (`compare_heats.py`) automatically runs both 3 and 4 heat configurations and presents a comprehensive comparison:

```bash
python source/compare_heats.py --csv path/to/file.csv

# Save output files for both configurations
python source/compare_heats.py --csv path/to/file.csv --save-outputs

# Show full output from both runs
python source/compare_heats.py --csv path/to/file.csv --verbose
```

The tool will:
1. Run 3-heat configuration
2. Run 4-heat configuration (with timing flexibility if needed)
3. If 4-heats fails, automatically try best-effort mode
4. Present a side-by-side comparison with recommendations

## Best-Effort Mode

When the algorithm can't find a solution that meets all constraints, use `--best-effort` to get a workable solution with documented issues:

```bash
python source/autologic.py --csv path/to/file.csv --heats 4 --best-effort
```

This mode:
- **Always produces a solution** - assigns as many qualified workers as possible
- **Documents all violations** - clearly shows which roles are short-staffed
- **Provides specific suggestions** - recommends workarounds like timing flexibility
- **Helps coordinators make decisions** - shows exactly what adjustments are needed

Example output shows violations with severity indicators:
- 🔴 Critical issues (timing, start positions)
- 🟡 Moderate issues (grid, instructor shortages)

Coordinators can use this information along with their knowledge of participants to:
- Recruit additional qualified workers
- Cross-train participants for critical roles
- Implement creative solutions (like timing workers working multiple heats)
- Make informed risk assessments

## Timing Flexibility

For events with limited timing workers (especially 4-heat configurations), the `--allow-timing-flexibility` flag enables timing workers to work in different heats than they race:

```bash
python source/autologic.py --csv path/to/file.csv --heats 4 --allow-timing-flexibility
```

This is particularly useful when you have exactly the minimum number of timing workers needed (e.g., 9 timing workers for 4 heats requiring 8 total).

## Sample Output

### Standard Run
```bash
$ python source/autologic.py --csv tests/sample.csv

         ______
        /|_||_\`.__
       (   _    _ _\
       =`-(_)--(_)-'
        

  Loaded 100 participants in 20 categories

  Heat Timing Analysis
  ===================
  Total participants: 100

  3 Heats (assuming equal distribution):
    - Average heat size: 33 drivers
    - Heat cycle time: 25.0 minutes

  4 Heats (assuming equal distribution):
    - Average heat size: 25 drivers
    - Heat cycle time: 18.8 minutes

  [... continues with heat assignments ...]
```

### Comparison Tool Output
```bash
$ python source/compare_heats.py --csv tests/sample.csv

🏁 AutoLogic Heat Comparison Tool
========================================
Analyzing: tests/sample.csv

→ Running 3 heat configuration...
→ Running 4 heat configuration...
→ Retrying 4 heats with timing flexibility...

======================================================================
HEAT CONFIGURATION COMPARISON
======================================================================

SUMMARY
----------------------------------------
                           3 HEATS              4 HEATS       
------------------------------------------------------------
Status                    ✓ SUCCESS            ✓ SUCCESS      
Heat Sizes                33, 33, 34          24, 25, 25, 26  
Cycle Time Range        24.8-25.5 min        18.0-19.5 min    
Timing Variance            0.8 min              1.5 min       
Timing Fairness             ✓ FAIR              ✓ FAIR       
Timing Flexibility        Not needed        Yes (2 workers)   
------------------------------------------------------------

[... continues with detailed analysis and recommendations ...]
```

## Output Files

Three output files are generated for each run:
1. `<filename>.heats.txt` - Participants listed by heat
2. `<filename>.heats_by_class.txt` - Participants organized by heat and car class
3. `<filename>.workers.txt` - Worker assignments by heat and role

When using the comparison tool with `--save-outputs`, files are saved as:
- `<filename>_3heats.*.txt`
- `<filename>_4heats.*.txt`

## Troubleshooting

### "Worker assignment failed"
- Try using `--best-effort` flag to see what constraints can't be met
- Consider using `--allow-timing-flexibility` for 4-heat configurations
- Check if you have enough qualified workers for the number of heats

### "Could not find valid heat assignment"
- Try adjusting `--heat-size-parity` (higher values allow more variation)
- Use fewer heats or ensure you have enough participants
- Run with `--verbose` to see detailed constraint information

### 4 Heats Not Working
- 4-heat configurations often require timing flexibility due to limited timing workers
- Use the comparison tool to see if 4 heats is feasible for your event
- Consider the best-effort mode to understand what adjustments would be needed

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)