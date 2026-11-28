# Public research data and model

Public Research is a distinct, no-key Personal forecast mode. It uses published historical net monthly returns of the five core U.S. Thrift Savings Plan funds. These are government retirement-plan funds, not ETFs or recommendations to buy them. G Fund holds special government securities, F Fund tracks broad US bonds, C/S/I cover US large-cap, US completion and international equities.

## Source and coverage

81 consecutive monthly observations, December 2019 through August 2026. The checked-in `web/public-tsp-returns.csv` transcribes the five fund columns (not benchmark index columns) of the following USPS Postal Bulletin government publications, converts percentages to decimal monthly returns and uses calendar month-end dates. These are dated government-published numerical facts; no Twelve Data prices or API keys are distributed.

- [2020 bulletin 22562](https://about.usps.com/postal-bulletin/2020/pb22562/html/po_001.htm): Dec 2019–Oct 2020.
- [2021 bulletin 22585](https://about.usps.com/postal-bulletin/2021/pb22585/html/po_001.htm): Nov 2020–Oct 2021.
- [2022 bulletin 22611](https://about.usps.com/postal-bulletin/2022/pb22611/html/po_001.htm): Nov 2021–Oct 2022.
- [2023 bulletin 22640](https://about.usps.com/postal-bulletin/2023/pb22640/html/po_001.htm): Dec 2022–Nov 2023, plus [22635](https://about.usps.com/postal-bulletin/2023/pb22635/html/po_001.htm) for Nov 2022.
- [2024 bulletin 22665](https://about.usps.com/postal-bulletin/2024/pb22665/html/po_001.htm): Dec 2023–Nov 2024.
- [2025 bulletin 22690](https://about.usps.com/postal-bulletin/2025/pb22690/html/po_001.htm): Dec 2024–Sep 2025.
- [2026 bulletin 22712](https://about.usps.com/postal-bulletin/2026/pb22712/html/po_001.htm): Oct 2025–Aug 2026.

Values are as published and may be revised. May/June 2022 include the TSP system transition's unusual reporting periods (see [FRTIB June 2022 review](https://www.frtib.gov/pdf/minutes/2022/July/Att2-June-2022-Performance-Review.pdf)). A direct full-history TSP CSV request was blocked; the snapshot is not a live feed, and monthly automatic updates are not enabled. A longer official history can replace it after validation. No pre-inception data are invented. The 2025 monthly values are from the monthly table; annual summaries are not used, and discrepancies require later reconciliation.

## Research design

The five-fund model has an independent long-only optimization using the same risk-aversion and horizon mapping, adaptive covariance and mean estimation, 80% total equity ceiling, individual caps, quarterly rebalancing, joint block simulation and separate contribution-adjusted wealth. Crisis overlays use the corresponding government-security, broad-bond and equity sleeve assumptions; these are illustrative and not calibrated. This is a different asset universe from the 28-ETF model; results and weights are not directly interchangeable.

## Private advanced mode

The server's private 28-ETF snapshot is restricted to the authorized owner. Sign in once with the configured owner token; an HttpOnly, Secure, same-origin cookie persists for 30 days. The Twelve Data server credential never goes to the browser. Public visitors use the government-published TSP returns without a key. Vendor history is refreshed only by the authenticated server schedule; an owner can still import an existing private CSV. No public redistribution or paid service is enabled.

Personal and Institutional can alternatively use their own licensed CSV or the optional direct personal API connection. The optional device storage for that direct connection is not encrypted by the application and can be read by same-origin scripts. It is disabled by default and can be cleared. It never stores the owner's server API credential. Use only on a trusted private browser.
