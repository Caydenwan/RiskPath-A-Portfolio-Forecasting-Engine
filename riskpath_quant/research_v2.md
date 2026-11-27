# Research v2 — November 2026

## Implemented
- Forecast blocks: choose each block's trailing estimation window using the reported blend weights, then uniformly select a contiguous six-month block inside it (no wrap when using the configured mixture). Historical returns are not recentered to match shrunken means or covariances; forecasts are empirical conditional scenarios, not calibrated predictive distributions.
- Cash flows: quarterly rebalance to targets, apply gross traded-notional costs, then mark holdings; month-end deposits buy target weights after their own execution fee. Investment NAV is time-weighted before deposit-specific execution costs; wealth includes the net deposit. Flow-driven changes in drift weights can change subsequent investment NAV.
- Correlation shrinkage: Ledoit–Wolf intensity on standardized nonconstant return columns, then rescale using sample marginal volatilities. A tiny ridge stabilizes covariance. The fixed multi-window blend is not selected out of sample.
- Goals: target in today's dollars, constant inflation, fixed nominal deposits, terminal goal probability, real median wealth and frictionless required return.
- Mean–variance frontier: same constraints and shrunken means as the optimizer; feasible solver points only, with out-of-constraint benchmark markers. Expected arithmetic return is not forecast CAGR.
- Validation: 36/60/120/240 month fixed and adaptive estimators evaluated only on a common test period (minimum 12 test months), with equal weight, 60/40 and US equity proxy benchmarks, quarterly rebalancing and costs. It is descriptive and not a held-out model-selection result; no claim of superiority.
- Scenario comparisons: baseline, recession, persistent stress and sudden jump on the same allocation with common random numbers; each uses 2,000 paths. Added shocks are illustrative and can overlap historical stress.
- Rule-based insights, 2,000/10,000 paths, default baseline without added shocks.

## Limits / next steps
The current common universe has limited joint history; the public TSP sample is a dated snapshot. Long-run factor proxies, historical crisis reconstruction, true prospective forecast calibration, and higher path-count convergence studies are not implemented. Reported conditional probabilities are not actual market odds. Real-data results depend on the user's private snapshot, and must not be published without appropriate authorization. Model is educational research, not a personal suitability assessment. Cloud credential and monthly refresh architecture is unchanged.
