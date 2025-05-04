#!/usr/bin/env python
"""
Test Runner Script for darktheme-auth-fastapi-server

This script runs all tests or specific test categories based on command-line arguments.
"""

import argparse
import os
import sys
import subprocess
import time
from datetime import datetime


def setup_environment():
    """Set up the environment for testing."""
    print("Setting up test environment...")
    os.environ["PYTHONPATH"] = os.getcwd()
    os.environ["TESTING"] = "1"


def run_tests(test_type, verbose=False, junit=False, report_dir=None):
    """Run the specified tests."""
    if report_dir and not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    # Separate run types for special cases (benchmark, stability)
    if test_type == "unit":
        return run_standard_tests("tests/unit/", verbose, junit, report_dir)
    elif test_type == "api":
        return run_standard_tests("tests/api/", verbose, junit, report_dir)
    elif test_type == "benchmark":
        return run_benchmark_tests(verbose, junit, report_dir)
    elif test_type == "stability":
        return run_stability_tests(verbose, junit, report_dir)
    elif test_type == "all":
        # Run unit and API tests first
        api_result = run_standard_tests("tests/api/", verbose, junit, report_dir)
        unit_result = run_standard_tests("tests/unit/", verbose, junit, report_dir)
        
        # Only run benchmark and stability if the basic tests pass
        if api_result == 0 and unit_result == 0:
            print("\n=== Basic tests passed. Running benchmark tests... ===\n")
            benchmark_result = run_benchmark_tests(verbose, junit, report_dir)
            
            print("\n=== Running stability tests... ===\n")
            stability_result = run_stability_tests(verbose, junit, report_dir)
            
            # Return the worst result
            return max(api_result, unit_result, benchmark_result, stability_result)
        else:
            print("\n=== Basic tests failed. Skipping benchmark and stability tests. ===\n")
            return max(api_result, unit_result)
    else:
        print(f"Unknown test type: {test_type}")
        return 1

def run_standard_tests(test_path, verbose=False, junit=False, report_dir=None):
    """Run standard tests with pytest."""
    cmd = ["pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add JUnit reports
    if junit and report_dir:
        cmd.extend(["--junitxml", f"{report_dir}/results_{test_path.replace('/', '_')}.xml"])
    
    # Add HTML reports
    if report_dir:
        report_file = f"{report_dir}/report_{test_path.replace('/', '_')}.html"
        cmd.extend(["--html", report_file, "--self-contained-html"])
    
    # Add test path
    cmd.append(test_path)
    
    # Show command
    print(f"Running command: {' '.join(cmd)}")
    
    # Run tests
    start_time = time.time()
    result = subprocess.run(cmd)
    end_time = time.time()
    
    # Show results
    print(f"\nTests completed in {end_time - start_time:.2f} seconds")
    print(f"Return code: {result.returncode}")
    
    return result.returncode

def run_benchmark_tests(verbose=False, junit=False, report_dir=None):
    """Run benchmark tests individually to avoid timeouts."""
    benchmark_tests = [
        "tests/benchmark/test_api_benchmark.py::TestApiBenchmark::test_ping_endpoint_benchmark",
        "tests/benchmark/test_api_benchmark.py::TestApiBenchmark::test_logs_count_benchmark",
        "tests/benchmark/test_api_benchmark.py::TestApiBenchmark::test_logs_access_benchmark",
        "tests/benchmark/test_api_benchmark.py::TestApiBenchmark::test_health_endpoint_benchmark"
    ]
    
    worst_result = 0
    for test in benchmark_tests:
        cmd = ["pytest"]
        
        # Add verbosity
        if verbose:
            cmd.append("-v")
        
        # Add test path
        cmd.append(test)
        
        # Show command
        print(f"\nRunning benchmark test: {' '.join(cmd)}")
        
        # Run test
        start_time = time.time()
        result = subprocess.run(cmd)
        end_time = time.time()
        
        # Show results
        print(f"Benchmark test completed in {end_time - start_time:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        # Track worst result
        worst_result = max(worst_result, result.returncode)
    
    return worst_result

def run_stability_tests(verbose=False, junit=False, report_dir=None):
    """Run stability tests individually to avoid timeouts."""
    stability_tests = [
        "tests/stability/test_api_stability.py::TestApiStability::test_ping_endpoint_stability",
        "tests/stability/test_api_stability.py::TestApiStability::test_logs_count_stability",
        "tests/stability/test_api_stability.py::TestApiStability::test_mixed_endpoints_stability"
    ]
    
    worst_result = 0
    for test in stability_tests:
        cmd = ["pytest"]
        
        # Add verbosity
        if verbose:
            cmd.append("-v")
        
        # Add test path
        cmd.append(test)
        
        # Show command
        print(f"\nRunning stability test: {' '.join(cmd)}")
        
        # Run test
        start_time = time.time()
        result = subprocess.run(cmd)
        end_time = time.time()
        
        # Show results
        print(f"Stability test completed in {end_time - start_time:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        # Track worst result
        worst_result = max(worst_result, result.returncode)
    
    return worst_result


def generate_summary(report_dir):
    """Generate a summary of all test results."""
    if not os.path.exists(report_dir):
        return
    
    summary_file = os.path.join(report_dir, "summary.txt")
    
    with open(summary_file, "w") as f:
        f.write(f"Test Summary - {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
        
        # Check for JUnit XML file
        junit_file = os.path.join(report_dir, "results.xml")
        if os.path.exists(junit_file):
            import xml.etree.ElementTree as ET
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            tests = int(root.attrib.get("tests", 0))
            failures = int(root.attrib.get("failures", 0))
            errors = int(root.attrib.get("errors", 0))
            skipped = int(root.attrib.get("skipped", 0))
            
            f.write(f"Total Tests: {tests}\n")
            f.write(f"Passed: {tests - failures - errors - skipped}\n")
            f.write(f"Failed: {failures}\n")
            f.write(f"Errors: {errors}\n")
            f.write(f"Skipped: {skipped}\n\n")
        
        # Check for benchmark and stability reports
        benchmark_dir = os.path.join("tests", "benchmark", "reports")
        stability_dir = os.path.join("tests", "stability", "reports")
        
        if os.path.exists(benchmark_dir):
            f.write("Benchmark Reports:\n")
            f.write("-" * 30 + "\n")
            for filename in os.listdir(benchmark_dir):
                if filename.endswith("_summary.json"):
                    f.write(f"- {filename}\n")
            f.write("\n")
        
        if os.path.exists(stability_dir):
            f.write("Stability Reports:\n")
            f.write("-" * 30 + "\n")
            for filename in os.listdir(stability_dir):
                if filename.endswith("_summary.json"):
                    f.write(f"- {filename}\n")
            f.write("\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run tests for darktheme-auth-fastapi-server")
    parser.add_argument(
        "test_type",
        choices=["unit", "api", "benchmark", "stability", "all"],
        default="all",
        nargs="?",
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--junit",
        action="store_true",
        help="Generate JUnit XML report"
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default="test_reports",
        help="Directory for test reports"
    )
    
    args = parser.parse_args()
    
    # Setup environment
    setup_environment()
    
    # Run tests
    return_code = run_tests(
        args.test_type,
        verbose=args.verbose,
        junit=args.junit,
        report_dir=args.report_dir
    )
    
    # Generate summary
    generate_summary(args.report_dir)
    
    return return_code


if __name__ == "__main__":
    sys.exit(main())