# RiskPath  
**Visual Portfolio Forecasting Engine**

RiskPath is a lightweight portfolio analytics and forecasting engine that transforms a user’s **risk tolerance**, **investment horizon**, and **capital plan** into an intuitive, forward-looking portfolio allocation and return outlook.

It is designed to feel like a simplified institutional investment tool:
> You input how much risk you can take and how long you want to invest, and RiskPath shows you what your future portfolio could look like.

---

## What Problem Does RiskPath Solve?

Most portfolio tools:
- Only show historical backtests
- Or are too technical for real users

RiskPath focuses on one simple but powerful question:

> **“Given my risk tolerance and time horizon, what does my future portfolio most likely look like?”**

It emphasizes **decision support**, not unrealistic prediction.

---

## Core Features

- Risk-based portfolio construction  
- Real-world ETF universe (not textbook assets)  
- Forward-looking Monte Carlo portfolio simulation  
- Percentage-based return forecasts  
- Simple, intuitive visualization  
- Designed for easy extension to Web UI  

---

## Asset Universe (ETF Pool)

| Ticker | Asset Class | Description |
|------|------------|------------|
| BIL | Cash | 1–3 Month Treasury Bills (Risk-free proxy) |
| IEF | Bonds | 7–10 Year US Treasury |
| TLT | Bonds | 20+ Year US Treasury |
| LQD | Bonds | Investment Grade Corporate Bonds |
| TIP | Bonds | Inflation-Protected Bonds |
| SPY | Equity | S&P 500 |
| QQQ | Equity | Nasdaq 100 (Growth/Tech) |
| EFA | Equity | Developed Markets ex-US |
| EEM | Equity | Emerging Markets |
| GLD | Alternative | Gold (Inflation / crisis hedge) |
| VNQ | Real Assets | US Real Estate (REITs) |

---

## What the Output Looks Like

RiskPath generates:

- Portfolio Allocation Pie Chart  
- Forward-looking Portfolio Growth Forecast  
- Percentage Return Distribution  
- Risk bands (best / median / worst scenarios)

All results are **future projections**, not historical backtests.

---

## How It Works

1. User inputs:
   - Risk tolerance (0–100)
   - Investment horizon (years)
   - Initial capital
   - Monthly contribution (optional)

2. System:
   - Builds ETF portfolio aligned with risk profile
   - Estimates expected return & volatility
   - Simulates thousands of future paths using Monte Carlo

3. Output:
   - Portfolio weights
   - Expected percentage return range
   - Risk visualization
   - Simple financial interpretation

---

## Run in Google Colab (Recommended)

1. Open Google Colab  
2. Upload the notebook:
RiskPath.ipynb
3. Install dependencies:
```python
!pip install numpy pandas matplotlib yfinance scipy
```
4. Run all cells from top to bottom

5. Enter your risk tolerance and horizon when prompted


---

## Design Philosophy

Financial rigor without academic heaviness

Product thinking over formulas

Institutional logic with consumer usability

RiskPath is not a trading bot.
It is a portfolio decision engine.

---

## Roadmap

Planned improvements:

Web interface (Streamlit / React)

User profiles & presets

PDF portfolio reports

Factor exposure visualization

Scenario stress testing (crash / inflation / rate hike)

---

## Author

Built by Yunhao Wan
Finance · Data · Product Engineering

---

## 
RiskPath — Your risk defines your future path.
