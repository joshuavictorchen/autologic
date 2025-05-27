#!/usr/bin/env python3
"""
Heat comparison orchestrator for AutoLogic.

Runs both 3 and 4 heat configurations and presents a side-by-side comparison
to help users choose the best configuration for their event.
"""

import subprocess
import sys
import os
import re
from typing import Dict, Any
import click


def run_autologic(csv_file: str, heats: int, allow_timing_flexibility: bool = False, best_effort: bool = False) -> Dict[str, Any]:
    """
    Run autologic with specified parameters and capture the output.
    
    Returns:
        dict: Parsed results including success status, timing info, and heat details
    """
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "autologic.py"),
        "--csv", csv_file,
        "--heats", str(heats)
    ]
    
    if allow_timing_flexibility:
        cmd.append("--allow-timing-flexibility")
    
    if best_effort:
        cmd.append("--best-effort")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = result.stdout
        
        # Parse the output
        parsed = {
            "success": result.returncode == 0,
            "heats": heats,
            "output": output,
            "heat_sizes": [],
            "cycle_times": [],
            "timing_variance": None,
            "is_fair": False,
            "uses_timing_flexibility": False,
            "timing_relocations": 0,
            "warnings": []
        }
        
        # Extract heat information
        heat_pattern = r"Heat \d+:.*?Participants: (\d+).*?Cycle time: ([\d.]+) minutes"
        for match in re.finditer(heat_pattern, output, re.DOTALL):
            parsed["heat_sizes"].append(int(match.group(1)))
            parsed["cycle_times"].append(float(match.group(2)))
        
        # Extract timing fairness
        variance_match = re.search(r"Variance: ([\d.]+) minutes", output)
        if variance_match:
            parsed["timing_variance"] = float(variance_match.group(1))
            
        # Check if fair
        if "Heat cycle times are FAIR" in output:
            parsed["is_fair"] = True
        
        # Check for timing flexibility
        if "timing relocations" in output.lower():
            parsed["uses_timing_flexibility"] = True
            reloc_match = re.search(r"Found (\d+) timing relocations", output)
            if reloc_match:
                parsed["timing_relocations"] = int(reloc_match.group(1))
        
        # Extract warnings
        warning_pattern = r"WARNING: (.+)"
        for match in re.finditer(warning_pattern, output):
            parsed["warnings"].append(match.group(1))
        
        # Check for best-effort solution
        if "best-effort solution" in output:
            parsed["best_effort"] = True
            
            # Extract violations
            parsed["violations"] = []
            violation_pattern = r"[🔴🟡]\s+(.+)"
            for match in re.finditer(violation_pattern, output):
                parsed["violations"].append(match.group(1))
            
        return parsed
        
    except Exception as e:
        return {
            "success": False,
            "heats": heats,
            "error": str(e),
            "output": ""
        }


