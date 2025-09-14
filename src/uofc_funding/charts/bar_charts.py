"""
Bar chart generators.

This module generates bar charts for comparing requested vs awarded
amounts across different groupings.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .base import BaseChart, setup_style

if TYPE_CHECKING:
    from ..analyzer import FundingAnalysis
    from ..config import Config


class BarChartGenerator(BaseChart):
    """Generates bar charts for funding analysis."""

    def __init__(self, config: Config, output_dir: Path) -> None:
        super().__init__(config, output_dir)

    def generate(self, analysis: FundingAnalysis) -> list[Path]:
        """
        Generate all bar charts from the analysis.

        Args:
            analysis: FundingAnalysis object

        Returns:
            List of paths to generated chart files
        """
        generated: list[Path] = []

        # Average by category (grouped bar)
        if analysis.avg_by_category is not None:
            path = self._generate_avg_by_category(analysis.avg_by_category)
            generated.append(path)

        # Total by category
        if analysis.total_by_category is not None:
            path = self._generate_total_by_category(analysis.total_by_category)
            generated.append(path)

        # Average by age group
        if analysis.avg_by_age is not None:
            path = self._generate_avg_by_age(analysis.avg_by_age)
            generated.append(path)

        # Average by Dwight Hall status
        if analysis.avg_by_dwight_hall is not None:
            path = self._generate_avg_by_dwight_hall(analysis.avg_by_dwight_hall)
            generated.append(path)

        # Average by other funding status
        if analysis.avg_by_other_funding is not None:
            path = self._generate_avg_by_other_funding(analysis.avg_by_other_funding)
            generated.append(path)

        return generated

    def _generate_avg_by_category(self, data: pd.DataFrame, top_n: int = 10) -> Path:
        """Generate grouped bar chart for average amounts by category."""
        setup_style()

        # Take top N categories
        data = data.head(top_n)

        fig, ax = plt.subplots(figsize=self._get_figsize("grouped_bar"))

        x = np.arange(len(data))
        bar_width = 0.35

        # Colors from Blues and Oranges palettes
        requested_color = sns.color_palette("Blues")[3]
        awarded_color = sns.color_palette("Oranges")[3]

        ax.bar(
            x - bar_width / 2,
            data["amount_requested"],
            bar_width,
            label="Requested",
            color=requested_color,
            edgecolor="black",
            linewidth=0.5,
        )

        ax.bar(
            x + bar_width / 2,
            data["amount_awarded"],
            bar_width,
            label="Awarded",
            color=awarded_color,
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xlabel("Organization Category", fontsize=self._get_font_size("axis_label"))
        ax.set_ylabel("Amount ($)", fontsize=self._get_font_size("axis_label"))
        ax.set_title(
            "Average Amount Requested & Awarded by Organization Category",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=15,
        )

        ax.set_xticks(x)
        ax.set_xticklabels(
            data.index, rotation=45, ha="right", fontsize=self._get_font_size("tick_label")
        )

        ax.legend(fontsize=self._get_font_size("legend"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        plt.tight_layout()
        return self._save_figure("avg_requested_by_category_bar.png")

    def _generate_total_by_category(self, data: pd.DataFrame, top_n: int = 10) -> Path:
        """Generate bar chart for total amounts by category."""
        setup_style()

        data = data.head(top_n)

        fig, ax = plt.subplots(figsize=self._get_figsize("bar_chart"))

        colors = sns.color_palette("magma", len(data))

        ax.bar(
            range(len(data)),
            data["amount_requested"],
            color=colors,
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xlabel("Organization Category", fontsize=self._get_font_size("axis_label"))
        ax.set_ylabel("Total Amount Requested ($)", fontsize=self._get_font_size("axis_label"))
        ax.set_title(
            "Total Amount Requested by Organization Category",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=15,
        )

        ax.set_xticks(range(len(data)))
        ax.set_xticklabels(
            data.index, rotation=45, ha="right", fontsize=self._get_font_size("tick_label")
        )

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        plt.tight_layout()
        return self._save_figure("total_requested_by_category_bar.png")

    def _generate_avg_by_age(self, data: pd.DataFrame) -> Path:
        """Generate grouped bar chart for average amounts by age group."""
        setup_style()

        fig, ax = plt.subplots(figsize=self._get_figsize("bar_chart"))

        x = np.arange(len(data))
        bar_width = 0.35

        colors = sns.color_palette("Paired")

        ax.bar(
            x - bar_width / 2,
            data["amount_requested"],
            bar_width,
            label="Amount Requested",
            color=colors[1],
            edgecolor="black",
            linewidth=0.5,
        )

        ax.bar(
            x + bar_width / 2,
            data["amount_awarded"],
            bar_width,
            label="Amount Awarded",
            color=colors[5],
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xlabel("Organization Age", fontsize=self._get_font_size("axis_label"))
        ax.set_ylabel("Average Amount ($)", fontsize=self._get_font_size("axis_label"))
        ax.set_title(
            "Average Amount Requested & Awarded by Organization Age",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=15,
        )

        ax.set_xticks(x)
        ax.set_xticklabels(data.index, rotation=0, fontsize=self._get_font_size("tick_label"))

        ax.legend(fontsize=self._get_font_size("legend"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        plt.tight_layout()
        return self._save_figure("avg_req_award_by_age_bar.png")

    def _generate_avg_by_dwight_hall(self, data: pd.DataFrame) -> Path:
        """Generate grouped bar chart for Dwight Hall comparison."""
        setup_style()

        fig, ax = plt.subplots(figsize=self._get_figsize("bar_chart"))

        x = np.arange(len(data))
        bar_width = 0.35

        ax.bar(
            x - bar_width / 2,
            data["amount_requested"],
            bar_width,
            label="Amount Requested",
            color="#449999",
            edgecolor="black",
            linewidth=0.5,
        )

        ax.bar(
            x + bar_width / 2,
            data["amount_awarded"],
            bar_width,
            label="Amount Awarded",
            color="#339202",
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xlabel("Group", fontsize=self._get_font_size("axis_label"))
        ax.set_ylabel("Average Amount ($)", fontsize=self._get_font_size("axis_label"))
        ax.set_title(
            "Average Amount Requested & Awarded by Dwight Hall Group",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=15,
        )

        ax.set_xticks(x)
        ax.set_xticklabels(data.index, rotation=0, fontsize=self._get_font_size("tick_label"))

        ax.legend(fontsize=self._get_font_size("legend"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        plt.tight_layout()
        return self._save_figure("avg_req_award_dwight_hall_bar.png")

    def _generate_avg_by_other_funding(self, data: pd.DataFrame) -> Path:
        """Generate grouped bar chart for other funding comparison."""
        setup_style()

        fig, ax = plt.subplots(figsize=self._get_figsize("bar_chart"))

        x = np.arange(len(data))
        bar_width = 0.35

        colors = sns.color_palette("Set2")

        ax.bar(
            x - bar_width / 2,
            data["amount_requested"],
            bar_width,
            label="Amount Requested",
            color=colors[0],
            edgecolor="black",
            linewidth=0.5,
        )

        ax.bar(
            x + bar_width / 2,
            data["amount_awarded"],
            bar_width,
            label="Amount Awarded",
            color=colors[1],
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xlabel("Has Other Funding Sources", fontsize=self._get_font_size("axis_label"))
        ax.set_ylabel("Average Amount ($)", fontsize=self._get_font_size("axis_label"))
        ax.set_title(
            "Average Amount Requested & Awarded by Other Funding Sources",
            fontsize=self._get_font_size("title"),
            fontweight="bold",
            pad=15,
        )

        ax.set_xticks(x)
        ax.set_xticklabels(data.index, rotation=0, fontsize=self._get_font_size("tick_label"))

        ax.legend(fontsize=self._get_font_size("legend"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        plt.tight_layout()
        return self._save_figure("avg_req_award_other_funding_bar.png")
