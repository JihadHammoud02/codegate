#!/usr/bin/env python3
"""
CodeGate CLI - Command-line interface for running contract evaluations.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from codegate.contract.parser import ContractParser
from codegate.engine.runner import EvaluationRunner


def main():
    """Main entry point for the CodeGate CLI."""
    parser = argparse.ArgumentParser(
        description="CodeGate - Contract-driven evaluator for Python code"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run contract evaluation")
    run_parser.add_argument(
        "contract",
        type=str,
        help="Path to the contract YAML file"
    )
    run_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="codegate-results.json",
        help="Output file for results (default: codegate-results.json)"
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "version":
        from codegate import __version__
        print(f"CodeGate version {__version__}")
        return 0
    
    if args.command == "run":
        return run_contract(args.contract, args.output, args.verbose)
    
    return 1


def run_contract(contract_path: str, output_path: str, verbose: bool = False) -> int:
    """
    Run contract evaluation.
    
    Args:
        contract_path: Path to the contract YAML file
        output_path: Path to save evaluation results
        verbose: Enable verbose output
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse contract
        if verbose:
            print(f"Loading contract from: {contract_path}")
        
        contract_file = Path(contract_path)
        if not contract_file.exists():
            print(f"Error: Contract file not found: {contract_path}", file=sys.stderr)
            return 1
        
        parser = ContractParser()
        contract = parser.parse(contract_file)
        
        if verbose:
            print(f"Contract loaded successfully")
            print(f"Project: {contract.get('project', {}).get('name', 'Unknown')}")
        
        # Run evaluation
        runner = EvaluationRunner(verbose=verbose)
        results = runner.run(contract)
        
        # Save results
        import json
        output_file = Path(output_path)
        output_file.write_text(json.dumps(results, indent=2))
        
        if verbose:
            print(f"Results saved to: {output_path}")
        
        # Print summary
        passed = results.get("summary", {}).get("passed", 0)
        failed = results.get("summary", {}).get("failed", 0)
        total = passed + failed
        
        print(f"\nEvaluation Summary:")
        print(f"  Total rules: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Success rate: {(passed/total*100) if total > 0 else 0:.1f}%")
        
        # Return non-zero if any checks failed
        return 0 if failed == 0 else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
