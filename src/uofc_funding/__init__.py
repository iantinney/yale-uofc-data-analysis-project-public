"""UOFC funding transparency report generator.

Config-driven pipeline that converts raw committee funding spreadsheets into
a branded PowerPoint deck. Built for Yale's Undergraduate Organizations
Funding Committee; designed to retarget to other institutions via a YAML
schema (branding, sheet name patterns, column aliases).

Pipeline:

    Excel sheet ── DataLoader ──▶ normalized DataFrame + ValidationWarning[]
                                  (severity-tiered: error / warning)
                       │
                       ▼
                 FundingAnalyzer ──▶ FundingAnalysis (totals, ratios,
                                     category / age / Dwight Hall splits)
                       │
                       ▼
                 chart generators ──▶ PNG + CSV per visualization
                       │
                       ▼
                PresentationBuilder ──▶ branded .pptx

Submodules:
    config       Type-safe pydantic configuration with YAML loading and
                 case-insensitive prefix-based alias resolution.
    loader       Excel ingestion with severity-tiered validation and
                 graceful degradation on missing optional columns.
    analyzer     Defensive analytics: column-existence guards, divide-by-zero
                 protection, normalized categorical handling.
    charts       Subclass-per-chart generators inheriting from BaseChart.
    slides       python-pptx composition over typed layout positions.
    google_api   Three-state Google Sheets client (live API ▸ deterministic
                 mock ▸ degraded with explicit warnings).
    cli          Click + Rich orchestrator with progress tracking.

Example:

    from uofc_funding import Config, DataLoader, FundingAnalyzer
    from uofc_funding.charts import generate_all_charts
    from uofc_funding.slides import PresentationBuilder

    config = Config()
    result = DataLoader(config).load("funding_data.xlsx", round_number=1)
    analysis = FundingAnalyzer(config).analyze(result.round_data, result.overview_data)
    generate_all_charts(config, analysis, "output/charts")
    builder = PresentationBuilder(config, "output/charts", round_number=1)
    builder.build(analysis)
    builder.save("report.pptx")
"""

__version__ = "1.0.0"
__author__ = "Ian Tinney"

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
