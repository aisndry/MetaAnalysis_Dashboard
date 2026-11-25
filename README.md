# Meta Ads Analysis Dashboard

Interactive Meta Ads performance dashboard built with **Python, Streamlit, Pandas and Plotly**.

> **Note:** All data in this project is randomly generated sample data (fictional brands) created for portfolio purposes. It does not represent any real client or campaign.

## Features

- **KPI cards** with % change vs. the previous period (Impressions, Reach, Frequency, CPM, Link Clicks, CTR, Cost/Link Click, Amount Spent)
- **Timeline** combining daily link clicks (bars) with impressions and spend (lines)
- **Campaign table** with in-cell data bars and period-over-period change
- **Device performance** donut chart and Mobile vs. Computer summary
- **State performance** map and table, plus a "Top performing state" panel
- **Sidebar filters** for date range, campaign, platform and province

## Tech stack

Python · Streamlit · Pandas · NumPy · Plotly

## Run locally

```bash
pip install -r requirements.txt
streamlit run meta_ads_dashboard.py
```

## Using your own data

Replace `load_data()` in `meta_ads_dashboard.py` with your own source (CSV, Meta Marketing API, BigQuery, etc.). The dataframe needs these columns:

`date, campaign, platform, state, impressions, reach, clicks, spend`

## Metric definitions

| Metric | Formula |
|---|---|
| CTR | clicks / impressions |
| CPM | spend / impressions × 1000 |
| CPC (cost per link click) | spend / clicks |
| Frequency | impressions / reach |

## Inspiration

Layout inspired by the Meta Ads dashboard template by Kodalogic, re-implemented from scratch in Python.
