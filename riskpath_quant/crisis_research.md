# Conditional crisis-path simulation

The forecast engine uses joint circular six-month return blocks, quarterly target rebalancing, modeled trading costs and a separate contribution-adjusted wealth process. The default web view enables a stress overlay. It is an illustrative sensitivity experiment, not an estimated probability of future crises. The Python function defaults to baseline for backward compatibility.

## Scenario design

| Mode | Assumption |
|---|---|
| Baseline | No additional shocks. Training blocks may already contain extreme returns. |
| Mixed | Four-state monthly Markov chain, starts in baseline. |
| Recession | Six months of additional stress from the first forecast month, followed by baseline. |
| Sudden shock | One initial jump month, five recession months, followed by baseline. |
| Persistent stress | Twelve months of added inflation and credit pressure, followed by baseline. |

State order: baseline, recession, persistent stress, sudden jump. Transition rows (source state) and columns (destination state) are:

| State | Baseline | Recession | Persistent | Jump |
|---|---:|---:|---:|---:|
| Baseline | 0.982 | 0.012 | 0.004 | 0.002 |
| Recession | 0.150 | 0.830 | 0.015 | 0.005 |
| Persistent | 0.080 | 0.025 | 0.890 | 0.005 |
| Jump | 0.150 | 0.800 | 0.050 | 0.000 |

The stress component adds state-specific log-return shifts and a shared standardized Student-t(5) factor, changing cross-asset dependence in active states. Explicit shifts and factor loadings are in [crisis.py](crisis.py); selected diversifiers have separate illustrative exposures. Shocked log returns are clipped to [-8,3] for numerical safety. These parameters are not calibrated to market data, and are not confidence bounds. Bootstrap observations can already include stress, so additional overlays can double-count downside. Some allocations can benefit from assumed hedge exposures; a crisis label does not guarantee a lower portfolio outcome. No endogenous asset allocation, recovery policy, liquidity execution model, or independent crisis probability estimate is implied.

## Outputs

- Terminal NAV loss share (contributions excluded).
- Share of paths with at least 20% peak-to-trough decline and median pathwise maximum drawdown.
- Average terminal net return among the worst ceil(1% of paths) outcomes, a signed tail-return measure (negative of loss-based ES99).
- Median of pathwise longest consecutive underwater durations, including censored/unrecovered periods at the horizon.
- Simulated shares of paths with an added crisis or jump; conditional on the assumed process, not real-world event probabilities.

The default 2,000 paths leave only 20 observations in the 1% tail; this measure is exploratory and sensitive to shock assumptions. Terminal loss is not proof of permanent capital impairment. The displayed 5th–95th percentile range is pointwise, not a simultaneous confidence band.

Reproduce with `python -m pytest -q`. Tests exercise state transitions, forced durations, positive gross returns, seeded repeatability, cash-flow separation and the baseline case.
