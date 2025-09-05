"""
Command-line interface for the UOFC Funding Transparency Report generator.

This module provides a rich CLI experience with colored output, progress
tracking, and comprehensive logging.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .analyzer import FundingAnalyzer
from .charts import generate_all_charts
from .config import Config, load_config
from .loader import DataLoader, print_column_mapping_table
from .slides import PresentationBuilder

console = Console()


def setup_logging(level: str = "INFO", use_rich: bool = True) -> None:
    """
    Configure logging with optional rich formatting.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        use_rich: Whether to use rich formatting
    """
    if use_rich:
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, rich_tracebacks=True)]
        )
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )


def print_header() -> None:
    """Print the application header."""
    header = Panel(
        "[bold blue]UOFC Funding Transparency Report Generator[/bold blue]\n"
        "[dim]Yale Undergraduate Organizations Funding Committee[/dim]",
        border_style="blue"
    )
    console.print(header)
    console.print()


def print_summary(
    round_number: int,
    num_organizations: int,
    total_requested: float,
    total_awarded: float,
    num_charts: int,
    output_path: Path
) -> None:
    """Print a summary of the generated report."""
    table = Table(title="Report Summary", show_header=False, border_style="green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Round Number", str(round_number))
    table.add_row("Organizations", str(num_organizations))
    table.add_row("Total Requested", f"${total_requested:,.2f}")
    table.add_row("Total Awarded", f"${total_awarded:,.2f}")
    table.add_row("Funding Ratio", f"{(total_awarded/total_requested*100):.1f}%" if total_requested > 0 else "N/A")
    table.add_row("Charts Generated", str(num_charts))
    table.add_row("Output File", str(output_path))
    
    console.print()
    console.print(table)


@click.command()
@click.argument("excel_file", type=click.Path(exists=True, path_type=Path))
@click.argument("round_number", type=int)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to custom configuration file"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for the PowerPoint file"
)
@click.option(
    "--charts-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory to save chart images"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.option(
    "--show-mapping",
    is_flag=True,
    help="Show column mapping table"
)
@click.option(
    "--skip-presentation",
    is_flag=True,
    help="Generate charts only, skip PowerPoint creation"
)
def main(
    excel_file: Path,
    round_number: int,
    config: Optional[Path],
    output: Optional[Path],
    charts_dir: Optional[Path],
    verbose: bool,
    show_mapping: bool,
    skip_presentation: bool
) -> None:
    """
    Generate a transparency report from funding data.
    
    EXCEL_FILE: Path to the Excel file containing funding data
    
    ROUND_NUMBER: The funding round number (e.g., 1, 2, 3)
    
    Example:
        uofc-report funding_data.xlsx 2
        uofc-report funding_data.xlsx 1 --output report.pptx --verbose
    """
    # Setup
    print_header()
    setup_logging("DEBUG" if verbose else "INFO")
    
    # Load configuration
    try:
        cfg = load_config(config)
        console.print(f"[green]✓[/green] Loaded configuration")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load configuration: {e}")
        sys.exit(1)
    
    # Set default paths
    if charts_dir is None:
        charts_dir = Path("funding_graphs")
    
    if output is None:
        output = Path(f"transparency_report_round{round_number}.pptx")
    
    # Load and validate data
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Loading Excel data...", total=None)
        
        loader = DataLoader(cfg)
        result = loader.load(excel_file, round_number)
        
        progress.update(task, completed=True)
    
    # Print load summary
    result.print_summary()
    
    if show_mapping and result.column_mapping:
        console.print()
        print_column_mapping_table(result.column_mapping)
    
    # Check for critical errors
    if not result.is_valid:
        console.print("\n[red]✗[/red] Cannot proceed due to critical errors")
        sys.exit(1)
    
    if result.has_errors:
        console.print("\n[yellow]![/yellow] Proceeding with warnings...")
    
    # Analyze data
    console.print("\n[cyan]Analyzing data...[/cyan]")
    
    analyzer = FundingAnalyzer(cfg)
    analysis = analyzer.analyze(result.round_data, result.overview_data)
    
    console.print(f"[green]✓[/green] Analysis complete")
    console.print(f"  • {analysis.total_organizations} organizations")
    console.print(f"  • ${analysis.total_requested:,.2f} total requested")
    console.print(f"  • ${analysis.total_awarded:,.2f} total awarded")
    
    # Generate charts
    console.print("\n[cyan]Generating charts...[/cyan]")
    
    chart_results = generate_all_charts(cfg, analysis, charts_dir)
    
    total_charts = sum(len(paths) for paths in chart_results.values())
    console.print(f"[green]✓[/green] Generated {total_charts} charts/tables")
    
    for chart_type, paths in chart_results.items():
        if paths:
            console.print(f"  • {chart_type}: {len(paths)} files")
    
    # Generate presentation
    if not skip_presentation:
        console.print("\n[cyan]Creating presentation...[/cyan]")
        
        builder = PresentationBuilder(cfg, charts_dir, round_number)
        builder.build(analysis)
        builder.save(output)
    
    # Print summary
    print_summary(
        round_number=round_number,
        num_organizations=analysis.total_organizations,
        total_requested=analysis.total_requested,
        total_awarded=analysis.total_awarded,
        num_charts=total_charts,
        output_path=output
    )
    
    console.print("\n[bold green]✓ Report generation complete![/bold green]")


@click.command()
@click.argument("excel_file", type=click.Path(exists=True, path_type=Path))
def validate(excel_file: Path) -> None:
    """
    Validate an Excel file without generating a report.
    
    This command checks the Excel file structure and column names,
    reporting any issues that would prevent report generation.
    """
    print_header()
    setup_logging("INFO")
    
    cfg = load_config()
    loader = DataLoader(cfg)
    
    # Try to discover sheets and columns
    import pandas as pd
    
    try:
        xl = pd.ExcelFile(excel_file)
        console.print(f"[green]✓[/green] Found {len(xl.sheet_names)} sheets")
        
        for sheet in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet, nrows=0)
            console.print(f"  • {sheet}: {len(df.columns)} columns")
        
        # Try loading with round 1
        console.print("\n[cyan]Validating round 1 data...[/cyan]")
        result = loader.load(excel_file, 1)
        result.print_summary()
        
        if result.column_mapping:
            print_column_mapping_table(result.column_mapping)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Validation failed: {e}")
        sys.exit(1)


# Add validate command to the CLI group
@click.group()
def cli() -> None:
    """UOFC Funding Transparency Report Generator."""
    pass


cli.add_command(main, name="generate")
cli.add_command(validate, name="validate")


if __name__ == "__main__":
    # When run directly, use the main command
    main()
