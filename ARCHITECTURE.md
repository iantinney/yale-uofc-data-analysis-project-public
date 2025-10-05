# Architecture

One-page design notes. Read alongside the module docstrings.

## Pipeline

```
   Excel workbook
         │
         ▼
   ┌──────────────┐    column aliases     ┌───────────────┐
   │  DataLoader  │ ◀──────────────────── │   Config      │
   └──────┬───────┘    (case-insensitive  │  (pydantic +  │
          │             exact + prefix)   │     YAML)     │
          │ LoadResult                    └───────────────┘
          │   ├── round_data (normalized DataFrame)
          │   ├── overview_data
          │   ├── column_mapping       ── shown by --show-mapping
          │   └── warnings: [ValidationWarning] (severity-tiered)
          ▼
   ┌────────────────┐
   │ FundingAnalyzer│   defensive: column-existence guards,
   └──────┬─────────┘   divide-by-zero protection, normalized
          │             categorical handling
          │ FundingAnalysis (totals, ratios, per-category /
          │   per-age / per-Dwight-Hall splits, top orgs)
          ▼
   ┌────────────────┐                     ┌───────────────────┐
   │ chart builders │ ◀── BaseChart ────▶ │  styling utils    │
   │ (pie/bar/table)│     subclasses      │  (wrap_text, etc) │
   └──────┬─────────┘                     └───────────────────┘
          │  PNG + CSV per visualization
          ▼
   ┌──────────────────────┐                ┌────────────────┐
   │ PresentationBuilder  │ ◀── layouts ── │ slide positions│
   │ (python-pptx)        │   typed coords │ in layouts.py  │
   └──────┬───────────────┘                └────────────────┘
          ▼
       .pptx
```

Optional sidecar — Google Sheets expense data:

```
                                ┌──────────────┐
                                │GoogleSheets  │
                                │   Client     │
                                └──────┬───────┘
   creds present? ─── yes ──▶  live googleapiclient call
                                  │
                  failure ───────▶ degraded (warning + empty data)
                                  │
   creds absent? ──── yes ──▶  deterministic mock (seeded)
```

## Design decisions worth knowing

**1. Severity-tiered validation, partial reports.** The loader emits
`ValidationWarning(severity="error" | "warning", message=..., details=...)`.
Required-column misses are errors and halt the pipeline; optional-column
misses are warnings and just skip the related visualization. Committee
sheets drop optional columns between rounds — a partial deck is more
useful than a hard failure.

**2. Config is the source of truth for column names.** Analyzer and chart
code reference canonical names (`organization_name`, `amount_requested`).
The alias resolver in `Config.resolve_column` translates them against
actual Excel headers via case-insensitive exact match first, then prefix
match (so committee question-form headers like "Is your organization a
Dwight Hall group? (member or provisional, but not outreach group)"
still resolve to `dwight_hall`).

**3. Mock Google Sheets is first-class.** Three modes: live API, deterministic
seeded mock (for demos / CI), degraded (credentials present but the call
failed → empty data with explicit warning). The mock is not a stub — it
generates plausible category breakdowns so the full
loader → analyzer → charts → slides path runs end-to-end with zero
external dependencies.

**4. One chart = one file.** `charts/bar_charts.py`, `charts/pie_charts.py`,
`charts/tables.py` each contain subclasses of `BaseChart`. Adding a new
visualization is one new file + one import in `charts/__init__.py`. No
edits to existing code, no shared mutable state, no chart-registry
bookkeeping.

**5. Slide layout coordinates live in `slides/layouts.py`.** The
`PresentationBuilder` reads typed position constants and never embeds
EMU/inch literals. Retargeting the deck to a different brand template
or aspect ratio is a layouts-module swap.

**6. Defensive analytics over pretty analytics.** `FundingAnalyzer` checks
column existence before every section, protects against division by zero
on the funding ratio, and normalizes the Dwight Hall affiliation field
with case-insensitive substring matching ("Dwight Hall", "dwight hall
member", "DWIGHT HALL provisional" all count). The currency / percentage
/ integer formatters return `str(value)` on non-numeric input rather than
raising — the overview-table renderer walks every cell and must tolerate
mixed types.

## Retargeting to another institution

Three files to touch:

1. `config/your_school.yaml` — branding (name, colors, URL, logo),
   `sheets.round_decision_pattern`, and any new column aliases.
2. `src/uofc_funding/charts/` — add a chart class if you need one not
   already covered by pie/bar/table generators.
3. `src/uofc_funding/slides/layouts.py` — adjust slide coordinates if
   you're shipping a different brand template / aspect ratio.

Pass the new config to the CLI with `--config config/your_school.yaml`.
Nothing else changes.

## What is deliberately not here

* No web service / async layer. The tool runs once per funding round; a
  CLI is the right surface.
* No database. The Excel workbook is the source of truth; persisting
  intermediate state would add a sync problem the committee doesn't have.
* No fuzzy column matching beyond exact-case-insensitive + prefix. Fuzzy
  match makes false positives quiet, and false positives in a
  funding-numbers pipeline are the worst possible failure mode.
* No retry / backoff on the Google API. If a single fetch fails, we
  surface the warning and let the operator re-run; the alternative is a
  silent stale-data report.
