"""
Table generators.

This module generates table images and CSV exports for summary data.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import pandas as pd

from .base import BaseChart, insert_line_breaks, setup_style

if TYPE_CHECKING:
    from ..analyzer import FundingAnalysis
    from ..config import Config


class TableGenerator(BaseChart):
    """Generates table images and CSV exports."""
    
    def __init__(self, config: Config, output_dir: Path) -> None:
        super().__init__(config, output_dir)
    
    def generate(self, analysis: FundingAnalysis) -> list[Path]:
        """
        Generate all tables from the analysis.
        
        Args:
            analysis: FundingAnalysis object
            
        Returns:
            List of paths to generated files (images and CSVs)
        """
        generated: list[Path] = []
        
        # Overview/Rubric table
        if analysis.overview_formatted is not None:
            paths = self._generate_overview_table(analysis.overview_formatted)
            generated.extend(paths)
        
        # Top categories table
        if analysis.top_categories is not None:
            path = self._generate_categories_csv(analysis.top_categories)
            generated.append(path)
        
        # Average by category table
        if analysis.avg_by_category is not None:
            path = self._generate_avg_category_csv(analysis.avg_by_category)
            generated.append(path)
        
        # Age group table
        if analysis.age_group_counts is not None:
            path = self._generate_age_group_csv(analysis.age_group_counts)
            generated.append(path)
        
        # Average by age table
        if analysis.avg_by_age is not None:
            path = self._generate_avg_age_csv(analysis.avg_by_age)
            generated.append(path)
        
        # Dwight Hall table
        if analysis.dwight_hall_counts is not None:
            paths = self._generate_dwight_hall_table(analysis.dwight_hall_counts)
            generated.extend(paths)
        
        # Other funding table
        if analysis.other_funding_counts is not None:
            path = self._generate_other_funding_csv(analysis.other_funding_counts)
            generated.append(path)
        
        # Average by other funding
        if analysis.avg_by_other_funding is not None:
            path = self._generate_avg_other_funding_csv(analysis.avg_by_other_funding)
            generated.append(path)
        
        # Top organizations table
        if analysis.top_organizations is not None:
            paths = self._generate_top_orgs_table(analysis.top_organizations)
            generated.extend(paths)
        
        return generated
    
    def _create_table_image(
        self,
        df: pd.DataFrame,
        output_path: Path,
        title: str | None = None,
        figsize: tuple[int, int] | None = None
    ) -> Path:
        """
        Create a styled table image from a DataFrame.
        
        Args:
            df: DataFrame to render as table
            output_path: Path for output file
            title: Optional title above the table
            figsize: Optional figure size override
        """
        setup_style()
        
        num_rows, num_cols = df.shape
        
        if figsize is None:
            # Calculate figsize based on content
            figsize = (max(num_cols * 2, 6), max(num_rows * 0.6 + 2, 3))
        
        fig, ax = plt.subplots(figsize=figsize)
        ax.axis("off")
        
        # Create table
        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            cellLoc="center",
            loc="center",
            colColours=["#add8e6"] * num_cols,  # Light blue header
            edges="closed"
        )
        
        # Style table
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1.5, 2)
        
        # Style cells
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                # Header row
                cell.set_text_props(weight="bold", color="black")
                cell.set_facecolor("#add8e6")
            else:
                # Alternate row colors
                if row % 2 == 0:
                    cell.set_facecolor("#ffffff")
                else:
                    cell.set_facecolor("#f2f2f2")
            
            cell.set_edgecolor("#cccccc")
        
        table.auto_set_column_width(col=list(range(num_cols)))
        
        if title:
            ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.config.charts.dpi, bbox_inches="tight")
        plt.close()
        
        return output_path
    
    def _generate_overview_table(self, df: pd.DataFrame) -> list[Path]:
        """Generate overview/rubric table image."""
        output_path = self.output_dir / "rubric.png"
        
        self._create_table_image(
            df,
            output_path,
            title="Overview Rubric",
            figsize=(max(len(df.columns) * 2.5, 10), len(df) * 0.8 + 3)
        )
        
        return [output_path]
    
    def _generate_categories_csv(self, df: pd.DataFrame) -> Path:
        """Generate categories CSV."""
        output_path = self.output_dir / "top_10_categories_table.csv"
        
        df_export = df.rename(columns={
            "category": "Organization Category",
            "count": "Number of Organizations",
            "percentage": "Percentage"
        })
        
        df_export.to_csv(output_path, index=False)
        return output_path
    
    def _generate_avg_category_csv(self, df: pd.DataFrame) -> Path:
        """Generate average by category CSV."""
        output_path = self.output_dir / "avg_requested_by_category_table.csv"
        
        df_export = df.reset_index()
        df_export.columns = [
            "Organization Category",
            "Average Amount Requested ($)",
            "Average Amount Awarded ($)"
        ]
        
        df_export.to_csv(output_path, index=False, float_format="%.2f")
        return output_path
    
    def _generate_age_group_csv(self, counts: pd.Series) -> Path:
        """Generate age group counts CSV."""
        output_path = self.output_dir / "age_group_table.csv"
        
        df = counts.reset_index()
        df.columns = ["Organization Age", "Count"]
        
        df.to_csv(output_path, index=False)
        return output_path
    
    def _generate_avg_age_csv(self, df: pd.DataFrame) -> Path:
        """Generate average by age CSV."""
        output_path = self.output_dir / "avg_req_award_by_age_table.csv"
        df.to_csv(output_path, float_format="%.2f")
        return output_path
    
    def _generate_dwight_hall_table(self, counts: pd.Series) -> list[Path]:
        """Generate Dwight Hall distribution table."""
        total = counts.sum()
        
        # Create DataFrame
        df = pd.DataFrame({
            "Group": counts.index,
            "Organization Count": counts.values,
            "Percentage": [f"{(c / total * 100):.2f}%" for c in counts.values]
        })
        
        # Generate image
        img_path = self.output_dir / "dwight_hall_distribution_table.png"
        self._create_table_image(
            df,
            img_path,
            title="Dwight Hall Group Distribution",
            figsize=(8, 3)
        )
        
        return [img_path]
    
    def _generate_other_funding_csv(self, counts: pd.Series) -> Path:
        """Generate other funding counts CSV."""
        output_path = self.output_dir / "other_funding_sources_counts.csv"
        
        df = counts.reset_index()
        df.columns = ["Has Other Funding", "Count"]
        
        df.to_csv(output_path, index=False)
        return output_path
    
    def _generate_avg_other_funding_csv(self, df: pd.DataFrame) -> Path:
        """Generate average by other funding CSV."""
        output_path = self.output_dir / "avg_req_award_other_funding_table.csv"
        df.to_csv(output_path, float_format="%.2f")
        return output_path
    
    def _generate_top_orgs_table(self, df: pd.DataFrame) -> list[Path]:
        """Generate top organizations table (image and CSV)."""
        generated: list[Path] = []
        
        # Prepare display DataFrame
        df_display = df.copy()
        
        # Apply line breaks to long names
        if "organization_name" in df_display.columns:
            df_display["organization_name"] = df_display["organization_name"].apply(
                lambda x: insert_line_breaks(str(x), max_chars=25)
            )
        if "organization_category" in df_display.columns:
            df_display["organization_category"] = df_display["organization_category"].apply(
                lambda x: insert_line_breaks(str(x), max_chars=20)
            )
        
        # Rename columns for display
        column_map = {
            "organization_name": "Organization",
            "organization_category": "Category",
            "amount_requested": "Requested ($)",
            "amount_awarded": "Awarded ($)",
            "funding_ratio_pct": "Funding Ratio (%)"
        }
        df_display = df_display.rename(columns=column_map)
        
        # Format currency columns
        for col in ["Requested ($)", "Awarded ($)"]:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
        
        # Generate image
        img_path = self.output_dir / "top_5_organizations_table.png"
        self._create_table_image(
            df_display,
            img_path,
            title="Top 5 Organizations: Funding Overview",
            figsize=(15, 6)
        )
        generated.append(img_path)
        
        # Generate CSV
        csv_path = self.output_dir / "top_5_organizations_table.csv"
        df.rename(columns=column_map).to_csv(csv_path, index=False, float_format="%.2f")
        generated.append(csv_path)
        
        return generated
