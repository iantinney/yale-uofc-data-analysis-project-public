"""
Base chart utilities and abstract chart class.

This module provides common functionality for all chart generators,
including styling, text wrapping, and file saving.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import seaborn as sns

if TYPE_CHECKING:
    from ..analyzer import FundingAnalysis
    from ..config import Config


def insert_line_breaks(text: str, max_chars: int = 15) -> str:
    """
    Insert line breaks into text at word boundaries.
    
    Args:
        text: The text to wrap
        max_chars: Maximum characters per line
        
    Returns:
        Text with newlines inserted at appropriate positions
    """
    if len(text) <= max_chars:
        return text
    
    lines: list[str] = []
    remaining = text
    
    while len(remaining) > max_chars:
        # Find the first space after max_chars
        match = re.search(r"\s", remaining[max_chars:])
        if match:
            break_index = max_chars + match.start()
        else:
            break_index = len(remaining)
        
        lines.append(remaining[:break_index])
        remaining = remaining[break_index:].strip()
    
    lines.append(remaining)
    return "\n".join(lines)


def setup_style(style: str = "whitegrid", context: str = "talk") -> None:
    """
    Set up the seaborn/matplotlib style for charts.
    
    Args:
        style: Seaborn style name
        context: Seaborn context name
    """
    sns.set_theme(style=style, context=context)


def get_color_palette(palette_name: str, n_colors: int) -> list[tuple[float, ...]]:
    """
    Get a color palette from seaborn.
    
    Args:
        palette_name: Name of the palette
        n_colors: Number of colors needed
        
    Returns:
        List of RGB tuples
    """
    return sns.color_palette(palette_name, n_colors)


class BaseChart(ABC):
    """
    Abstract base class for chart generators.
    
    Subclasses must implement the generate() method to create specific
    chart types.
    """
    
    def __init__(self, config: Config, output_dir: Path) -> None:
        """
        Initialize the chart generator.
        
        Args:
            config: Configuration object
            output_dir: Directory to save generated charts
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def generate(self, analysis: FundingAnalysis) -> list[Path]:
        """
        Generate charts from the analysis data.
        
        Args:
            analysis: FundingAnalysis object containing computed statistics
            
        Returns:
            List of paths to generated chart files
        """
        pass
    
    def _save_figure(
        self, 
        filename: str, 
        dpi: int | None = None,
        bbox_inches: str = "tight"
    ) -> Path:
        """
        Save the current matplotlib figure.
        
        Args:
            filename: Name of the output file (without directory)
            dpi: Resolution (uses config default if not specified)
            bbox_inches: Bounding box setting for saving
            
        Returns:
            Path to the saved file
        """
        if dpi is None:
            dpi = self.config.charts.dpi
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=dpi, bbox_inches=bbox_inches)
        plt.close()
        
        return output_path
    
    def _get_figsize(self, chart_type: str) -> tuple[int, int]:
        """Get figure size for a chart type from config."""
        sizes = self.config.charts.figure_sizes.get(chart_type, [10, 6])
        return tuple(sizes)  # type: ignore
    
    def _get_font_size(self, element: str) -> int:
        """Get font size for an element from config."""
        return getattr(self.config.charts.fonts, element, 12)


class ChartGenerationError(Exception):
    """Raised when chart generation fails."""
    pass