def format_comparison(results_3: Dict[str, Any], results_4: Dict[str, Any]) -> str:
    """Format the comparison results in a user-friendly way."""
    output = []
    output.append("\n" + "="*70)
    output.append("HEAT CONFIGURATION COMPARISON")
    output.append("="*70)
    
    # Summary table
    output.append("\nSUMMARY")
    output.append("-"*40)
    output.append(f"{'':20} {'3 HEATS':^20} {'4 HEATS':^20}")
    output.append("-"*60)
    
    # Success status
    status_3 = "✓ SUCCESS" if results_3["success"] else "✗ FAILED"
    status_4 = "✓ SUCCESS" if results_4["success"] else "✗ FAILED"
    output.append(f"{'Status':20} {status_3:^20} {status_4:^20}")
    
    # Heat sizes
    if results_3["heat_sizes"] and results_4["heat_sizes"]:
        sizes_3 = ", ".join(map(str, results_3["heat_sizes"]))
        sizes_4 = ", ".join(map(str, results_4["heat_sizes"]))
        output.append(f"{'Heat Sizes':20} {sizes_3:^20} {sizes_4:^20}")
    
    # Cycle times
    if results_3["cycle_times"] and results_4["cycle_times"]:
        min_3, max_3 = min(results_3["cycle_times"]), max(results_3["cycle_times"])
        min_4, max_4 = min(results_4["cycle_times"]), max(results_4["cycle_times"])
        output.append(f"{'Cycle Time Range':20} {f'{min_3:.1f}-{max_3:.1f} min':^20} {f'{min_4:.1f}-{max_4:.1f} min':^20}")
    
    # Timing variance
    if results_3["timing_variance"] is not None and results_4["timing_variance"] is not None:
        var_3 = f"{results_3['timing_variance']:.1f} min"
        var_4 = f"{results_4['timing_variance']:.1f} min"
        output.append(f"{'Timing Variance':20} {var_3:^20} {var_4:^20}")
    
    # Fairness
    fair_3 = "✓ FAIR" if results_3["is_fair"] else "✗ UNFAIR"
    fair_4 = "✓ FAIR" if results_4["is_fair"] else "✗ UNFAIR"
    output.append(f"{'Timing Fairness':20} {fair_3:^20} {fair_4:^20}")
    
    # Timing flexibility
    if results_4["uses_timing_flexibility"]:
        flex_3 = "Not needed"
        flex_4 = f"Yes ({results_4['timing_relocations']} workers)"
        output.append(f"{'Timing Flexibility':20} {flex_3:^20} {flex_4:^20}")
    
    output.append("-"*60)
    
    # Detailed analysis
    output.append("\nDETAILED ANALYSIS")
    output.append("-"*40)
    
    # 3 Heats analysis
    output.append("\n3 HEATS:")
    if results_3["success"]:
        output.append("  ✓ Successfully assigned all participants")
        if results_3["is_fair"]:
            output.append(f"  ✓ Fair timing distribution (variance: {results_3['timing_variance']:.1f} min)")
        else:
            output.append(f"  ✗ Unfair timing distribution (variance: {results_3['timing_variance']:.1f} min)")
        
        avg_cycle_3 = sum(results_3["cycle_times"]) / len(results_3["cycle_times"])
        output.append(f"  • Average cycle time: {avg_cycle_3:.1f} minutes")
        output.append(f"  • Heat sizes: {results_3['heat_sizes']}")
        
        if results_3["warnings"]:
            output.append("  • Warnings:")
            for warning in results_3["warnings"]:
                output.append(f"    - {warning}")
    else:
        output.append("  ✗ Failed to create valid heat assignment")
    
    # 4 Heats analysis
    output.append("\n4 HEATS:")
    if results_4["success"]:
        if results_4.get("best_effort", False):
            output.append("  ⚠️  BEST-EFFORT SOLUTION (with constraint violations)")
        else:
            output.append("  ✓ Successfully assigned all participants")
        
        if results_4["uses_timing_flexibility"]:
            output.append(f"  • Uses timing flexibility ({results_4['timing_relocations']} workers relocated)")
        if results_4["is_fair"]:
            output.append(f"  ✓ Fair timing distribution (variance: {results_4['timing_variance']:.1f} min)")
        else:
            output.append(f"  ✗ Unfair timing distribution (variance: {results_4['timing_variance']:.1f} min)")
        
        avg_cycle_4 = sum(results_4["cycle_times"]) / len(results_4["cycle_times"])
        output.append(f"  • Average cycle time: {avg_cycle_4:.1f} minutes")
        output.append(f"  • Heat sizes: {results_4['heat_sizes']}")
        
        if results_4["warnings"]:
            output.append("  • Warnings:")
            for warning in results_4["warnings"]:
                output.append(f"    - {warning}")
        
        if results_4.get("violations", []):
            output.append("  • Constraint Violations:")
            for violation in results_4["violations"][:5]:  # Show first 5
                output.append(f"    - {violation}")
            if len(results_4["violations"]) > 5:
                output.append(f"    ... and {len(results_4['violations']) - 5} more")
    else:
        output.append("  ✗ Failed to create valid heat assignment")
        
        # Check for specific error patterns
        if "timing (1/2)" in results_4.get("output", "") or "timing (0/2)" in results_4.get("output", ""):
            output.append("  • Issue: Insufficient timing workers distributed across heats")
            output.append("  • With only 9 timing workers for 8 slots, distribution is critical")
        
        if results_4.get("uses_timing_flexibility", False):
            output.append("  • Timing flexibility was attempted but still failed")
            output.append("  • The event may not have enough qualified workers for 4 heats")
        else:
            output.append("  • Consider using --allow-timing-flexibility flag")
    
    # Recommendation
    output.append("\nRECOMMENDATION")
    output.append("-"*40)
    
    if results_3["success"] and results_4["success"]:
        # Both succeeded, compare them
        avg_3 = sum(results_3["cycle_times"]) / len(results_3["cycle_times"]) if results_3["cycle_times"] else 0
        avg_4 = sum(results_4["cycle_times"]) / len(results_4["cycle_times"]) if results_4["cycle_times"] else 0
        
        if avg_4 < avg_3 * 0.8:  # 4 heats is significantly faster
            output.append("→ Recommend 4 HEATS for significantly shorter cycle times")
            output.append(f"  ({avg_4:.1f} min vs {avg_3:.1f} min average cycle time)")
        elif results_4["uses_timing_flexibility"]:
            output.append("→ Recommend 3 HEATS for simpler logistics")
            output.append("  (4 heats requires timing workers to work in different heats)")
        elif results_3["is_fair"] and not results_4["is_fair"]:
            output.append("→ Recommend 3 HEATS for fairer timing distribution")
        else:
            output.append("→ Both configurations are viable")
            output.append("  • Choose 3 heats for simpler event management")
            output.append("  • Choose 4 heats for shorter cycle times")
    elif results_3["success"] and not results_4["success"]:
        output.append("→ Recommend 3 HEATS (4 heats configuration failed)")
    elif not results_3["success"] and results_4["success"]:
        output.append("→ Recommend 4 HEATS (3 heats configuration failed)")
    else:
        output.append("→ Neither configuration succeeded - check your input data")
    
    output.append("\n" + "="*70)
    
    return "\n".join(output)


