# UOFC Funding Transparency Report Generator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Automated transparency report generation for the Yale Undergraduate Organizational Funding Committee (UOFC). Transforms Excel funding data into professional PowerPoint presentations with charts, tables, and year-over-year comparisons.

## Features

- **Flexible Column Mapping**: Handles varying Excel column names through configurable aliases
- **Comprehensive Analysis**: Category distributions, age group analysis, funding source breakdowns
- **Professional Charts**: Pie charts, grouped bar charts, and formatted tables
- **PowerPoint Generation**: Complete slide decks with Yale branding
- **Data Validation**: Warns about missing data, proceeds gracefully
- **Rich CLI**: Colored output, progress tracking, detailed logging

## Quick Start

```bash
# Install
pip install -e .

# Generate a report
uofc-report ExampleFundingSheet.xlsx 1

# With custom output path
uofc-report ExampleFundingSheet.xlsx 2 --output round2_report.pptx

# Validate data without generating
uofc-report validate ExampleFundingSheet.xlsx
```

## Installation

### From Source

```bash
git clone https://github.com/iantinney/yale-uofc-data-analysis-project-public.git
cd yale-uofc-data-analysis-project-public
pip install -e .
```

### With Development Dependencies

```bash
pip install -e ".[dev]"
```

### With Google API Support (Optional)

```bash
pip install -e ".[google]"
```

## Usage

### Basic Usage

```bash
# Generate Round 1 report
uofc-report ExampleFundingSheet.xlsx 1

# Generate Round 2 report with verbose output
uofc-report ExampleFundingSheet.xlsx 2 --verbose

# Show column mapping for debugging
uofc-report ExampleFundingSheet.xlsx 1 --show-mapping
```

### Python API

```python
from uofc_funding import Config, DataLoader, FundingAnalyzer
from uofc_funding.charts import generate_all_charts
from uofc_funding.slides import PresentationBuilder

# Load configuration
config = Config()

# Load and validate data
loader = DataLoader(config)
result = loader.load("ExampleFundingSheet.xlsx", round_number=1)

if not result.is_valid:
    print("Data validation failed!")
    for warning in result.warnings:
        print(f"  {warning}")
    exit(1)

# Analyze data
analyzer = FundingAnalyzer(config)
analysis = analyzer.analyze(result.round_data, result.overview_data)

# Generate charts
charts = generate_all_charts(config, analysis, "output/charts")

# Build presentation
builder = PresentationBuilder(config, "output/charts", round_number=1)
builder.build(analysis)
builder.save("transparency_report.pptx")
```

## Excel File Format

The generator expects an Excel file with the following structure:

### Required Sheet: `Round {N} Decision for Analysis`

| Column | Description | Required |
|--------|-------------|----------|
| Organization Name | Name of the student organization | ✓ |
| Organization Category | Category (e.g., "Academic", "Arts") | ✓ |
| Amount Requested | Funding amount requested | ✓ |
| Amount Awarded | Funding amount awarded | ✓ |
| Organization Age | Age group (e.g., "2-5 Years") | Optional |
| Number of Active Members | Member count | Optional |
| Other Funding Sources | External funding description | Optional |

### Optional Sheet: `Overview`

Year-over-year comparison metrics including budget totals, organization counts, and funding ratios.

### Column Name Flexibility

The generator supports multiple column name variations. For example, all of these will work:
- "Organization Name", "Org Name", "Name"
- "Amount Requested", "Requested", "Funding Requested"
- "Dwight Hall Group?", "Is your organization a Dwight Hall group?..."

See `config/default.yaml` for the full list of supported aliases.

## Configuration

### Custom Configuration

Create a custom config file:

```yaml
# my_config.yaml
branding:
  organization_name: "My University Funding Committee"
  website_url: "funding.myuniversity.edu"
  primary_color: "#003366"

column_aliases:
  organization_name:
    - "Organization Name"
    - "Club Name"
    - "Group Name"
```

Use it:

```bash
uofc-report ExampleFundingSheet.xlsx 1 --config my_config.yaml
```

### Extending for Other Institutions

This project was built for Yale's UOFC but is designed to be adaptable:

1. **Branding**: Update `branding` section in config with your colors and URLs
2. **Column Names**: Add your institution's column names to `column_aliases`
3. **Sheets**: Modify `sheets.round_decision_pattern` for your naming convention
4. **Charts**: Extend chart generators in `src/uofc_funding/charts/`

Example for a different institution:

