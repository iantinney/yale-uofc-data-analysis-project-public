"""
Tests for the data loader module.
"""

from pathlib import Path

import pytest

from uofc_funding import Config, DataLoader, LoadResult
from uofc_funding.config import load_config


@pytest.fixture
def config() -> Config:
    """Create a test configuration from the default YAML file."""

    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    return load_config(config_path)


@pytest.fixture
def mock_excel_path() -> Path:
    """Get path to mock Excel file."""
    return Path(__file__).parent / "fixtures" / "mock_data.xlsx"


class TestDataLoader:
    """Tests for DataLoader class."""

    def test_load_valid_file(self, config: Config, mock_excel_path: Path) -> None:
        """Test loading a valid Excel file."""
        loader = DataLoader(config)
        result = loader.load(mock_excel_path, round_number=1)

        assert result.is_valid
        assert result.round_data is not None
        assert len(result.round_data) == 5

    def test_load_discovers_sheets(self, config: Config, mock_excel_path: Path) -> None:
        """Test that loader discovers available sheets."""
        loader = DataLoader(config)
        result = loader.load(mock_excel_path, round_number=1)

        assert "Overview" in result.sheet_names
        assert "Round 1 Decision for Analysis" in result.sheet_names

    def test_load_resolves_columns(self, config: Config, mock_excel_path: Path) -> None:
        """Test that column aliases are resolved."""
        loader = DataLoader(config)
        result = loader.load(mock_excel_path, round_number=1)

        # Check that required columns were mapped
        assert "organization_name" in result.column_mapping
        assert "amount_requested" in result.column_mapping
        assert "amount_awarded" in result.column_mapping

    def test_load_normalizes_columns(self, config: Config, mock_excel_path: Path) -> None:
        """Test that DataFrame columns are normalized to canonical names."""
        loader = DataLoader(config)
        result = loader.load(mock_excel_path, round_number=1)

        # Check that DataFrame uses canonical names
        assert "organization_name" in result.round_data.columns
        assert "amount_requested" in result.round_data.columns

    def test_load_missing_file(self, config: Config) -> None:
        """Test loading a non-existent file."""
        loader = DataLoader(config)
        result = loader.load("nonexistent.xlsx", round_number=1)

        assert not result.is_valid
        assert result.has_errors

    def test_load_wrong_round(self, config: Config, mock_excel_path: Path) -> None:
        """Test loading with wrong round number."""
        loader = DataLoader(config)
        result = loader.load(mock_excel_path, round_number=99)

        # Should fail because Round 99 sheet doesn't exist
        assert not result.is_valid

    def test_load_overview_data(self, config: Config, mock_excel_path: Path) -> None:
        """Test that overview data is loaded."""
        loader = DataLoader(config)
        result = loader.load(mock_excel_path, round_number=1)

        assert result.overview_data is not None
        assert len(result.overview_data) > 0


class TestLoadResult:
    """Tests for LoadResult class."""

    def test_is_valid_with_data(self) -> None:
        """Test is_valid with valid data."""
        import pandas as pd

        result = LoadResult(round_data=pd.DataFrame({"a": [1, 2, 3]}), warnings=[])

        assert result.is_valid

    def test_is_valid_without_data(self) -> None:
        """Test is_valid without data."""
        result = LoadResult()

        assert not result.is_valid

    def test_has_errors(self) -> None:
        """Test has_errors property."""
        from uofc_funding.loader import ValidationWarning

        result = LoadResult(warnings=[ValidationWarning(severity="error", message="Test error")])

        assert result.has_errors

    def test_no_errors(self) -> None:
        """Test has_errors when only warnings."""
        from uofc_funding.loader import ValidationWarning

        result = LoadResult(
            warnings=[ValidationWarning(severity="warning", message="Test warning")]
        )

        assert not result.has_errors


class TestColumnAliasResolution:
    """Tests for the column alias resolver in Config.

    Real committee spreadsheets contain typos, casing drift, and verbose
    question-form headers. The resolver must accept all of these.
    """

    def test_case_insensitive_exact_match(self, config: Config) -> None:
        """Alias matching ignores case differences."""
        available = ["ORGANIZATION NAME", "Amount Requested", "amount awarded"]
        resolved = config.resolve_column("organization_name", available)
        assert resolved == "ORGANIZATION NAME"

    def test_prefix_match_for_verbose_header(self, config: Config) -> None:
        """Long question-form headers match via prefix."""
        # Committee sheets sometimes append clarifying text to the question.
        available = [
            "Is your organization a Dwight Hall group? (yes/no, see policy doc)",
        ]
        resolved = config.resolve_column("dwight_hall", available)
        assert resolved == available[0]

    def test_missing_alias_returns_none(self, config: Config) -> None:
        """Unknown column name resolves to None (caller decides severity)."""
        available = ["Totally Unrelated Column"]
        resolved = config.resolve_column("organization_name", available)
        assert resolved is None

    def test_resolve_all_columns_separates_required_and_optional(self, config: Config) -> None:
        """resolve_all_columns reports required and optional misses separately."""
        # A sheet missing the required "Amount Requested" column should land
        # the column in missing_required, not missing_optional.
        available = ["Organization Name", "Amount Awarded"]
        _resolved, missing_required, missing_optional = config.resolve_all_columns(available)

        assert "amount_requested" in missing_required
        # Optional columns also absent must not be promoted to errors.
        assert "amount_requested" not in missing_optional
