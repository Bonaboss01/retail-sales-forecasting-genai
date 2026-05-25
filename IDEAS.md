# IDEAS — SunnyBest AI Retail Forecasting System
> Potential improvements, experiments, and future features

---

## Forecasting

- **Multi-week ahead forecasts** — current pipeline only generates 1 week ahead. Extend to 4-week rolling horizon so buyers can plan further out.
- **Retrain trigger** — automatically flag retraining when WAPE exceeds the 20% alert threshold in `14_model_monitoring.ipynb`.
- **Promotion-aware forecasting** — current v3 model doesn't use promo features (v4 does but underperforms). Investigate why v4's WAPE is worse; try feature selection to get the best of both.
- **Per-category models** — a single model for all categories (Mobile Phones, TVs, Accessories, etc.) may underfit niche categories. Try separate models per category.
- **Confidence intervals** — add prediction intervals (e.g. quantile regression or bootstrapping) so buyers know forecast uncertainty.
- **External signals** — incorporate payday cycles (month-end), public holidays (Nigeria), and local events into features.

---

## Stock-Out & Inventory

- **Real-time stockout alert** — connect `src/monitoring/rules.py` to a notification channel (email or Slack) when a stockout risk is detected.
- **Reorder point automation** — use inventory optimisation results from notebook 17 to auto-generate purchase orders.
- **Safety stock by store** — different stores have different lead times; model safety stock per store rather than globally.

---

## GenAI Assistant

- **Natural language forecast explanation** — "Why is product X predicted to sell more this week?" using LLM + context.
- **What-if scenarios** — "What happens to sales if we run a 15% promo on Tecno phones?" via structured prompting.
- **Weekly insight email** — auto-generate a short narrative summary of the week's forecast using the LLM, delivered via email every Saturday.
- **Voice interface** — expose the GenAI assistant via WhatsApp or a voice API for store managers without laptop access.

---

## Monitoring & Ops

- **Scheduled forecast run** — automate `generate_weekly_forecast.py` via a cron job or GitHub Actions every Saturday.
- **Drift detection** — track feature drift (e.g. lag features changing pattern) as an early warning before WAPE degrades.
- **Dashboard** — build a simple Streamlit or Metabase dashboard over `data/outputs/` for non-technical stakeholders.

---

## Data

- **Weather data integration** — real weather API (e.g. Open-Meteo) for Edo State to replace simulated weather features.
- **Competitor pricing** — scrape or source competitor prices as external signals.
- **Customer segmentation** — if customer-level data becomes available, build RFM segments to enrich demand signals.

---

## Deployment

- **Model versioning on S3** — store each model artefact in S3 with a timestamp; pull latest via registry at inference time.
- **CI/CD pipeline** — GitHub Actions to run tests and redeploy the FastAPI app on each merge to main.
- **A/B forecast testing** — run two model versions simultaneously and route a fraction of stores to each to compare live WAPE.