@click.command()
@click.option(
    "--csv",
    "csv_file",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to CSV file containing participant data.",
)
@click.option(
    "--save-outputs",
    is_flag=True,
    help="Save the output files for both configurations.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show full output from both runs.",
)
def main(csv_file: str, save_outputs: bool, verbose: bool) -> None:
    """
    Compare 3 and 4 heat configurations for an autocross event.
    
    This tool runs autologic with both 3 and 4 heats and presents
    a side-by-side comparison to help you choose the best configuration.
    """
    print("\n🏁 AutoLogic Heat Comparison Tool")
    print("="*40)
    print(f"Analyzing: {csv_file}")
    
    # Run 3 heats
    print("\n→ Running 3 heat configuration...")
    results_3 = run_autologic(csv_file, 3)
    
    # Run 4 heats (first without timing flexibility)
    print("→ Running 4 heat configuration...")
    results_4 = run_autologic(csv_file, 4)
    
    # If 4 heats failed, try with timing flexibility
    if not results_4["success"]:
        print("→ Retrying 4 heats with timing flexibility...")
        results_4_flex = run_autologic(csv_file, 4, allow_timing_flexibility=True)
        if results_4_flex["success"]:
            results_4 = results_4_flex
        else:
            # Try best-effort mode
            print("→ Generating best-effort solution for 4 heats...")
            results_4_best = run_autologic(csv_file, 4, best_effort=True)
            if results_4_best["success"]:
                results_4 = results_4_best
                results_4["best_effort"] = True
    
    # Display comparison
    comparison = format_comparison(results_3, results_4)
    print(comparison)
    
    # Show full outputs if requested
    if verbose:
        print("\n\nFULL OUTPUT - 3 HEATS")
        print("="*70)
        print(results_3["output"])
        
        print("\n\nFULL OUTPUT - 4 HEATS")
        print("="*70)
        print(results_4["output"])
    
    # Save outputs if requested
    if save_outputs:
        base_name = os.path.splitext(csv_file)[0]
        
        # Rename output files to include heat count
        if results_3["success"]:
            for ext in [".heats.txt", ".heats_by_class.txt", ".workers.txt"]:
                src = f"{csv_file}{ext}"
                dst = f"{base_name}_3heats{ext}"
                if os.path.exists(src):
                    os.rename(src, dst)
                    print(f"  Saved: {dst}")
        
        # Run 4 heats again to generate files (if successful)
        if results_4["success"]:
            # Re-run to generate files
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "autologic.py"),
                "--csv", csv_file,
                "--heats", "4"
            ]
            if results_4["uses_timing_flexibility"]:
                cmd.append("--allow-timing-flexibility")
            
            subprocess.run(cmd, capture_output=True)
            
            # Rename files
            for ext in [".heats.txt", ".heats_by_class.txt", ".workers.txt"]:
                src = f"{csv_file}{ext}"
                dst = f"{base_name}_4heats{ext}"
                if os.path.exists(src):
                    os.rename(src, dst)
                    print(f"  Saved: {dst}")


if __name__ == "__main__":
    main()