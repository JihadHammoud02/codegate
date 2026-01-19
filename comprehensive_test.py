#!/usr/bin/env python3
"""
Comprehensive test of codegate functionality.
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def run_test(name, command, expected_exit_code=0):
    """Run a test case."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == expected_exit_code:
        print(f"✓ PASS - Exit code {result.returncode} matches expected {expected_exit_code}")
        return True
    else:
        print(f"✗ FAIL - Exit code {result.returncode}, expected {expected_exit_code}")
        return False


def verify_artifacts(rule_name):
    """Verify artifacts were created for a rule."""
    result_file = Path(f".artifacts/{rule_name}/result.json")
    output_file = Path(f".artifacts/{rule_name}/output.txt")
    
    if not result_file.exists():
        print(f"✗ Missing result.json for {rule_name}")
        return False
    
    if not output_file.exists():
        print(f"✗ Missing output.txt for {rule_name}")
        return False
    
    # Verify JSON is valid
    try:
        with open(result_file) as f:
            data = json.load(f)
            if 'status' not in data:
                print(f"✗ result.json missing 'status' field for {rule_name}")
                return False
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON in result.json for {rule_name}")
        return False
    
    print(f"✓ Artifacts verified for {rule_name}")
    return True


def main():
    """Run all tests."""
    print("CODEGATE COMPREHENSIVE TESTS")
    print("="*60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Help command
    tests_total += 1
    if run_test("CLI Help", "codegate --help", 0):
        tests_passed += 1
    
    # Test 2: Run help
    tests_total += 1
    if run_test("Run Command Help", "codegate run --help", 0):
        tests_passed += 1
    
    # Test 3: Successful contract
    tests_total += 1
    if os.path.exists(".artifacts"):
        subprocess.run("rm -rf .artifacts", shell=True)
    
    if run_test("Successful Contract Execution", "codegate run example_contract.yaml", 0):
        tests_passed += 1
        
        # Verify artifacts
        for rule in ['build_import', 'unit_tests', 'security_sast', 'security_deps', 'policy', 'quality']:
            tests_total += 1
            if verify_artifacts(rule):
                tests_passed += 1
    
    # Test 4: Failing contract
    tests_total += 1
    if os.path.exists(".artifacts"):
        subprocess.run("rm -rf .artifacts", shell=True)
    
    if run_test("Failing Contract Execution", "codegate run failing_contract.yaml", 1):
        tests_passed += 1
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
