# RiskPath 2.0 | Portfolio Construction and Risk Analytics

Research prototype for comparing long-only multi-asset allocation rules with chronological out-of-sample simulation, explicit transaction costs and joint block resampling.

## Reproduce
Python 3.11+ recommended.

```bash
cd riskpath_quant
python -m pip install -r requirements.txt
python -m pytest -q
python run.py
```

For an external return dataset: `python run.py --returns-csv monthly_returns.csv --out external_results`. First CSV column contains chronological monthly dates (one observation per consecutive month); subsequent columns must be BIL, IEF, TLT, LQD, TIP, SPY, QQQ, EFA, EEM, GLD, VNQ in that order. Returns must be finite decimal simple total returns greater than -1, with at least 61 observations. The runner does not verify data provenance. Outputs include monthly net returns, allocations, metrics and simulation quantiles. No paid APIs are required.

## Methodology
- Equal-weight and SPY/IEF 60/40 benchmarks.
- Long-only fully invested minimum variance with 25% diagonal covariance shrinkage and a small ridge.
- Risk parity minimizes squared deviations from equal variance contributions.
- Empirical 95% CVaR minimized using linear programming.
- Rolling 60-month estimation windows, quarterly rebalancing, weight drift and 10 bp per gross dollar traded, including initial entry.
- Cash proxy excess-return Sharpe, annualized volatility, CAGR, drawdown, monthly empirical tail loss and annual gross turnover.
- Circular joint six-month block bootstrap, with a fixed seed; investment NAV is independent of external contributions.

## Synthetic benchmark
240 artificial monthly observations, 180 evaluated out of sample; all labels are proxies and are not actual ETF performance.

| Method | CAGR | Ann. vol | Sharpe (excess BIL) | Max drawdown |
|---|---:|---:|---:|---:|
| Equal | -3.05% | 9.16% | -0.547 | -62.86% |
| 60/40 | -3.54% | 9.41% | -0.586 | -64.21% |
| Minimum variance | 2.26% | 0.26% | -0.413 | -0.008% |
| Risk parity | 1.58% | 1.51% | -0.498 | -6.21% |
| CVaR | 2.24% | 0.27% | -0.466 | -0.008% |

All five models have negative cash-relative Sharpe in this particular artificial sample. The minimum-risk methods are cash-like and do not establish an investment advantage. See [research note](research.md).

## Scope
Synthetic numerical experiment only; no live feed, verified historical returns, investment recommendation or claim of performance. No leverage, shorting, taxes, spread model, market impact, estimation uncertainty or investor risk-budget calibration. The prospective bootstrap illustration holds weights constant monthly and excludes trading costs; the backtest rebalances quarterly and includes modeled costs. Neither establishes future returns.
