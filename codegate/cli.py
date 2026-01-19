"""
CLI interface for codegate.
"""

import click
import sys
from pathlib import Path

from .contract import load_contract
from .executor import execute_contract


@click.group()
def cli():
    """Codegate - Contract-driven evaluator for AI-generated code."""
    pass


@cli.command()
@click.argument('contract_file', type=click.Path(exists=True))
def run(contract_file):
    """Load and execute a YAML contract to evaluate code.
    
    Args:
        contract_file: Path to the YAML contract file
    """
    try:
        # Load the contract
        contract = load_contract(contract_file)
        
        # Execute the contract
        results = execute_contract(contract, Path(contract_file).parent)
        
        # Print summary
        click.echo("\n" + "="*60)
        click.echo("CODEGATE EVALUATION RESULTS")
        click.echo("="*60 + "\n")
        
        overall_status = "PASS"
        for rule_name, result in results.items():
            status = result['status']
            status_color = {
                'PASS': 'green',
                'FAIL': 'red',
                'ERROR': 'yellow'
            }.get(status, 'white')
            
            click.echo(f"{rule_name}: ", nl=False)
            click.secho(status, fg=status_color, bold=True)
            
            if status != 'PASS':
                overall_status = status
                if 'message' in result:
                    click.echo(f"  → {result['message']}")
        
        click.echo("\n" + "="*60)
        click.echo(f"Overall Status: ", nl=False)
        click.secho(overall_status, 
                   fg='green' if overall_status == 'PASS' else 'red',
                   bold=True)
        click.echo("="*60)
        
        # Exit with appropriate code
        sys.exit(0 if overall_status == 'PASS' else 1)
        
    except Exception as e:
        click.secho(f"Error: {str(e)}", fg='red', err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
