"""
Data analysis utilities.

This module contains functions for analyzing funding data and computing
statistics used in charts and tables.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from .config import Config


@dataclass
class FundingAnalysis:
    """Container for all computed funding statistics."""

    # Overview statistics
    total_organizations: int = 0
    total_requested: float = 0.0
    total_awarded: float = 0.0
    average_requested: float = 0.0
    average_awarded: float = 0.0
    overall_funding_ratio: float = 0.0

    # Category analysis
    category_counts: pd.Series | None = None
    top_categories: pd.DataFrame | None = None
    avg_by_category: pd.DataFrame | None = None
    total_by_category: pd.DataFrame | None = None

    # Age group analysis
    age_group_counts: pd.Series | None = None
    avg_by_age: pd.DataFrame | None = None

    # Dwight Hall analysis
    dwight_hall_counts: pd.Series | None = None
    avg_by_dwight_hall: pd.DataFrame | None = None

    # Other funding analysis
    other_funding_counts: pd.Series | None = None
    avg_by_other_funding: pd.DataFrame | None = None

    # Top organizations
    top_organizations: pd.DataFrame | None = None

    # Overview comparison (year-over-year)
    overview_formatted: pd.DataFrame | None = None


class FundingAnalyzer:
    """
    Analyzes funding data to produce statistics for visualization.

    This class computes various aggregations and statistics from the raw
    funding data, handling missing columns gracefully by skipping analyses
    that require unavailable data.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the analyzer.

        Args:
            config: Configuration object
        """
        self.config = config

    def analyze(
        self, round_data: pd.DataFrame, overview_data: pd.DataFrame | None = None
    ) -> FundingAnalysis:
        """
        Perform full analysis of funding data.

        Args:
            round_data: DataFrame with normalized column names
            overview_data: Optional overview DataFrame for year-over-year comparison

        Returns:
            FundingAnalysis object containing all computed statistics
        """
        analysis = FundingAnalysis()

        # Basic statistics (always computed)
        analysis.total_organizations = len(round_data)
        analysis.total_requested = round_data["amount_requested"].sum()
        analysis.total_awarded = round_data["amount_awarded"].sum()
        analysis.average_requested = round_data["amount_requested"].mean()
        analysis.average_awarded = round_data["amount_awarded"].mean()

        if analysis.total_requested > 0:
            analysis.overall_funding_ratio = analysis.total_awarded / analysis.total_requested

        # Category analysis (requires organization_category)
        if "organization_category" in round_data.columns:
            analysis.category_counts = self._compute_category_counts(round_data)
            analysis.top_categories = self._compute_top_categories(round_data)
            analysis.avg_by_category = self._compute_avg_by_category(round_data)
            analysis.total_by_category = self._compute_total_by_category(round_data)

        # Age group analysis (requires organization_age)
        if "organization_age" in round_data.columns:
            analysis.age_group_counts = self._compute_age_group_counts(round_data)
            analysis.avg_by_age = self._compute_avg_by_age(round_data)

        # Dwight Hall analysis (requires other_funding column)
        # Note: We check for "Dwight Hall" in the other_funding column
        if "other_funding" in round_data.columns:
            analysis.dwight_hall_counts = self._compute_dwight_hall_counts(round_data)
            analysis.avg_by_dwight_hall = self._compute_avg_by_dwight_hall(round_data)
            analysis.other_funding_counts = self._compute_other_funding_counts(round_data)
            analysis.avg_by_other_funding = self._compute_avg_by_other_funding(round_data)

        # Also check for explicit dwight_hall column
        if "dwight_hall" in round_data.columns and analysis.dwight_hall_counts is None:
            analysis.dwight_hall_counts = self._compute_dwight_hall_from_column(round_data)
            analysis.avg_by_dwight_hall = self._compute_avg_by_dwight_hall_column(round_data)

        # Top organizations
        analysis.top_organizations = self._compute_top_organizations(round_data)

        # Overview formatting (if available)
        if overview_data is not None:
            analysis.overview_formatted = self._format_overview(overview_data)

        return analysis

    def _compute_category_counts(self, df: pd.DataFrame) -> pd.Series:
        """Count organizations per category."""
        return df["organization_category"].value_counts()

    def _compute_top_categories(self, df: pd.DataFrame, top_n: int = 9) -> pd.DataFrame:
        """
        Get top N categories plus an "Other" category.

        Returns DataFrame with columns: category, count, percentage
        """
        counts = df["organization_category"].value_counts()
        total = counts.sum()

        top = counts.head(top_n)
        other_count = counts.iloc[top_n:].sum() if len(counts) > top_n else 0

        result = pd.DataFrame(
            {
                "category": list(top.index) + (["Other Categories"] if other_count > 0 else []),
                "count": list(top.values) + ([other_count] if other_count > 0 else []),
            }
        )
        result["percentage"] = (result["count"] / total * 100).round(2)

        return result

    def _compute_avg_by_category(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute average requested/awarded by category."""
        grouped = (
            df.groupby("organization_category")[["amount_requested", "amount_awarded"]]
            .mean()
            .round(2)
        )

        return grouped.sort_values("amount_requested", ascending=False)

    def _compute_total_by_category(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute total requested/awarded by category."""
        grouped = (
            df.groupby("organization_category")[["amount_requested", "amount_awarded"]]
            .sum()
            .round(2)
        )

        return grouped.sort_values("amount_requested", ascending=False)

    def _compute_age_group_counts(self, df: pd.DataFrame) -> pd.Series:
        """Count organizations per age group."""
        return df["organization_age"].value_counts()

    def _compute_avg_by_age(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute average requested/awarded by organization age."""
        grouped = (
            df.groupby("organization_age")[["amount_requested", "amount_awarded"]].mean().round(2)
        )

        # Sort by age group in logical order
        age_order = ["0-1 Year", "1-2 Years", "2-5 Years", "5-10 Years", "10+ Years"]
        available_ages = [a for a in age_order if a in grouped.index]
        other_ages = [a for a in grouped.index if a not in age_order]

        return grouped.reindex(available_ages + other_ages)

    def _compute_dwight_hall_counts(self, df: pd.DataFrame) -> pd.Series:
        """
        Count organizations by Dwight Hall affiliation.

        Checks if "Dwight Hall" appears in the other_funding column.
        """
        df = df.copy()
        df["is_dwight_hall"] = (
            df["other_funding"].astype(str).str.contains("Dwight Hall", case=False, na=False)
        )

        counts = df["is_dwight_hall"].value_counts()
        counts.index = counts.index.map({True: "Dwight Hall Group", False: "Other Group"})

        return counts

    def _compute_avg_by_dwight_hall(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute average requested/awarded by Dwight Hall status."""
        df = df.copy()
        df["is_dwight_hall"] = (
            df["other_funding"].astype(str).str.contains("Dwight Hall", case=False, na=False)
        )

        grouped = (
            df.groupby("is_dwight_hall")[["amount_requested", "amount_awarded"]].mean().round(2)
        )

        grouped.index = grouped.index.map({True: "Dwight Hall Group", False: "Other Group"})

        return grouped

    def _compute_dwight_hall_from_column(self, df: pd.DataFrame) -> pd.Series:
        """Count organizations by explicit Dwight Hall column."""
        counts = df["dwight_hall"].value_counts()

        # Normalize Yes/No values
        normalized = {}
        for val, count in counts.items():
            val_str = str(val).strip().lower()
            if val_str in ("yes", "y", "true", "1"):
                normalized["Dwight Hall Group"] = normalized.get("Dwight Hall Group", 0) + count
            else:
                normalized["Other Group"] = normalized.get("Other Group", 0) + count

        return pd.Series(normalized)

    def _compute_avg_by_dwight_hall_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute average by explicit Dwight Hall column."""
        df = df.copy()
        df["is_dwight_hall"] = (
            df["dwight_hall"].astype(str).str.lower().isin(["yes", "y", "true", "1"])
        )

        grouped = (
            df.groupby("is_dwight_hall")[["amount_requested", "amount_awarded"]].mean().round(2)
        )

        grouped.index = grouped.index.map({True: "Dwight Hall Group", False: "Other Group"})

        return grouped

    def _compute_other_funding_counts(self, df: pd.DataFrame) -> pd.Series:
        """Count organizations by whether they have other funding sources."""
        df = df.copy()
        df["has_other_funding"] = ~df["other_funding"].isna() & (df["other_funding"] != "")

        counts = df["has_other_funding"].value_counts()
        counts.index = counts.index.map({True: "Yes", False: "No"})

        return counts

    def _compute_avg_by_other_funding(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute average requested/awarded by other funding status."""
        df = df.copy()
        df["has_other_funding"] = ~df["other_funding"].isna() & (df["other_funding"] != "")

        grouped = (
            df.groupby("has_other_funding")[["amount_requested", "amount_awarded"]].mean().round(2)
        )

        grouped.index = grouped.index.map({True: "Yes", False: "No"})

        return grouped

    def _compute_top_organizations(self, df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
        """Get top N organizations by amount requested."""
        cols = ["organization_name", "amount_requested", "amount_awarded"]
        if "organization_category" in df.columns:
            cols.insert(1, "organization_category")

        top = df.nlargest(top_n, "amount_requested")[cols].copy()

        # Calculate funding ratio
        top["funding_ratio_pct"] = ((top["amount_awarded"] / top["amount_requested"]) * 100).round(
            2
        )

        return top

    def _format_overview(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format overview data for display.

        Applies appropriate formatting (currency, percentages) based on row labels.
        """
        df = df.copy()

        # Convert all non-metric columns to object type for mixed string/numeric values
        for col in df.columns:
            if col != "metric":
                df[col] = df[col].astype(object)

        # Define formatting rules by metric name patterns
        currency_patterns = ["budget", "requested", "awarded", "average", "target"]
        percentage_patterns = ["ratio", "percentage"]
        integer_patterns = ["# of", "number of"]

        # Apply formatting to each row
        for idx, row in df.iterrows():
            metric = str(row.get("metric", "")).lower()

            # Determine formatting type
            if any(p in metric for p in currency_patterns):
                for col in df.columns[1:]:
                    if col != "metric" and "percentage" not in col.lower():
                        with contextlib.suppress(ValueError, TypeError):
                            df.at[idx, col] = self._format_currency(row[col])

            elif any(p in metric for p in percentage_patterns):
                for col in df.columns[1:]:
                    if col != "metric":
                        with contextlib.suppress(ValueError, TypeError):
                            df.at[idx, col] = self._format_percentage(row[col])

            elif any(p in metric for p in integer_patterns):
                for col in df.columns[1:]:
                    if col != "metric":
                        with contextlib.suppress(ValueError, TypeError):
                            df.at[idx, col] = self._format_integer(row[col])

        return df

    @staticmethod
    def _format_currency(value: float | int | str) -> str:
        """Format a value as currency."""
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_percentage(value: float | int | str) -> str:
        """Format a value as percentage."""
        try:
            val = float(value)
            # If value is already in percentage form (> 1), use as-is
            if abs(val) > 1:
                return f"{val:.2f}%"
            # Otherwise, convert from decimal
            return f"{val * 100:.2f}%"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_integer(value: float | int | str) -> str:
        """Format a value as integer."""
        try:
            return f"{int(float(value)):,}"
        except (ValueError, TypeError):
            return str(value)
