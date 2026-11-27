# RiskPath | Baseline Research Archive

Historical 11-asset numerical experiment, preserved for reproducibility. For the current 28-asset research engine, see [RiskPath 2.2](README.md) and the [institutional research note](institutional_research.md).

## Research question
How do long-only allocations designed to minimize variance or tail losses compare with equal-weight and 60/40 benchmarks when evaluated using strictly chronological estimation windows and trading costs?

## Mathematical specification
Let r_t be the vector of monthly simple asset returns. The feasible set is w_i >= 0 and sum(w)=1. Covariance estimate S = 0.75 sample_cov + 0.25 diag(sample_cov) + 1e-8 I; fixed shrinkage is used, not estimated Ledoit-Wolf shrinkage.

Minimum variance minimizes w' S w. Risk parity minimizes sum_i [w_i (S w)_i / (w' S w) - 1/n]^2, where the ratio is the fractional contribution to variance. CVaR uses the Rockafellar-Uryasev empirical formulation: minimize a + sum(u_t)/(0.05 m), subject to u_t >= -r_t'w - a, u_t >= 0, and the same budget and long-only constraints. No expected return target is imposed. The optimization may therefore favor cash-like assets.

At month t, use only months t-60 through t-1 to estimate weights; update quarterly. In non-rebalance months weights drift with asset performance. Gross traded notional fraction is sum_i |w_target,i - w_pretrade,i|; charge 10 bp per unit of that quantity, including initial entry. Net return = (1-cost)(1+gross return)-1. This is a simplified cost haircut rather than an exact self-financing execution model.

NAV compounds net returns with no external cash flows. Maximum drawdown includes initial NAV of one. Sharpe is sqrt(12) times mean monthly excess return over the synthetic BIL proxy divided by its sample standard deviation. Monthly ES95 is negative mean of the worst ceil(5% of observations) returns; a negative value denotes a gain even in the selected tail.

## Numerical design and results
Use 240 seeded artificial monthly observations from three correlated factor loadings, asset-specific noise and two predetermined adverse factor episodes. The dates and ETF symbols are labels, not a historical sample. First 60 months train the initial portfolio, leaving 180 for evaluation. Models, windows and cost assumptions are fixed for this experiment.

| Model | CAGR % | Vol % | Sharpe | Drawdown % | Monthly ES95 % | Annual gross turnover % |
|---|---:|---:|---:|---:|---:|---:|
| Equal | -3.047 | 9.164 | -0.547 | -62.857 | 6.077 | 23.493 |
| 60/40 | -3.544 | 9.411 | -0.586 | -64.205 | 6.156 | 19.577 |
| Min variance | 2.262 | 0.261 | -0.413 | -0.0078 | -0.031 | 7.198 |
| Risk parity | 1.579 | 1.509 | -0.498 | -6.207 | 0.812 | 14.210 |
| CVaR | 2.243 | 0.265 | -0.466 | -0.0078 | -0.023 | 8.084 |

Risk objectives reduce measured volatility in this artificial sample, but all models underperform the synthetic cash proxy on the reported excess Sharpe metric. Cash dominance is an expected possibility for unconstrained minimum-risk objectives. This is evidence that the code distinguishes risk reduction from excess return, not that one strategy is economically superior.

## Separate forward simulation
For a risk-parity allocation estimated on the last 60 months, 2,000 seeded ten-year paths resample six-month circular blocks jointly across assets. This preserves within-block contemporaneous dependence and short-run serial structure but does not model changing long-run regimes. Constant monthly weights are assumed without costs. The terminal NAV 5/50/95 percentiles are 0.9993/1.1778/1.3559. With $100,000 initial wealth and $500 monthly contributions (total paid in $160,000), terminal wealth quantiles are $160,108/$182,898/$206,174. Contributions are not counted as investment returns. Quantiles are conditional simulation summaries, not guarantees or calibrated forecast probabilities.

## Validation and limitations
The 14 local pytest cases check feasibility, initial allocation independence from later observations, weight drift, cost accounting, reproducible simulations, cash-flow separation, initial drawdown, invalid returns and minimum-variance/CVaR training objectives. Internal numerical testing is not independent validation. Synthetic results are sensitive to seed, shock design and factor loadings. Risk parity uses a local constrained optimizer; global optimality is not guaranteed. CVaR uses only three tail months per 60-month training sample and is statistically unstable. No verified historical dataset, cross-regime robustness test, cash allocation cap, expected return constraint, real transaction cost estimate or investor-specific risk profile has been validated.

## References
- Markowitz, H. (1952). Portfolio Selection. Journal of Finance 7(1), 77–91.
- Rockafellar, R. T., and Uryasev, S. (2000). Optimization of Conditional Value-at-Risk. Journal of Risk 2(3), 21–41.
- Maillard, S., Roncalli, T., and Teïletche, J. (2010). The Properties of Equally Weighted Risk Contribution Portfolios. Journal of Portfolio Management 36(4), 60–70.
- Politis, D. N., and Romano, J. P. (1992). A Circular Block-Resampling Procedure for Stationary Data. In Exploring the Limits of Bootstrap, 263–270.
