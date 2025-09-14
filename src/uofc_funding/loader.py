"""
Data loading and validation utilities.

This module handles loading Excel files, validating data quality,
and normalizing column names using the configured aliases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from .config import Config

console = Console()


@dataclass
class ValidationWarning:
    """Represents a data validation warning."""

    severity: str  # "warning" or "error"
    message: str
    details: str | None = None

    def __str__(self) -> str:
        if self.details:
            return f"[{self.severity.upper()}] {self.message}: {self.details}"
        return f"[{self.severity.upper()}] {self.message}"


@dataclass
class LoadResult:
    """Result of loading and validating an Excel file."""

    round_data: pd.DataFrame | None = None
    overview_data: pd.DataFrame | None = None
    column_mapping: dict[str, str] = field(default_factory=dict)
    warnings: list[ValidationWarning] = field(default_factory=list)
    sheet_names: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the load result has minimum required data."""
        return self.round_data is not None and len(self.round_data) > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level warnings."""
        return any(w.severity == "error" for w in self.warnings)

    def print_summary(self) -> None:
        """Print a summary of the load result to the console."""
        if self.round_data is not None:
            console.print(f"[green]✓[/green] Loaded {len(self.round_data)} organizations")

        if self.overview_data is not None:
            console.print(f"[green]✓[/green] Loaded overview data ({len(self.overview_data)} rows)")

        if self.warnings:
            console.print(f"\n[yellow]Warnings ({len(self.warnings)}):[/yellow]")
            for warning in self.warnings:
                if warning.severity == "error":
                    console.print(f"  [red]✗[/red] {warning.message}")
                else:
                    console.print(f"  [yellow]![/yellow] {warning.message}")
                if warning.details:
                    console.print(f"    [dim]{warning.details}[/dim]")


class DataLoader:
    """
    Handles loading and validating Excel data for funding reports.

    This class manages the entire data loading pipeline:
    1. Loading the Excel file and discovering sheets
    2. Resolving column aliases to actual column names
    3. Validating data quality and completeness
    4. Normalizing data for downstream processing
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the data loader.

        Args:
            config: Configuration object with column aliases and validation settings
        """
        self.config = config

    def load(self, excel_path: str | Path, round_number: int) -> LoadResult:
        """
        Load and validate data from an Excel file.

        Args:
            excel_path: Path to the Excel file
            round_number: The funding round number (1, 2, 3, etc.)

        Returns:
            LoadResult containing the loaded data and any warnings
        """
        excel_path = Path(excel_path)
        result = LoadResult()

        # Check file exists
        if not excel_path.exists():
            result.warnings.append(
                ValidationWarning(
                    severity="error", message="Excel file not found", details=str(excel_path)
                )
            )
            return result

        # Load Excel file
        try:
            excel_file = pd.ExcelFile(excel_path)
            result.sheet_names = excel_file.sheet_names
        except Exception as e:
            result.warnings.append(
                ValidationWarning(
                    severity="error", message="Failed to open Excel file", details=str(e)
                )
            )
            return result

        # Load round decision sheet
        round_sheet_name = self.config.sheets.get_round_sheet_name(round_number)
        result.round_data, round_warnings = self._load_round_sheet(
            excel_file, round_sheet_name, result
        )
        result.warnings.extend(round_warnings)

        # Load overview sheet (optional)
        overview_sheet_name = self.config.sheets.overview_sheet
        if overview_sheet_name in result.sheet_names:
            result.overview_data, overview_warnings = self._load_overview_sheet(
                excel_file, overview_sheet_name
            )
            result.warnings.extend(overview_warnings)
        else:
            result.warnings.append(
                ValidationWarning(
                    severity="warning",
                    message=f"Overview sheet '{overview_sheet_name}' not found",
                    details="Year-over-year comparison will be skipped",
                )
            )

        return result

    def _load_round_sheet(
        self, excel_file: pd.ExcelFile, sheet_name: str, result: LoadResult
    ) -> tuple[pd.DataFrame | None, list[ValidationWarning]]:
        """Load and validate the round decision sheet."""
        warnings: list[ValidationWarning] = []

        if sheet_name not in excel_file.sheet_names:
            # Try to find a similar sheet name
            similar = [s for s in excel_file.sheet_names if "decision" in s.lower()]
            warnings.append(
                ValidationWarning(
                    severity="error",
                    message=f"Sheet '{sheet_name}' not found",
                    details=f"Available sheets: {excel_file.sheet_names}. Similar: {similar}",
                )
            )
            return None, warnings

        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        except Exception as e:
            warnings.append(
                ValidationWarning(
                    severity="error", message=f"Failed to read sheet '{sheet_name}'", details=str(e)
                )
            )
            return None, warnings

        # Check minimum rows
        if len(df) < self.config.validation.min_rows:
            warnings.append(
                ValidationWarning(
                    severity="error",
                    message=f"Sheet has too few rows ({len(df)})",
                    details=f"Minimum required: {self.config.validation.min_rows}",
                )
            )
            return None, warnings

        # Resolve column aliases
        available_columns = df.columns.tolist()
        resolved, missing_required, missing_optional = self.config.resolve_all_columns(
            available_columns
        )
        result.column_mapping = resolved

        # Report missing required columns
        for col in missing_required:
            warnings.append(
                ValidationWarning(
                    severity="error",
                    message=f"Required column '{col}' not found",
                    details=f"Tried aliases: {self.config.column_aliases.get(col, [])}",
                )
            )

        # Report missing optional columns
        for col in missing_optional:
            warnings.append(
                ValidationWarning(
                    severity="warning",
                    message=f"Optional column '{col}' not found",
                    details="Related visualizations will be skipped",
                )
            )

        if missing_required:
            return None, warnings

        # Normalize column names to canonical names
        df = self._normalize_columns(df, resolved)

        # Validate data quality
        quality_warnings = self._validate_data_quality(df)
        warnings.extend(quality_warnings)

        # Convert numeric columns
        df = self._convert_numeric_columns(df)

        return df, warnings

    def _load_overview_sheet(
        self, excel_file: pd.ExcelFile, sheet_name: str
    ) -> tuple[pd.DataFrame | None, list[ValidationWarning]]:
        """Load and validate the overview sheet."""
        warnings: list[ValidationWarning] = []

        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        except Exception as e:
            warnings.append(
                ValidationWarning(
                    severity="warning", message="Failed to read overview sheet", details=str(e)
                )
            )
            return None, warnings

        # Rename first column to 'metric' if it's unnamed
        first_col = df.columns[0]
        if "unnamed" in str(first_col).lower() or first_col == "":
            df = df.rename(columns={first_col: "metric"})
        else:
            df = df.rename(columns={first_col: "metric"})

        # Look for year columns (2023-2024, 2024-2025, etc.)
        year_pattern_cols = [
            c
            for c in df.columns
            if "-" in str(c) and any(str(y) in str(c) for y in range(2020, 2030))
        ]

        if len(year_pattern_cols) < 2:
            warnings.append(
                ValidationWarning(
                    severity="warning",
                    message="Could not identify year comparison columns in overview",
                    details=f"Found columns: {df.columns.tolist()}",
                )
            )

        return df, warnings

    def _normalize_columns(self, df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
        """
        Rename columns from actual Excel names to canonical names.

        This allows downstream code to use consistent column names
        regardless of the actual names in the Excel file.
        """
        reverse_mapping = {v: k for k, v in mapping.items()}
        return df.rename(columns=reverse_mapping)

    def _validate_data_quality(self, df: pd.DataFrame) -> list[ValidationWarning]:
        """Check data quality and return warnings for issues."""
        warnings: list[ValidationWarning] = []

        # Check for missing values in key columns
        key_columns = ["organization_name", "amount_requested", "amount_awarded"]

        for col in key_columns:
            if col in df.columns:
                missing_count = df[col].isna().sum()
                missing_pct = (missing_count / len(df)) * 100

                if missing_pct > 0:
                    warnings.append(
                        ValidationWarning(
                            severity="warning"
                            if missing_pct < self.config.validation.max_missing_percent
                            else "error",
                            message=f"Missing values in '{col}'",
                            details=f"{missing_count} rows ({missing_pct:.1f}%) have missing values",
                        )
                    )

        # Check for negative amounts
        for col in ["amount_requested", "amount_awarded"]:
            if col in df.columns:
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    warnings.append(
                        ValidationWarning(
                            severity="warning",
                            message=f"Negative values in '{col}'",
                            details=f"{negative_count} rows have negative amounts",
                        )
                    )

        # Check for duplicate organization names
        if "organization_name" in df.columns:
            duplicates = df["organization_name"].duplicated().sum()
            if duplicates > 0:
                warnings.append(
                    ValidationWarning(
                        severity="warning",
                        message="Duplicate organization names found",
                        details=f"{duplicates} duplicate entries",
                    )
                )

        return warnings

    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert columns that should be numeric."""
        numeric_columns = [
            "amount_requested",
            "amount_awarded",
            "funding_ratio",
            "current_funds",
            "estimated_income",
            "active_members",
            "panlist_size",
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df


def print_column_mapping_table(mapping: dict[str, str]) -> None:
    """Print a rich table showing the column mapping."""
    table = Table(title="Column Mapping", show_header=True, header_style="bold magenta")
    table.add_column("Canonical Name", style="cyan")
    table.add_column("Excel Column", style="green")

    for canonical, actual in sorted(mapping.items()):
        table.add_row(canonical, actual)

    console.print(table)
