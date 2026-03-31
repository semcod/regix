#!/usr/bin/env python3
"""
Regression detection script for regix
Checks for regressions in code metrics and quality gates
"""

import json
import sys
import subprocess
from pathlib import Path

def run_command(cmd):
    """Run a command and return its output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def load_json_file(filepath):
    """Load JSON file if it exists"""
    if Path(filepath).exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def check_regression():
    """Main regression check function"""
    # Load current metrics
    current_metrics = load_json_file('.pyqual/metrics.json')
    baseline_metrics = load_json_file('.pyqual/baseline.json')
    
    regression_detected = False
    regression_report = {
        "regression": False,
        "metrics": {},
        "details": []
    }
    
    if baseline_metrics and current_metrics:
        # Compare key metrics
        metrics_to_check = ['cc_max', 'coverage_min', 'vallm_pass_min']
        
        for metric in metrics_to_check:
            if metric in baseline_metrics and metric in current_metrics:
                baseline_val = baseline_metrics[metric]
                current_val = current_metrics[metric]
                
                # Check for regression (different logic for different metrics)
                if 'cc_max' in metric:
                    # Lower is better for complexity
                    if current_val > baseline_val:
                        regression_detected = True
                        regression_report["metrics"][metric] = {
                            "baseline": baseline_val,
                            "current": current_val,
                            "regression": True
                        }
                        regression_report["details"].append(
                            f"Cyclomatic complexity increased from {baseline_val} to {current_val}"
                        )
                elif 'coverage_min' in metric or 'vallm_pass_min' in metric:
                    # Higher is better for coverage and pass rate
                    if current_val < baseline_val:
                        regression_detected = True
                        regression_report["metrics"][metric] = {
                            "baseline": baseline_val,
                            "current": current_val,
                            "regression": True
                        }
                        regression_report["details"].append(
                            f"{metric} decreased from {baseline_val}% to {current_val}%"
                        )
    
    # Check for errors from vallm
    errors = load_json_file('.pyqual/errors.json')
    if errors:
        regression_detected = True
        regression_report["errors"] = errors
        regression_report["details"].append(f"Found {len(errors)} validation errors")
    
    regression_report["regression"] = regression_detected
    
    # Save regression report
    with open('.pyqual/regression_report.json', 'w') as f:
        json.dump(regression_report, f, indent=2)
    
    if regression_detected:
        print("❌ Regression detected!")
        for detail in regression_report["details"]:
            print(f"  - {detail}")
        sys.exit(1)
    else:
        print("✅ No regression detected")
        sys.exit(0)

if __name__ == "__main__":
    check_regression()
