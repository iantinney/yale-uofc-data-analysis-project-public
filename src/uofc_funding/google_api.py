"""
Google API integration for expense sheet access.

This module provides integration with Google Sheets/Drive APIs to fetch
expense data from linked Google documents. When Google API is not configured,
it provides mock data for demonstration purposes.

SETUP INSTRUCTIONS (for full functionality):
============================================

1. Go to https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the Google Sheets API and Google Drive API
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as application type
   - Download the credentials JSON file
5. Save the credentials as `credentials.json` in your project root
6. Install the Google API dependencies:
   ```
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```
7. Set `google_api.enabled: true` in your config file
8. On first run, you'll be prompted to authorize access in your browser

NOTE: The production version of this project used Google API integration
to pull expense details from linked Google Sheets. This functionality has
been disabled in the public version for privacy reasons, but the mock
implementation demonstrates the intended behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console

if TYPE_CHECKING:
    from .config import Config

console = Console()


@dataclass
class ExpenseData:
    """Container for expense sheet data."""

    organization_name: str
    total_expenses: float
    categories: dict[str, float]
    line_items: list[dict[str, Any]]
    source_url: str | None = None
    is_mock: bool = False


class GoogleSheetsClient:
    """
    Client for accessing Google Sheets data.

    When Google API is not available/configured, provides mock data
    that demonstrates the expected behavior.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the Google Sheets client.

        Args:
            config: Configuration object with Google API settings
        """
        self.config = config
        self._service = None
        self._is_mock = not config.google_api.enabled

        if not self._is_mock:
            self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize the Google Sheets API service."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None
            token_path = Path(self.config.google_api.token_path)
            credentials_path = Path(self.config.google_api.credentials_path)

            # Load existing token
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(
                    str(token_path), self.config.google_api.scopes
                )

            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not credentials_path.exists():
                        console.print(
                            "[yellow]Warning:[/yellow] Google API credentials not found. "
                            "Using mock data."
                        )
                        self._is_mock = True
                        return

                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path), self.config.google_api.scopes
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(token_path, "w") as token:
                    token.write(creds.to_json())

            self._service = build("sheets", "v4", credentials=creds)
            console.print("[green]✓[/green] Google Sheets API initialized")

        except ImportError:
            console.print(
                "[yellow]Warning:[/yellow] Google API libraries not installed. "
                "Using mock data. Install with: pip install uofc-funding-transparency[google]"
            )
            self._is_mock = True
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Failed to initialize Google API: {e}")
            self._is_mock = True

    def fetch_expense_data(self, sheet_url: str, organization_name: str) -> ExpenseData | None:
        """
        Fetch expense data from a Google Sheet.

        Args:
            sheet_url: URL to the Google Sheet
            organization_name: Name of the organization

        Returns:
            ExpenseData object, or None if fetch failed
        """
        if self._is_mock:
            return self._generate_mock_data(organization_name, sheet_url)

        # Extract sheet ID from URL
        sheet_id = self._extract_sheet_id(sheet_url)
        if not sheet_id:
            console.print(f"[yellow]Warning:[/yellow] Invalid sheet URL: {sheet_url}")
            return None

        try:
            # Fetch data from the sheet
            result = (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=sheet_id,
                    range="A:Z",  # Fetch all columns
                )
                .execute()
            )

            values = result.get("values", [])
            return self._parse_expense_data(values, organization_name, sheet_url)

        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Failed to fetch sheet: {e}")
            return self._generate_mock_data(organization_name, sheet_url)

    def _extract_sheet_id(self, url: str) -> str | None:
        """Extract the sheet ID from a Google Sheets URL."""
        # Match patterns like:
        # https://docs.google.com/spreadsheets/d/SHEET_ID/edit
        # https://docs.google.com/spreadsheets/d/SHEET_ID
        pattern = r"/spreadsheets/d/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def _parse_expense_data(
        self, values: list[list[str]], organization_name: str, source_url: str
    ) -> ExpenseData:
        """Parse raw sheet values into ExpenseData."""
        categories: dict[str, float] = {}
        line_items: list[dict[str, Any]] = []
        total = 0.0

        if not values:
            return ExpenseData(
                organization_name=organization_name,
                total_expenses=0.0,
                categories={},
                line_items=[],
                source_url=source_url,
                is_mock=False,
            )

        # First row is headers; skip past it when summing line items.
        for row in values[1:]:
            if len(row) >= 2:
                try:
                    category = str(row[0])
                    amount = float(str(row[1]).replace("$", "").replace(",", ""))

                    categories[category] = categories.get(category, 0) + amount
                    total += amount

                    line_items.append(
                        {
                            "category": category,
                            "amount": amount,
                            "description": row[2] if len(row) > 2 else "",
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return ExpenseData(
            organization_name=organization_name,
            total_expenses=total,
            categories=categories,
            line_items=line_items,
            source_url=source_url,
            is_mock=False,
        )

    def _generate_mock_data(
        self, organization_name: str, source_url: str | None = None
    ) -> ExpenseData:
        """
        Generate mock expense data for demonstration.

        This provides realistic-looking data that demonstrates what the
        Google API integration would return.
        """
        import random

        # Seed based on org name for consistency
        random.seed(hash(organization_name) % 2**32)

        # Common expense categories for student organizations
        possible_categories = [
            "Events & Programming",
            "Food & Refreshments",
            "Marketing & Publicity",
            "Equipment & Supplies",
            "Travel & Transportation",
            "Guest Speakers",
            "Competition Fees",
            "Software & Subscriptions",
            "Printing & Materials",
            "Miscellaneous",
        ]

        # Select 3-6 random categories
        num_categories = random.randint(3, 6)
        selected_categories = random.sample(possible_categories, num_categories)

        # Generate amounts
        categories = {}
        line_items = []
        total = 0.0

        for category in selected_categories:
            amount = round(random.uniform(50, 2000), 2)
            categories[category] = amount
            total += amount

            line_items.append(
                {
                    "category": category,
                    "amount": amount,
                    "description": f"[Mock] {category} expenses",
                }
            )

        return ExpenseData(
            organization_name=organization_name,
            total_expenses=round(total, 2),
            categories=categories,
            line_items=line_items,
            source_url=source_url,
            is_mock=True,
        )

    @property
    def is_mock_mode(self) -> bool:
        """Check if client is running in mock mode."""
        return self._is_mock


def fetch_all_expense_data(
    config: Config, organizations: list[dict[str, str]]
) -> dict[str, ExpenseData]:
    """
    Fetch expense data for all organizations.

    Args:
        config: Configuration object
        organizations: List of dicts with 'name' and 'expense_sheet' keys

    Returns:
        Dictionary mapping organization names to ExpenseData
    """
    client = GoogleSheetsClient(config)
    results: dict[str, ExpenseData] = {}

    for org in organizations:
        name = org.get("name", "Unknown")
        url = org.get("expense_sheet")

        if url and url.lower() not in ("", "nan", "none", "null"):
            data = client.fetch_expense_data(url, name)
            if data:
                results[name] = data

    if client.is_mock_mode and results:
        console.print(
            f"[dim]Note: Generated mock expense data for {len(results)} organizations. "
            "Enable Google API for real data.[/dim]"
        )

    return results
