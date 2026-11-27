# Institutional Multi-Asset Allocation: Mandate Constraints and Liability Risk

## Research question
How do asset-class allocation limits and different optimization objectives affect risk-adjusted performance and funding risk in a diversified liquid investment portfolio? This is an independently designed numerical study, not a replication of any institution's holdings or proprietary model.

## Design
The 28 liquid securities represent cash, public equity, rates, credit, real assets, diversifiers and listed private-market proxies. The last category consists of listed vehicles, not direct private-fund NAVs. The two illustrative mandates differ in allocation bands and risk budgets. Long-only vehicle weights sum to one, with an 18% noncash single-position cap; underlying fund exposures can include derivatives, shorts or leverage. The unrestricted 60/40 reference is exempt from mandate limits. Bounds apply at rebalance dates, not continuously.

The synthetic sample contains 240 monthly observations from a seeded six-factor simulation, with 180 out-of-sample months. Its artificial dates and ticker labels do not indicate actual historical market returns. The simulation incorporates equity, duration, credit, inflation, trend and USD factors and two imposed adverse episodes. Every quarter, models estimate parameters from the preceding 60 months only, then hold and drift through subsequent months. Returns include a modeled 15 bp cost per gross dollar traded, including initial entry. These costs are not measured execution costs.

## Optimization
Let w be asset weights, G the sleeve-membership matrix, and S the annualized covariance matrix. The feasible set is sum(w)=1, 0 <= w <= asset caps, and sleeve lower bounds <= Gw <= sleeve upper bounds. S is 80% sample covariance plus 20% diagonal covariance with a small ridge. Annual arithmetic expected returns are shrunk 75% toward within-sleeve means.

- Minimum variance: minimize w' S w.
- Mean-variance utility: minimize (5/2) w' S w - mu' w.
- Group risk budgeting: minimize squared deviation of G[w * (Sw)/(w'Sw)] from target variance-contribution shares. Signed contributions can be negative; exact budget matching is not assured under the constraints.
- CVaR: minimize empirical 95% tail loss using the Rockafellar–Uryasev linear program. Its 60-month estimation window has very few tail observations.
- Liability-aware allocation: minimize the variance of the difference between asset and liability returns, using a jointly shrunk covariance estimate. The stylized funding ratio starts at 90% and compounds by (1 + net asset return)/(1 + liability return). There are no contributions, payouts or actuarial revaluations.

## Results (synthetic; not investment performance)
| Mandate/model | CAGR | Volatility | Sharpe | Maximum drawdown |
|---|---:|---:|---:|---:|
| 60/40 reference | 4.35% | 7.41% | 0.30 | -22.33% |
| Pension policy | 5.56% | 7.59% | 0.44 | -20.66% |
| Pension min variance | 4.65% | 2.63% | 0.87 | -4.94% |
| Pension utility | 6.01% | 6.28% | 0.59 | -11.49% |
| Pension risk budget | 4.99% | 5.83% | 0.47 | -15.40% |
| Pension CVaR | 4.89% | 2.99% | 0.83 | -6.33% |
| Pension liability-aware | 2.70% | 5.07% | 0.09 | -18.69% |
| Liquid multi policy | 6.01% | 6.04% | 0.61 | -14.63% |
| Liquid multi min variance | 4.66% | 2.04% | 1.13 | -1.52% |
| Liquid multi utility | 6.17% | 5.71% | 0.67 | -10.28% |
| Liquid multi risk budget | 5.33% | 5.14% | 0.59 | -12.62% |
| Liquid multi CVaR | 5.16% | 2.43% | 1.13 | -1.77% |

The liability-aware allocation reduced annualized volatility of the asset-minus-liability return from 14.02% (pension policy) to 9.24%, but had lower asset CAGR and ending funding ratio. Its minimum modeled funding ratio improved from 71.89% to 75.99%. This illustrates the difference between minimizing asset risk and liability-relative risk. Constrained minimum variance limited average cash weights to 11.97% and 19.96% in the pension and liquid multi mandates respectively. These outputs are particular to this simulation and the assumed constraints.

Four illustrative sleeve shock vectors are applied to allocations estimated from the final 60 months. They are instantaneous mark-to-market scenarios, not historical event reconstructions, probabilistic forecasts or bounds on potential loss.

## Validation and limitations
29 local tests passed across the legacy and institutional research modules. They cover optimization feasibility, chronology, covariance, funding arithmetic and missing-data treatment. Public ETF history ingestion is optional; actual data retrieval and historical model performance were not validated in this experiment. Common inception dates, current-universe selection bias, revisions, overlapping exposures, transaction costs and alternative-fund leverage may affect results. There is no derivatives position-level risk, private-asset valuation model, financing, margin, redemption modeling, cash-flow liability schedule, or independent institutional benchmark. All parameter values and policy targets are illustrative. Numerical results are not investment recommendations.

## Reproduction
Install requirements, run `python -m pytest -q`, then `python institutional.py` from this directory. The runner generates metrics, sleeve allocations, risk contributions, monthly returns and stress results. The checked-in metrics and stress files are deterministic synthetic outputs.

## References
- Markowitz, H. (1952). Portfolio Selection. Journal of Finance.
- Rockafellar, R. T., and Uryasev, S. (2000). Optimization of Conditional Value-at-Risk. Journal of Risk.
- Maillard, S., Roncalli, T., and Teïletche, J. (2010). The Properties of Equally Weighted Risk Contribution Portfolios. Journal of Portfolio Management.
- CalPERS, Investment Strategy and Asset Allocation / asset-liability management public materials.
- CPP Investments, Annual Report, public investment framework.
- AQR, public research on risk parity and diversification.
