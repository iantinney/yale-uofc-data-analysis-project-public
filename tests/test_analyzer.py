"""
Tests for the data analyzer module.
"""

from pathlib import Path

import pandas as pd
import pytest

from uofc_funding import Config, DataLoader, FundingAnalyzer


@pytest.fixture
def config() -> Config:
    """Create a test configuration from the default YAML file."""
    from uofc_funding.config import load_config

    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    return load_config(config_path)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create sample funding data."""
    return pd.DataFrame(
        {
            "organization_name": ["Org A", "Org B", "Org C", "Org D"],
            "organization_category": ["Academic", "Arts", "Academic", "Sports"],
            "organization_age": ["2-5 Years", "10+ Years", "2-5 Years", "0-1 Year"],
            "amount_requested": [1000, 2000, 1500, 3000],
            "amount_awarded": [800, 1500, 1200, 2000],
            "other_funding": [None, "Dwight Hall", "Department", None],
        }
    )


@pytest.fixture
def mock_excel_path() -> Path:
    """Get path to mock Excel file."""
    return Path(__file__).parent / "fixtures" / "mock_data.xlsx"


class TestFundingAnalyzer:
    """Tests for FundingAnalyzer class."""

    def test_analyze_basic_stats(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test basic statistics computation."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.total_organizations == 4
        assert analysis.total_requested == 7500
        assert analysis.total_awarded == 5500

    def test_analyze_averages(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test average computation."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.average_requested == 1875.0  # 7500 / 4
        assert analysis.average_awarded == 1375.0  # 5500 / 4

    def test_analyze_funding_ratio(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test funding ratio computation."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        expected_ratio = 5500 / 7500
        assert abs(analysis.overall_funding_ratio - expected_ratio) < 0.001

    def test_analyze_category_counts(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test category distribution."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.category_counts is not None
        assert analysis.category_counts["Academic"] == 2
        assert analysis.category_counts["Arts"] == 1
        assert analysis.category_counts["Sports"] == 1

    def test_analyze_top_categories(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test top categories computation."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.top_categories is not None
        assert "category" in analysis.top_categories.columns
        assert "count" in analysis.top_categories.columns
        assert "percentage" in analysis.top_categories.columns

    def test_analyze_age_groups(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test age group analysis."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.age_group_counts is not None
        assert analysis.age_group_counts["2-5 Years"] == 2

    def test_analyze_dwight_hall(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test Dwight Hall analysis."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.dwight_hall_counts is not None
        # Only Org B has "Dwight Hall" in other_funding
        assert analysis.dwight_hall_counts.get("Dwight Hall Group", 0) == 1

    def test_analyze_other_funding(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test other funding analysis."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.other_funding_counts is not None
        # Org B and C have other funding
        assert analysis.other_funding_counts.get("Yes", 0) == 2

    def test_analyze_top_organizations(self, config: Config, sample_data: pd.DataFrame) -> None:
        """Test top organizations extraction."""
        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(sample_data)

        assert analysis.top_organizations is not None
        # Should be sorted by amount_requested descending
        assert analysis.top_organizations.iloc[0]["organization_name"] == "Org D"

    def test_analyze_with_real_data(self, config: Config, mock_excel_path: Path) -> None:
        """Test analysis with real mock data file."""
        loader = DataLoader(config)
        result = loader.load(mock_excel_path, round_number=1)

        assert result.is_valid

        analyzer = FundingAnalyzer(config)
        analysis = analyzer.analyze(result.round_data, result.overview_data)

        assert analysis.total_organizations == 5
        assert analysis.top_organizations is not None
        assert len(analysis.top_organizations) == 5


class TestAnalysisFormatting:
    """Tests for formatting utilities in analyzer."""

    def test_format_currency(self) -> None:
        """Test currency formatting."""
        assert FundingAnalyzer._format_currency(1234.56) == "$1,234.56"
        assert FundingAnalyzer._format_currency(1000000) == "$1,000,000.00"

    def test_format_percentage(self) -> None:
        """Test percentage formatting."""
        assert FundingAnalyzer._format_percentage(0.5) == "50.00%"
        assert FundingAnalyzer._format_percentage(75.5) == "75.50%"

    def test_format_integer(self) -> None:
        """Test integer formatting."""
        assert FundingAnalyzer._format_integer(1234) == "1,234"
        assert FundingAnalyzer._format_integer(1234.7) == "1,234"

    def test_format_currency_non_numeric_returns_passthrough(self) -> None:
        """Non-numeric input is returned as-is rather than raising."""
        # _format_currency is called with mixed dataframe cells in
        # _format_overview; non-numeric cells must not blow up the pipeline.
        assert FundingAnalyzer._format_currency("N/A") == "N/A"


class TestAnalyzerEdgeCases:
    """Edge cases the analyzer must tolerate without crashing.

    These cover the real-world failure modes the loader's severity-tiered
    validation lets through (partial data, all-null optional columns, etc.).
    """

    def test_zero_total_requested_does_not_divide_by_zero(self, config: Config) -> None:
        """Funding ratio stays at its default when no money was requested."""
        df = pd.DataFrame(
            {
                "organization_name": ["A", "B"],
                "organization_category": ["Academic", "Arts"],
                "amount_requested": [0, 0],
                "amount_awarded": [0, 0],
            }
        )
        analysis = FundingAnalyzer(config).analyze(df)

        assert analysis.total_requested == 0
        # ratio is left at its dataclass default rather than raising ZeroDivisionError
        assert analysis.overall_funding_ratio == 0.0

    def test_missing_optional_columns_skip_cleanly(self, config: Config) -> None:
        """Optional columns absent → related sections stay None, no crash."""
        df = pd.DataFrame(
            {
                "organization_name": ["A", "B"],
                "amount_requested": [100, 200],
                "amount_awarded": [100, 150],
            }
        )
        analysis = FundingAnalyzer(config).analyze(df)

        assert analysis.total_organizations == 2
        assert analysis.category_counts is None
        assert analysis.age_group_counts is None
        assert analysis.dwight_hall_counts is None

    def test_null_optional_values_treated_as_no_other_funding(self, config: Config) -> None:
        """All-null other_funding column → zero Dwight Hall affiliations."""
        df = pd.DataFrame(
            {
                "organization_name": ["A", "B", "C"],
                "organization_category": ["Academic", "Arts", "Sports"],
                "amount_requested": [100, 200, 300],
                "amount_awarded": [100, 150, 200],
                "other_funding": [None, None, None],
            }
        )
        analysis = FundingAnalyzer(config).analyze(df)

        assert analysis.dwight_hall_counts is not None
        assert analysis.dwight_hall_counts.get("Dwight Hall Group", 0) == 0

    def test_dwight_hall_string_matching_is_case_insensitive(self, config: Config) -> None:
        """Real spreadsheets use "dwight hall", "DWIGHT HALL", etc."""
        df = pd.DataFrame(
            {
                "organization_name": ["A", "B", "C", "D"],
                "organization_category": ["Arts"] * 4,
                "amount_requested": [100] * 4,
                "amount_awarded": [100] * 4,
                "other_funding": [
                    "Dwight Hall",
                    "dwight hall member",
                    "DWIGHT HALL provisional",
                    "Department of Music",
                ],
            }
        )
        analysis = FundingAnalyzer(config).analyze(df)

        assert analysis.dwight_hall_counts is not None
        assert analysis.dwight_hall_counts.get("Dwight Hall Group", 0) == 3
