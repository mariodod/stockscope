# Future feature ideas

Ideas that were considered but are not implemented. They are ordered roughly by user value and by how well the current data supports them.

## Implemented already

- **Watchlist** — star companies in the screener; stored in the browser only.
- **CSV export** — download the full filtered and ranked screen (up to 5,000 rows) from the screener.

## Next candidates

| Idea | What it does | Prerequisites | Notes |
| --- | --- | --- | --- |
| Peer comparison | For a company, show the top and bottom five same-sector companies on the same metrics | None | Pure read of the existing API; a natural next section on the company detail page |
| Price-history backfill | Store several years of daily adjusted prices for each company | One ingestion job using yfinance history | Needed by any backtest; the current `quotes` table only fills going forward |
| Portfolio tracker | Record shares, cost basis and transactions; show value, unrealised P/L, allocation and contribution to return | A decision on accounts vs browser-local storage | Start browser-local like the watchlist; add sync only if needed |
| Returns simulator / backtester | Compare lump sum vs dollar-cost averaging, with and without dividend reinvestment, against a benchmark such as SPY | Price-history backfill | Report annualised return, total return and maximum drawdown; use adjusted prices so splits and dividends are handled |
| Dividend calendar | Upcoming ex-dividend and payment dates for watched or held companies | A provider with forward dividend data | FMP has some of this on paid tiers |
| Alerts | Notify when a metric crosses a threshold or a new filing appears | A delivery channel (email or push) | Needs an external service or credentials; not startable without that decision |
| Analyst-estimate fair value | Use forward EPS estimates and growth to show scenario valuations | A live `FMP_API_KEY` and confirmation of free-tier estimate coverage | The FMP adapter exists, but live quote data has not been verified |
| Sector heatmap | Visualise sector performance and valuation on one screen | Price history for period returns | Useful overview once price history exists |

## Suggested order

1. **Peer comparison** — no new data or infrastructure.
2. **Price-history backfill** — unlocks the simulator and the heatmap.
3. **Portfolio tracker** — browser-local first; revisit accounts only if cross-device sync becomes important.
4. **Returns simulator** — build after backfill so scenarios run on real prices.
5. **Alerts and analyst estimates** — require a delivery channel or a validated API key.

## Open decisions

- **Accounts:** saved screens and the watchlist deliberately avoid accounts. If portfolios need sync across devices, decide between accounts and an exported/imported file before adding auth.
- **Alert delivery:** email or push needs an external provider and credentials. No implementation should start until that choice is made.
- **Provider tier:** analyst estimates depend on how much FMP exposes on the free tier; validate with a real key before designing around them.
