# RiskPath 2.2 — Research Engine

Institutional multi-asset portfolio construction, risk analytics and historical-data evaluation. See the [project overview](../README.md) for the investment universe, mandate constraints and synthetic benchmark results.

## Quick start

Run from the repository root:

```bash
cd riskpath_quant
python -m pip install -r requirements.txt
python -m pytest -q
python institutional.py
```

The institutional experiment is deterministic and synthetic. It is useful for numerical validation, not evidence of actual investment performance.

## Historical market-data research

```bash
python -m pip install yfinance
python market_study.py
```

The historical study requests adjusted prices for the current 28-vehicle universe from Yahoo Finance via the unofficial yfinance client. It excludes incomplete months, uses common valid observations, and does not fill pre-inception or missing returns. It evaluates 36- and 60-month rolling estimation windows with at least 12 out-of-sample months, quarterly rebalancing and 15 bp modeled cost per gross dollar traded. Ineligible windows are reported; errors never trigger a synthetic fallback.

Alternatively, run the **RiskPath market data research** workflow in GitHub Actions. Actual network retrieval and end-to-end historical performance have not yet been verified. Follow the data provider's terms and keep raw downloaded returns out of public commits.

The local market study writes aggregate metrics, data-coverage records, package versions, an input SHA-256 fingerprint and explicit success/failure status under the ignored directory `market_study_local/`. No real liability series is supplied by the market-data runner.

### External data and liabilities

```bash
python institutional.py --returns-csv monthly_returns.csv --out external_results
python institutional.py --returns-csv monthly_returns.csv --liability-csv liabilities.csv --out external_results
```

Use a date index with consecutive monthly decimal simple returns and the following columns in exact order:

```text
BIL,VTI,IWM,QQQ,VTV,VEA,VWO,SHY,IEF,TLT,TIP,BNDX,LQD,HYG,EMB,BKLN,GLD,DBC,VNQ,IGF,DBMF,KMLM,BTAL,QAI,UUP,TAIL,PSP,BIZD
```

The institutional runner requires more than 60 monthly observations. The optional liability file must contain an aligned date index and a `liability_return` column. The runner does not independently verify external data provenance. The funding-ratio model is stylized and excludes contributions, payouts and actuarial cash flows.

## Model specification

All mandate-constrained models are fully invested and long-only at the vehicle level. Sleeve limits and an 18% noncash position cap apply at each rebalance. Underlying funds may use derivatives, shorting or leverage.

| Model | Objective |
|---|---|
| Policy portfolio | Fixed sleeve reference weights |
| 60/40 | VTI/IEF benchmark, exempt from mandate constraints |
| Minimum variance | Minimize portfolio variance |
| Mean-variance utility | Trade off expected return and variance |
| Group risk budgeting | Minimize deviation from target sleeve risk contributions |
| CVaR | Minimize empirical 95% tail loss |
| Liability-aware | Minimize variance of asset-minus-liability returns |

Annualized covariance uses 20% diagonal shrinkage and a small ridge. Estimated returns are shrunk 75% toward within-sleeve means. The risk-budget objective allows signed contributions and is solved locally. Empirical CVaR with limited monthly observations is statistically unstable.

## Files and outputs

| File | Description |
|---|---|
| [institutional.py](institutional.py) | Investment mandates, optimization, backtesting, funding ratio and stress tests |
| [market_study.py](market_study.py) | Historical data study and provenance |
| [download_returns.py](download_returns.py) | Market data alignment and validation |
| [institutional_research.md](institutional_research.md) | Mathematical methods and synthetic research findings |
| [institutional_outputs/metrics.csv](institutional_outputs/metrics.csv) | Synthetic portfolio comparison |
| [institutional_outputs/stress.csv](institutional_outputs/stress.csv) | Prescribed synthetic sleeve shocks |
| [institutional_outputs/metadata.json](institutional_outputs/metadata.json) | Synthetic experiment configuration |
| [test_institutional.py](test_institutional.py) | Institutional model validation |
| [test_engine.py](test_engine.py) | Baseline model validation |

Running the institutional experiment also generates allocation, risk contribution and monthly net-return files locally. Earlier baseline experiments remain available in [the original research note](research.md), `engine.py` and `run.py` for reproducibility; they are not the current institutional benchmark.

## Interpretation

The selected universe is not a point-in-time investment universe. Common inception dates, fund selection bias, covariance estimation error, simplified execution costs and fund-level exposures limit conclusions. Listed private-market vehicles are not direct private asset investments. The current release does not claim verified historical performance or production readiness.

## Personal allocation

The browser's Personal mode uses [personal.py](personal.py). It minimizes `0.5 * lambda * w' S w - mu' w` with the same shrunk estimates as the institutional engine. The effective score is the smaller of the user score and the illustrative horizon ceiling: 30 (1 year), 50 (3 years), 70 (5 years), 100 (10+ years). Lambda decreases geometrically from 1000 to 0.5 as effective score increases. Fixed long-only constraints cap noncash individual targets at 25%, equity at 80%, rates at 85%, credit, real assets and diversifiers each at 35%, and listed private-market proxies at 10%; cash may reach 100%. These are assumptions rather than a calibrated suitability framework. Higher scores target a lower variance penalty; realized risk and forecast percentiles are not guaranteed to move monotonically. [Tests](test_personal.py) cover feasibility, horizon mapping and modeled volatility ordering on a synthetic sample.
