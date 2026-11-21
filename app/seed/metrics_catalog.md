# Metrics catalog

This is the canonical vocabulary for metrics used across ingestion, API, and UI. `metric_key` is the stable identifier stored in `MetricDefinition` and `FundamentalFact`; the UI labels and formats are driven from the same registry.

**Direction** indicates whether a higher (`high`) or lower (`low`) value is "better" for composite ranking. **Nulls** are never stored as zero and are excluded from rankings.

## Valuation

| metric_key | Label | Formula / source | Unit | Direction |
| --- | --- | --- | --- | --- |
| `market_cap` | Market cap | price × shares outstanding | currency | high |
| `enterprise_value` | Enterprise value | market cap + total debt − cash | currency | high |
| `pe_ratio` | P/E (TTM) | price / trailing EPS | ratio | low |
| `forward_pe` | Forward P/E | price / estimated forward EPS | ratio | low |
| `forward_eps` | Forward EPS (estimate) | analyst forward EPS estimate | currency | high |
| `peg_ratio` | PEG | P/E / earnings growth rate | ratio | low |
| `price_to_sales` | P/S | market cap / revenue (TTM) | ratio | low |
| `price_to_book` | P/B | market cap / book value | ratio | low |
| `ev_to_ebitda` | EV/EBITDA | enterprise value / EBITDA | ratio | low |
| `ev_to_sales` | EV/Sales | enterprise value / revenue | ratio | low |

## Profitability

| metric_key | Label | Formula / source | Unit | Direction |
| --- | --- | --- | --- | --- |
| `ebitda` | EBITDA | operating income + D&A (derived when not reported) | currency | high |
| `ebitda_margin` | EBITDA margin | EBITDA / revenue | percent | high |
| `gross_margin` | Gross margin | gross profit / revenue | percent | high |
| `net_margin` | Net margin | net income / revenue | percent | high |
| `eps_ttm` | EPS (TTM) | trailing twelve-month net income / diluted shares | currency | high |
| `roe` | Return on equity | net income / shareholder equity | percent | high |
| `roa` | Return on assets | net income / total assets | percent | high |
| `roic` | Return on invested capital | NOPAT / invested capital | percent | high |

## Growth

| metric_key | Label | Formula / source | Unit | Direction |
| --- | --- | --- | --- | --- |
| `revenue` | Revenue (TTM) | trailing twelve-month revenue | currency | high |
| `revenue_growth_yoy` | Revenue growth YoY | (rev TTM / rev prior TTM) − 1 | percent | high |
| `earnings_growth_yoy` | Earnings growth YoY | (EPS TTM / EPS prior TTM) − 1 | percent | high |
| `eps_growth_5y` | EPS growth (5y CAGR) | compounded annual EPS growth, 5 years | percent | high |
| `earnings_growth_estimate` | Earnings growth estimate | analyst forward earnings growth estimate | percent | high |

## Financial health

| metric_key | Label | Formula / source | Unit | Direction |
| --- | --- | --- | --- | --- |
| `free_cash_flow` | Free cash flow | operating cash flow − capex | currency | high |
| `debt_to_equity` | Debt / equity | total debt / shareholder equity | ratio | low |
| `current_ratio` | Current ratio | current assets / current liabilities | ratio | high |
| `interest_coverage` | Interest coverage | EBIT / interest expense | ratio | high |
| `cash_and_equivalents` | Cash & equivalents | balance sheet | currency | high |

## Dividends & market

| metric_key | Label | Formula / source | Unit | Direction |
| --- | --- | --- | --- | --- |
| `dividend_yield` | Dividend yield | annual dividend / price | percent | high |
| `payout_ratio` | Payout ratio | dividend / EPS | percent | low |
| `beta` | Beta | vs. market (provider-supplied) | ratio | neutral |
| `price` | Last price | latest close | currency | neutral |
| `fifty_two_week_high` | 52-week high | trailing 52w max close | currency | neutral |
| `fifty_two_week_low` | 52-week low | trailing 52w min close | currency | neutral |
| `last_daily_volume` | Last daily volume | volume reported on the latest quote | number | neutral |

## Descriptive (not scored)

| metric_key | Label | Notes |
| --- | --- | --- |
| `sector` | Sector | From company profile; used as a filter, not ranked |
| `industry` | Industry | From company profile; used as a filter, not ranked |
| `exchange` | Exchange | NYSE / NASDAQ / AMEX |
| `country` | Country | Enables global expansion |
| `currency` | Reporting currency | All monetary values are in this currency (no FX conversion in v1) |

## Conventions

- **TTM** = trailing twelve months. **YoY** = year over year. **CAGR** = compound annual growth rate.
- Ratios are stored as plain numbers (e.g. `18.5` for a P/E of 18.5); percentages are stored as fractions (e.g. `0.234` for 23.4%) and formatted in the UI.
- Derived metrics (e.g. `ebitda`, `ev_to_ebitda`) record their formula in `MetricDefinition.formula` and are flagged as derived in the detail view.
- When two providers disagree, prefer the authoritative source per metric (SEC for filed fundamentals, FMP/yfinance for quotes) and record `source` on each fact.