```yaml
branding:
  organization_name: "Stanford Student Organizations Funding"
  short_name: "SSOF"
  website_url: "funding.stanford.edu"
  primary_color: "#8C1515"  # Stanford Cardinal

sheets:
  round_decision_pattern: "Funding Cycle {round_number}"
  overview_sheet: "Summary"

column_aliases:
  organization_name:
    - "Organization"
    - "Student Group"
    - "RSO Name"
```

## Architecture

```
uofc-funding-transparency/
├── src/uofc_funding/
│   ├── __init__.py          # Package exports
│   ├── cli.py               # Command-line interface (Click + Rich)
│   ├── config.py            # Pydantic configuration models
│   ├── loader.py            # Excel loading and validation
│   ├── analyzer.py          # Data analysis and statistics
│   ├── google_api.py        # Google Sheets integration (with mock)
│   ├── charts/
│   │   ├── base.py          # Base chart class and utilities
│   │   ├── pie_charts.py    # Pie chart generators
│   │   ├── bar_charts.py    # Bar chart generators
│   │   └── tables.py        # Table image and CSV generators
│   └── slides/
│       ├── layouts.py       # Slide position definitions
│       └── builder.py       # PowerPoint presentation builder
├── config/
│   └── default.yaml         # Default configuration with aliases
├── tests/
│   ├── fixtures/            # Test data files
│   ├── test_loader.py       # Loader tests
│   └── test_analyzer.py     # Analyzer tests
└── pyproject.toml           # Modern Python packaging
```

### Design Decisions

1. **Column Aliases over Fuzzy Matching**: We chose explicit alias lists rather than fuzzy string matching. This prevents false matches and makes debugging easier—you know exactly which names are supported.

2. **Skip & Warn for Missing Data**: Rather than failing on missing optional columns, we skip related visualizations and warn. This produces useful partial reports even with incomplete data.

3. **Modular Chart Generators**: Each chart type is a separate class inheriting from `BaseChart`. Adding new visualizations requires only adding a new file—no changes to existing code.

4. **Pydantic Configuration**: Type-safe configuration with validation. Catches config errors early with helpful messages.

5. **Mock Google API**: The Google Sheets integration generates realistic mock data when credentials aren't available. This allows the full pipeline to run for demos/testing.

## Google Sheets Integration

The production version integrated with Google Sheets to fetch expense data from linked documents. This has been disabled in the public version for privacy, but the infrastructure remains.

### Enabling Google API (Optional)

1. Create a Google Cloud project at https://console.cloud.google.com/
2. Enable Google Sheets API and Google Drive API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download credentials as `credentials.json`
5. Install dependencies: `pip install -e ".[google]"`
6. Enable in config:
   ```yaml
   google_api:
     enabled: true
   ```
7. On first run, authorize in browser when prompted

Without Google API configured, the system generates mock expense data demonstrating the intended functionality.

## Development

### Setup

```bash
# Clone and install with dev dependencies
git clone https://github.com/iantinney/yale-uofc-data-analysis-project-public.git
cd yale-uofc-data-analysis-project-public
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=uofc_funding --cov-report=html

# Run specific test file
pytest tests/test_loader.py -v
```

### Code Quality

```bash
# Lint
ruff check src/

# Format
ruff format src/

# Type check
mypy src/
```

## Generated Output

The generator produces:

1. **PowerPoint Presentation** (`transparency_report_roundN.pptx`)
   - Title slide with branding
   - Overview/rubric comparison
   - Category distribution (pie + table)
   - Average funding by category (bar chart)
   - Age group analysis (pie + bar + tables)
   - Dwight Hall group comparison
   - Other funding sources analysis
   - Top organizations summary

2. **Chart Images** (`funding_graphs/`)
   - PNG files for each visualization
   - CSV exports of table data

## Troubleshooting

### "Required column 'X' not found"

Your Excel file uses a column name not in the alias list. Either:
- Rename the column in Excel to match a known alias
- Add your column name to `column_aliases` in the config

### "Sheet 'Round 1 Decision for Analysis' not found"

Your Excel file uses different sheet naming. Update `sheets.round_decision_pattern` in config:
```yaml
sheets:
  round_decision_pattern: "Your Sheet Name Pattern {round_number}"
```

### Charts look wrong or missing

Run with `--verbose` to see which data is available:
```bash
uofc-report ExampleFundingSheet.xlsx 1 --verbose --show-mapping
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

Built for the Yale College Council's Undergraduate Organizations Funding Committee to increase transparency in student organization funding decisions.
