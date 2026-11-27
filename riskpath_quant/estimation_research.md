# Multi-horizon estimation and market-data coverage

The web workbench uses adaptive estimation by default. This is an explicit research heuristic, not an empirically optimized choice.

- Eligible trailing horizons: 36, 60, 120 and 240 months; include the longest available sample, capped at 240, if it falls between these horizons.
- Blend weights 15%, 25%, 35%, 25% in ascending horizon order, renormalized over available windows. For 70 observations this yields 36/60/70 months with weights 20%/33.33%/46.67%.
- Annualized arithmetic means and shrinkage covariance estimates are blended separately. Within each window, diagonal shrinkage is min(0.65,max(0.20,p/(n-1))). Add a small diagonal ridge; retain within-sleeve mean shrinkage.
- For the CVaR objective and forward block resampling, use the longest selected window instead of duplicating historical rows. The empirical tail sample remains small.
- Adaptive walk-forward starts after 36 completed observations and uses only data available prior to each test observation. Fixed windows require their full sample. A minimum of 12 out-of-sample months is required. Compare windows over matched test dates before selecting a model; the market study also shows coverage for each method.
- The current 28-vehicle universe includes funds with short live histories. Never backfill pre-inception observations, silently substitute another asset, or fill missing monthly returns. A distinct longer-history proxy/factor universe is a separate research design and has not been implemented.

## Browser data

Real market is the default input mode, but no result is computed without an actual dataset. The client requests monthly bars using the Twelve Data `time_series` endpoint with `adjust=all`, a user-provided personal API key and free-tier paced batches. Adjusted prices are converted to consecutive common monthly returns, and incomplete months are removed. API credentials and raw data remain in the browser; no key is committed, no automatic paid upgrade, and no raw market dataset is redistributed. Live retrieval requires a working key and provider access. Coverage and provider are displayed on each result. CSV imports remain available, and synthetic demonstrations are an explicit opt-in. The separate yfinance downloader is also available; verify data rights and actual total-return adjustment with provider documentation. Crisis parameters remain illustrative.

The new moments and window mechanics are covered by numerical tests. No claim of improved real-market performance or calibrated crisis probability is made.
