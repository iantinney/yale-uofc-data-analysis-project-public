"""
Pie chart generators.

This module generates pie charts for categorical distributions
such as organization categories, age groups, and funding sources.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .base import BaseChart, setup_style

if TYPE_CHECKING:
    from ..analyzer import FundingAnalysis
    from ..config import Config


class PieChartGenerator(BaseChart):
    """Generates pie charts for funding analysis."""
    
    def __init__(self, config: Config, output_dir: Path) -> None:
        super().__init__(config, output_dir)
    
    def generate(self, analysis: FundingAnalysis) -> list[Path]:
        """
        Generate all pie charts from the analysis.
        
        Args:
            analysis: FundingAnalysis object
            
        Returns:
            List of paths to generated chart files
        """
        generated: list[Path] = []
        
        # Category distribution pie chart
        if analysis.top_categories is not None:
            path = self._generate_category_pie(analysis.top_categories)
            generated.append(path)
        
        # Age group distribution
        if analysis.age_group_counts is not None:
            path = self._generate_age_group_pie(analysis.age_group_counts)
            generated.append(path)
        
        # Dwight Hall distribution
        if analysis.dwight_hall_counts is not None:
            path = self._generate_dwight_hall_pie(analysis.dwight_hall_counts)
            generated.append(path)
        
        # Other funding sources distribution
        if analysis.other_funding_counts is not None:
            path = self._generate_other_funding_pie(analysis.other_funding_counts)
            generated.append(path)
        
        return generated
    
    def _generate_category_pie(self, top_categories: pd.DataFrame) -> Path:
        """Generate pie chart for organization categories."""
        setup_style()
        
        fig, ax = plt.subplots(figsize=self._get_figsize("pie_chart"))
        
        categories = top_categories["category"].tolist()
        sizes = top_categories["count"].tolist()
        colors = sns.color_palette(self.config.charts.palettes.categorical, len(categories))
        explode = [0.05] * len(categories)
        
        patches, texts, autotexts = ax.pie(
            sizes,
            labels=categories,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors,
            explode=explode,
            wedgeprops={"edgecolor": "white", "linewidth": 1}
        )
        
        # Style the labels
        for text in texts:
            text.set_fontsize(self._get_font_size("tick_label"))
        for autotext in autotexts:
            autotext.set_fontsize(self._get_font_size("tick_label"))
            autotext.set_color("white")
            autotext.set_fontweight("bold")
        
        ax.set_title(
            "Organizations by Category",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=20
        )
        
        plt.tight_layout()
        return self._save_figure("top_10_categories_pie.png")
    
    def _generate_age_group_pie(self, age_counts: pd.Series) -> Path:
        """Generate pie chart for age group distribution."""
        setup_style()
        
        fig, ax = plt.subplots(figsize=self._get_figsize("pie_chart"))
        
        colors = sns.color_palette("pastel", len(age_counts))
        
        patches, texts, autotexts = ax.pie(
            age_counts.values,
            labels=age_counts.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors,
            wedgeprops={"edgecolor": "white", "linewidth": 1}
        )
        
        for text in texts:
            text.set_fontsize(self._get_font_size("tick_label"))
        for autotext in autotexts:
            autotext.set_fontsize(self._get_font_size("tick_label"))
            autotext.set_color("white")
            autotext.set_fontweight("bold")
        
        ax.set_title(
            "Organizations by Age Group",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=20
        )
        ax.axis("equal")
        
        plt.tight_layout()
        return self._save_figure("age_group_pie.png")
    
    def _generate_dwight_hall_pie(self, dh_counts: pd.Series) -> Path:
        """Generate pie chart for Dwight Hall distribution."""
        setup_style()
        
        fig, ax = plt.subplots(figsize=self._get_figsize("pie_chart"))
        
        # Yale colors - blue for Dwight Hall, lighter for others
        colors = ["#66b3ff", "#ff9999"]
        
        patches, texts, autotexts = ax.pie(
            dh_counts.values,
            labels=dh_counts.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors,
            wedgeprops={"edgecolor": "white", "linewidth": 1},
            textprops={"fontsize": self._get_font_size("tick_label")}
        )
        
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")
        
        ax.set_title(
            "Dwight Hall Group Distribution",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=20
        )
        ax.axis("equal")
        
        plt.tight_layout()
        return self._save_figure("dwight_hall_distribution_pie_chart.png")
    
    def _generate_other_funding_pie(self, funding_counts: pd.Series) -> Path:
        """Generate pie chart for other funding sources."""
        setup_style()
        
        fig, ax = plt.subplots(figsize=self._get_figsize("pie_chart"))
        
        colors = sns.color_palette("pastel", len(funding_counts))
        
        patches, texts, autotexts = ax.pie(
            funding_counts.values,
            labels=funding_counts.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors,
            wedgeprops={"edgecolor": "white", "linewidth": 1}
        )
        
        for text in texts:
            text.set_fontsize(self._get_font_size("tick_label"))
        for autotext in autotexts:
            autotext.set_fontsize(self._get_font_size("tick_label"))
            autotext.set_color("white")
            autotext.set_fontweight("bold")
        
        ax.set_title(
            "Organizations Receiving Other Funding Sources",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=20
        )
        ax.axis("equal")
        
        plt.tight_layout()
        return self._save_figure("other_funding_sources_pie.png")
