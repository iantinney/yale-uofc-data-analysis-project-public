"""
Configuration models and loading utilities.

This module provides Pydantic models for validating configuration files
and utilities for resolving column aliases to actual Excel column names.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class BrandingConfig(BaseModel):
    """Branding settings for the generated reports."""
    
    organization_name: str = "Yale Undergraduate Organizations Funding Committee"
    short_name: str = "UOFC"
    website_url: str = "ycc.yale.edu/uofc"
    logo_path: str = "assets/uofcsubtitle.png"
    primary_color: str = "#00356B"
    secondary_color: str = "#4A90D9"
    accent_color: str = "#F2A900"


class SheetConfig(BaseModel):
    """Sheet naming configuration."""
    
    round_decision_pattern: str = "Round {round_number} Decision for Analysis"
    overview_sheet: str = "Overview"
    
    def get_round_sheet_name(self, round_number: int) -> str:
        """Generate the round decision sheet name for a given round number."""
        return self.round_decision_pattern.format(round_number=round_number)


class ChartPaletteConfig(BaseModel):
    """Color palette configuration for charts."""
    
    categorical: str = "tab10"
    sequential: str = "Blues"
    diverging: str = "RdYlGn"
    paired: str = "Paired"


class ChartFontConfig(BaseModel):
    """Font size configuration for charts."""
    
    title: int = 16
    axis_label: int = 12
    tick_label: int = 10
    legend: int = 10


class ChartConfig(BaseModel):
    """Chart generation configuration."""
    
    palettes: ChartPaletteConfig = Field(default_factory=ChartPaletteConfig)
    figure_sizes: dict[str, list[int]] = Field(default_factory=lambda: {
        "pie_chart": [8, 8],
        "bar_chart": [10, 6],
        "grouped_bar": [12, 6],
        "table": [8, 4],
    })
    dpi: int = 300
    fonts: ChartFontConfig = Field(default_factory=ChartFontConfig)


class SlideConfig(BaseModel):
    """PowerPoint slide configuration."""
    
    width_inches: float = 10.0
    height_inches: float = 7.5
    positions: dict[str, list[float]] = Field(default_factory=lambda: {
        "full_chart": [1.0, 1.0, 8.0, 6.0],
        "split_chart": [0.5, 1.0, 6.2, 6.0],
        "split_table": [6.7, 1.0, 2.8, 6.0],
        "pie_left": [0.5, 1.0, 4.5, 5.0],
        "bar_right": [5.0, 1.0, 4.5, 5.0],
        "table_left": [0.5, 5.2, 4.5, 2.0],
        "table_right": [5.0, 5.2, 4.5, 2.0],
        "centered_table": [2.75, 5.2, 4.5, 2.0],
        "header_logo": [8.0, 6.5, 2.0, 1.0],
        "title": [0.5, 0.2, 9.0, 0.5],
    })


class ValidationConfig(BaseModel):
    """Data validation settings."""
    
    required_columns: list[str] = Field(default_factory=lambda: [
        "organization_name",
        "organization_category", 
        "amount_requested",
        "amount_awarded",
    ])
    optional_columns: list[str] = Field(default_factory=lambda: [
        "organization_age",
        "active_members",
        "panlist_size",
        "dwight_hall",
        "current_funds",
        "estimated_income",
        "other_funding",
        "funding_ratio",
    ])
    min_rows: int = 1
    max_missing_percent: float = 50.0


class GoogleAPIConfig(BaseModel):
    """Google API configuration for expense sheet integration."""
    
    enabled: bool = False
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"
    scopes: list[str] = Field(default_factory=lambda: [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ])


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = "INFO"
    format: str = "rich"
    file: str | None = None
    
    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class Config(BaseModel):
    """
    Main configuration model.
    
    This model validates and provides access to all configuration settings
    for the UOFC Funding Transparency Report generator.
    """
    
    branding: BrandingConfig = Field(default_factory=BrandingConfig)
    sheets: SheetConfig = Field(default_factory=SheetConfig)
    column_aliases: dict[str, list[str]] = Field(default_factory=dict)
    overview_columns: dict[str, list[str]] = Field(default_factory=dict)
    charts: ChartConfig = Field(default_factory=ChartConfig)
    slides: SlideConfig = Field(default_factory=SlideConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    google_api: GoogleAPIConfig = Field(default_factory=GoogleAPIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    def resolve_column(self, canonical_name: str, available_columns: list[str]) -> str | None:
        """
        Resolve a canonical column name to an actual Excel column name.
        
        Args:
            canonical_name: The internal/canonical column name (e.g., "organization_name")
            available_columns: List of actual column names from the Excel file
            
        Returns:
            The matched column name from available_columns, or None if not found
        """
        aliases = self.column_aliases.get(canonical_name, [])
        
        # Normalize available columns for case-insensitive matching
        normalized_available = {col.lower().strip(): col for col in available_columns}
        
        for alias in aliases:
            alias_lower = alias.lower().strip()
            
            # Exact match (case-insensitive)
            if alias_lower in normalized_available:
                return normalized_available[alias_lower]
            
            # Prefix match for long column names (e.g., "Is your organization a Dwight Hall...")
            for norm_col, orig_col in normalized_available.items():
                if norm_col.startswith(alias_lower) or alias_lower.startswith(norm_col):
                    return orig_col
        
        return None
    
    def resolve_all_columns(
        self, 
        available_columns: list[str]
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """
        Resolve all configured columns against available Excel columns.
        
        Args:
            available_columns: List of actual column names from the Excel file
            
        Returns:
            Tuple of (resolved_mapping, missing_required, missing_optional)
            - resolved_mapping: Dict mapping canonical names to actual column names
            - missing_required: List of required columns that couldn't be resolved
            - missing_optional: List of optional columns that couldn't be resolved
        """
        resolved: dict[str, str] = {}
        missing_required: list[str] = []
        missing_optional: list[str] = []
        
        # Resolve required columns
        for canonical in self.validation.required_columns:
            actual = self.resolve_column(canonical, available_columns)
            if actual:
                resolved[canonical] = actual
            else:
                missing_required.append(canonical)
        
        # Resolve optional columns
        for canonical in self.validation.optional_columns:
            actual = self.resolve_column(canonical, available_columns)
            if actual:
                resolved[canonical] = actual
            else:
                missing_optional.append(canonical)
        
        return resolved, missing_required, missing_optional


def load_config(config_path: str | Path | None = None) -> Config:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file. If None, uses the default config.
        
    Returns:
        Validated Config object
    """
    if config_path is None:
        # Try to find default config in package or current directory
        possible_paths = [
            Path("config/default.yaml"),
            Path(__file__).parent.parent.parent / "config" / "default.yaml",
            Path(os.environ.get("UOFC_CONFIG", "")) if os.environ.get("UOFC_CONFIG") else None,
        ]
        
        for path in possible_paths:
            if path and path.exists():
                config_path = path
                break
        
        if config_path is None:
            # Return default config if no file found
            return Config()
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    
    return Config.model_validate(raw_config or {})


def get_default_config_path() -> Path:
    """Get the path to the default configuration file."""
    return Path(__file__).parent.parent.parent / "config" / "default.yaml"
