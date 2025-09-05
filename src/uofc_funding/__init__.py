"""
UOFC Funding Transparency Report Generator.

This package provides tools for generating transparency reports from
Yale Undergraduate Organizations Funding Committee data.

Main components:
- config: Configuration management with column aliases
- loader: Excel data loading and validation
- analyzer: Funding data analysis and statistics
- charts: Chart and table generation
- slides: PowerPoint presentation building
- google_api: Google Sheets integration (with mock support)
- cli: Command-line interface

Example usage:
    from uofc_funding import Config, DataLoader, FundingAnalyzer
    from uofc_funding.charts import generate_all_charts
    from uofc_funding.slides import PresentationBuilder
    
    # Load configuration and data
    config = Config()
    loader = DataLoader(config)
    result = loader.load("funding_data.xlsx", round_number=1)
    
    # Analyze data
    analyzer = FundingAnalyzer(config)
    analysis = analyzer.analyze(result.round_data, result.overview_data)
    
    # Generate outputs
    charts = generate_all_charts(config, analysis, "output/charts")
    
    builder = PresentationBuilder(config, "output/charts", round_number=1)
    builder.build(analysis)
    builder.save("report.pptx")
"""

__version__ = "1.0.0"
__author__ = "Yale UOF Committee"

from .analyzer import FundingAnalysis, FundingAnalyzer
from .config import Config, load_config
from .loader import DataLoader, LoadResult

__all__ = [
    "Config",
    "DataLoader",
    "FundingAnalysis",
    "FundingAnalyzer",
    "LoadResult",
    "load_config",
]
