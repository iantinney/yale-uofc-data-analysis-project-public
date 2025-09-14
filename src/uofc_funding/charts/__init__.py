"""
Chart generation package.

This package provides modular chart generators for funding analysis
visualizations including pie charts, bar charts, and tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .bar_charts import BarChartGenerator
from .base import BaseChart, ChartGenerationError, insert_line_breaks
from .pie_charts import PieChartGenerator
from .tables import TableGenerator

if TYPE_CHECKING:
    from ..analyzer import FundingAnalysis
    from ..config import Config

__all__ = [
    "BaseChart",
    "BarChartGenerator",
    "ChartGenerationError",
    "PieChartGenerator",
    "TableGenerator",
    "generate_all_charts",
    "insert_line_breaks",
]


def generate_all_charts(
    config: Config, analysis: FundingAnalysis, output_dir: Path | str
) -> dict[str, list[Path]]:
    """
    Generate all charts and tables from the analysis.

    This is a convenience function that creates and runs all chart generators.

    Args:
        config: Configuration object
        analysis: FundingAnalysis object with computed statistics
        output_dir: Directory to save generated files

    Returns:
        Dictionary mapping chart type to list of generated file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[Path]] = {}

    # Generate pie charts
    pie_generator = PieChartGenerator(config, output_dir)
    results["pie_charts"] = pie_generator.generate(analysis)

    # Generate bar charts
    bar_generator = BarChartGenerator(config, output_dir)
    results["bar_charts"] = bar_generator.generate(analysis)

    # Generate tables
    table_generator = TableGenerator(config, output_dir)
    results["tables"] = table_generator.generate(analysis)

    return results
