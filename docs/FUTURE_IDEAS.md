# Feature ideas

All ideas previously listed here are now implemented. This page records what shipped and the two substitutions made so no external credentials were needed.

## Delivered

| Idea | Where | Notes |
| --- | --- | --- |
| Peer comparison | Company detail page, `GET /api/v1/companies/{ticker}/peers` | Same-sector companies, closest market cap first |
| Price-history backfill | `python -m app.ingestion.runner --job history` | yfinance daily close and adjusted close, five years by default |
| Portfolio tracker | `/portfolio` | Browser-local holdings, market value, unrealised P/L and sector allocation |
| Returns simulator | `/simulator`, `POST /api/v1/simulate` | Lump sum or DCA, dividend reinvestment, benchmark, annualised return and max drawdown |
| Dividend calendar | `/dividends`, `GET /api/v1/dividends` | Expected ex-dividend and payment dates, filterable to watched/held tickers |
| Alerts | `/alerts` | Browser-local metric thresholds with in-app triggered status |
| Analyst-estimate fair value | Company detail page, `GET /api/v1/companies/{ticker}/fair-value` | Bear/base/bull scenarios from forward EPS and P/E multiples |
| Sector heatmap | `/heatmap`, `GET /api/v1/sector-performance` | Colored tiles by period return, clickable through to a filtered screen |

## Substitutions made

- **Alerts:** the original idea assumed email or push delivery and therefore needed an external service. Shipped as in-app alerts stored in the browser. External delivery can be added later without changing the threshold model.
- **Analyst estimates:** the original idea depended on a validated FMP key. Shipped using yfinance forward EPS and earnings-growth estimates, which are free and already part of the fundamentals job. Custom P/E multiples can be supplied to the fair-value endpoint.

## Decisions resolved

- **Accounts:** portfolios, watchlists and alerts stay browser-local, consistent with saved screens. No auth system was added.
- **Price history:** split-adjusted close is stored in `price` and split/dividend-adjusted close in `adjusted_close`. The simulator uses adjusted prices when dividend reinvestment is enabled.
- **Quote retention:** five years (`QUOTE_RETENTION_DAYS=1825`), matching the default backfill window.
