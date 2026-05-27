# SunnyBest AI Retail Forecasting System — Project Plan
**Last updated:** 2026-05-27
**Author:** Bonaventure Osuide

---

## Project Overview

SunnyBest Telecommunications operates electronics and telecom retail stores across **7 locations** in Edo State, Nigeria:
Benin, Ekpoma, Auchi, Irrua, Igueben, Agenebode, and Ogwa.

This project delivers a **production-grade AI platform** that:
- Forecasts weekly product-level sales per store
- Predicts and prevents stockouts before they occur
- Models promotion uplift and price elasticity
- Optimises pricing and inventory decisions
- Provides natural-language business insights via a GenAI assistant
- Exposes all capabilities through a REST API with a Streamlit dashboard

---

## System Architecture

```
Supabase (PostgreSQL)
        │
        ▼
Data Pipeline (src/data/)
        │
        ▼
Feature Engineering  ──►  Model Training (src/models/)
                                  │
                                  ▼
                          Model Registry (models/model_registry.csv)
                                  │
                                  ▼
                    Weekly Forecast Script (src/forecasting/)
                                  │
                          ┌───────┴────────┐
                          ▼                ▼
              weekly_forecasts.csv    Monitoring (src/monitoring/)
                          │                │
                          ▼                ▼
               Notebook 15             Notebook 14
            (What will sell?)      (Was model right?)
                          │
                          ▼
              FastAPI (src/api/)  ◄──  GenAI Assistant (src/genai/)
                          │
                          ▼
              Streamlit Dashboard (src/dashboards/)
                          │
                          ▼
                   Docker + AWS
```

---

## Workstream Status

| # | Workstream | Status |
|---|-----------|--------|
| 1 | Data Engineering & Pipeline | ✅ Complete |
| 2 | Exploratory Data Analysis | ✅ Complete |
| 3 | Forecasting Models | ✅ Complete — actively maintained |
| 4 | Stockout Prediction | ✅ Complete |
| 5 | Price Elasticity & Pricing Optimisation | ✅ Complete |
| 6 | Promotion Uplift (Causal) | ✅ Complete |
| 7 | Model Monitoring Pipeline | ✅ Complete |
| 8 | Demand Sensing | 🔄 In Progress |
| 9 | Inventory Optimisation | 🔄 In Progress |
| 10 | GenAI Insight Assistant | 🔄 In Progress |
| 11 | FastAPI + Deployment | 🔄 In Progress |
| 12 | Streamlit Dashboard | 🔄 In Progress |
| 13 | Documentation & Presentation | ⬜ Not Started |

---

## Notebooks

| Notebook | Purpose | Status |
|----------|---------|--------|
| 01_data_understanding.ipynb | EDA — sales, stores, products, categories | ✅ Done |
| 01_Bona_data_analysis.ipynb | Extended personal EDA | ✅ Done |
| 02_baseline_forecast.ipynb | Naïve, moving average, exponential smoothing baselines | ✅ Done |
| 03_ml_forecasting.ipynb | LinearReg, RandomForest, XGBoost, LightGBM | ✅ Done |
| 04_stockout_classification.ipynb | Binary stockout classifier | ✅ Done |
| 05_promo_uplift_causal.ipynb | Causal promo uplift (DiD / regression) | ✅ Done |
| 06_genai_rag_experiments.ipynb | RAG pipeline experiments | ✅ Done |
| 07_price_elasticity.ipynb | Price elasticity modelling per category | ✅ Done |
| 08_pricing_optimization.ipynb | Profit/revenue pricing optimisation | ✅ Done |
| 09_spark_data_processing.ipynb | Spark-based aggregation & ETL | ✅ Done |
| 10_validate_data.ipynb | Data validation & sanity checks | ✅ Done |
| 11_store_stockout_analysis.ipynb | Store-level stockout patterns | ✅ Done |
| 12_product_stockout_analysis.ipynb | Product-level stockout deep dive | ✅ Done |
| 13_timing_drivers_stockout.ipynb | Timing & drivers of stockout events | ✅ Done |
| 14_model_monitoring.ipynb | Forecast vs actuals — WAPE tracking | ✅ Done — run every Saturday |
| 15_weekly_forecast_analysis.ipynb | Weekly forecast visualisation (store, category, heatmap) | ✅ Done — run after each forecast |
| 16_demand_sensing.ipynb | Short-term demand signal detection | 🔄 Recent — review outputs |
| 17_inventory_optimisation.ipynb | Safety stock, reorder points, inventory optimisation | 🔄 Recent — review outputs |

---

## Data Pipeline

### Source
- **Database:** Supabase (PostgreSQL) — `aws-1-eu-central-1.pooler.supabase.com`
- **Key tables:** `core.fact_sales`, `core.dim_stores`, `core.dim_products`, `core.dim_calendar`
- **Connection module:** `src/data/db_connection.py` — all scripts must use this

### Pipeline Scripts (run in order when refreshing data)

```
Step 1: src/data/make_weekly_dataset.py          → data/processed/weekly_sales.csv
Step 2: src/data/make_weekly_dataset_v2.py        → data/processed/weekly_sales_v2.csv
Step 3: src/data/make_weekly_dataset_v3_calendar.py → data/processed/weekly_sales_v3_calendar.csv
Step 4: src/data/make_weekly_dataset_v4_promotions.py → data/processed/weekly_sales_v4_promotions.csv
```

Run with: `PYTHONPATH=. python3 src/data/<script_name>.py`

### Current Data Coverage
- **Range:** 2020-12-28 → 2026-05-04
- **Rows:** 235,200 (7 stores × 120 products × ~280 weeks)
- **Last refreshed:** 2026-05-26

---

## Models

### Model Registry (`models/model_registry.csv`)

| Model | Status | MAE | WAPE | Notes |
|-------|--------|-----|------|-------|
| weekly_baseline_model | Archived | 1.05 | 0.9982 | RandomForest, basic features |
| weekly_model_v2 | Archived | 2.37 | 0.1502 | More features |
| weekly_model_v3_calendar | Archived | 2.37 | 0.1500 | Calendar features, old cutoff Jan 2026 |
| **weekly_model_retrained_v3_calendar** | **BEST** | **2.11** | **0.1471** | Retrained May 2026, cutoff Mar 31 |
| weekly_model_v4_promotions | Archived | 2.61 | 0.1655 | Promo features, underperforms v3 |

### Training Scripts (`src/models/`)

| Script | Trains | Cutoff |
|--------|--------|--------|
| baseline_units_model.py | weekly_baseline_model | 2026-01-01 |
| train_weekly_model_v2.py | weekly_model_v2 | 2026-01-01 |
| train_weekly_model_v3_calendar.py | weekly_model_v3_calendar | **2026-03-31** (updated) |
| train_weekly_model_v4_promotions.py | weekly_model_v4_promotions | needs updating |
| compare_models.py | — | Compares all trained models |

### Retraining Rules
- **When:** When WAPE exceeds 20% alert threshold in notebook 14, or every quarter
- **Cutoff principle:** Train/test split is a business decision — never change it just to improve WAPE numbers
- **Current split:** train `< 2026-03-31`, test `>= 2026-04-01` (April–May = ~5 weeks unseen)
- **After retraining:** always update `model_registry.csv` manually — scripts do NOT auto-update it

### How to Retrain (Full Steps)
```bash
# 1. Refresh data
PYTHONPATH=. python3 src/data/make_weekly_dataset.py
PYTHONPATH=. python3 src/data/make_weekly_dataset_v2.py
PYTHONPATH=. python3 src/data/make_weekly_dataset_v3_calendar.py

# 2. Train
PYTHONPATH=. python3 src/models/train_weekly_model_v3_calendar.py

# 3. Note WAPE + MAE from output, update model_registry.csv manually

# 4. Generate fresh forecast
PYTHONPATH=. python3 src/forecasting/generate_weekly_forecast.py
```

---

## Forecasting Pipeline

### Script: `src/forecasting/generate_weekly_forecast.py`
- Reads best model from `model_registry.csv` automatically
- Builds lag features (lag_1, lag_4, rolling_mean_4) from latest data
- Forecasts **1 week ahead** for all 7 stores × 120 products = 840 predictions
- Appends to `data/outputs/weekly_forecasts.csv` (deduplicates on re-run)

### Current Forecasts (`data/outputs/weekly_forecasts.csv`)

| Forecast Week | Model | Total Predicted Units |
|---|---|---|
| 2026-03-30 | weekly_model_v4_promotions | 13,571 |
| 2026-05-04 | weekly_model_v3_calendar | 12,138 |
| 2026-05-11 | weekly_model_v3_calendar | 12,525 |

**Note:** Retrained model not yet used for a forecast run — do this next.

### Weekly Operations (Every Saturday)
```
1. Run generate_weekly_forecast.py    → new week's predictions
2. Upload actuals to Supabase         → previous week's real sales
3. Run src/monitoring/model_monitor.py → compare forecast vs actuals
4. Open notebook 14                   → check WAPE, investigate if > 20%
5. Open notebook 15                   → visualise new week's forecast
```

---

## Monitoring

### Script: `src/monitoring/model_monitor.py`
- Pulls actuals from Supabase
- Joins against `weekly_forecasts.csv`
- Computes WAPE, MAE, Bias per week
- Alerts when WAPE > 20%
- Saves to `data/outputs/weekly_model_monitoring.csv` and `weekly_monitoring_summary.csv`
- Produces plots in `data/outputs/plots/`

### Current Monitoring State

| Forecast Week | WAPE | Alert |
|---|---|---|
| 2026-03-30 | 1.358 (135%) | ⚠️ Check Model |
| 2026-05-04 | NaN | OK (no actuals yet) |
| 2026-05-11 | — | Not in monitoring file yet |

**Action needed:** Upload actuals for May 4 and May 11, investigate the March WAPE spike.

---

## GenAI Insight Assistant

### What's Built (`src/genai/`)
- `router.py` — routes questions to offline handler or OpenAI LLM
- `rag/build_kb.py` — builds embeddings knowledge base (OpenAI text-embedding-3-small)
- `rag/retrieve.py` — retrieves relevant chunks for a question
- `rag_qa.py` — full RAG Q&A pipeline
- `tools/forecast_tools.py` — tools for LLM to query forecast data
- `prompts.py` — system prompts
- `openai_client.py` — OpenAI API client
- `copilot.py` — main assistant entry point

### Current State
- **Offline mode works** — keyword-based answers for stockout, promo, pricing, revenue questions
- **LLM mode** — requires OpenAI API billing to be active
- **Knowledge base** — partially built, needs more documents added
- **API endpoint** — `POST /ask` is live in FastAPI

### To Complete GenAI
- [ ] Add more knowledge documents to `data/knowledge/`
- [ ] Run `src/genai/rag/build_kb.py` to rebuild embeddings
- [ ] Activate OpenAI billing and test full LLM responses
- [ ] Update the `DOCS` list in `src/api/app.py` with richer context
- [ ] Test example queries: forecast explanation, promo impact, what-if scenarios

---

## FastAPI — `src/api/`

### Endpoints (Currently Built)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| POST | `/predict/units/csv` | Upload CSV, get unit predictions |
| POST | `/decision/plan` | Combined pricing + inventory decision |
| GET | `/pricing/elasticity` | Price elasticity by category |
| POST | `/ask` | GenAI Q&A assistant |

### Agents Behind the API (`src/agents/`)
- `pricing_agent.py` — recommends optimal price given constraints
- `inventory_agent.py` — recommends reorder quantity and trigger point

### To Complete API
- [ ] Test all endpoints end-to-end (currently untested in production)
- [ ] Add `POST /forecast/weekly` endpoint — return latest weekly forecast as JSON
- [ ] Add `POST /stockout-risk` endpoint — return stockout probability per product
- [ ] Add authentication (API key header)
- [ ] Add input validation and error handling on all routes

---

## Deployment

### Docker (`docker-compose.yml`)
- `sunnybest-api` — FastAPI on port 8000
- `sunnybest-dashboard` — Streamlit on port 8501
- Both containerised with `docker/Dockerfile` and `docker/Dockerfile.streamlit`

### To Deploy
- [ ] Test Docker build locally: `docker-compose up --build`
- [ ] Set `SUPABASE_DB_PASSWORD` as Docker environment variable
- [ ] Deploy to AWS EC2 (or ECS + ECR for managed containers)
- [ ] Store model `.pkl` files on S3, pull at startup
- [ ] Set up domain + HTTPS

---

## Streamlit Dashboard — `src/dashboards/streamlit_app.py`
- **Status:** File exists, needs completion
- **Goal:** Visual dashboard for non-technical store managers
- **Should show:** Weekly forecast by store, WAPE history, stockout risk, top/bottom products

---

## Remaining Work — Priority Order

### High Priority (Do Next)
1. **Generate new forecast** with retrained model:
   ```bash
   PYTHONPATH=. python3 src/forecasting/generate_weekly_forecast.py
   ```
2. **Upload actuals** for May 4 and May 11, then run `model_monitor.py`
3. **Investigate March WAPE** of 135% in notebook 14 — data issue or model failure?
4. **Review notebooks 16 and 17** — demand sensing and inventory optimisation outputs

### Medium Priority
5. **Retrain v4 with new cutoff** (Mar 31) — compare against retrained v3, may now beat it
6. **Complete FastAPI testing** — run all endpoints, fix any issues
7. **Test Docker build** — `docker-compose up --build`
8. **Complete GenAI** — activate OpenAI, enrich knowledge base, test `/ask` endpoint

### Lower Priority
9. **Deploy to AWS** — EC2 or ECS
10. **Complete Streamlit dashboard** — weekly forecast view, WAPE history
11. **Multi-week ahead forecasting** — extend from 1-week to 4-week horizon
12. **Per-category models** — separate models for Mobile Phones, TVs, Accessories etc.
13. **Automate Saturday pipeline** — cron job for forecast + monitoring
14. **Final documentation & portfolio presentation**

---

## Key Metrics to Track

| Metric | Current | Target |
|--------|---------|--------|
| Live WAPE (best model) | 14.71% (validation) | < 20% on live data |
| Forecast horizon | 1 week | 4 weeks |
| Data freshness | Up to 2026-05-04 | Refreshed every Saturday |
| API status | Built, untested | Deployed on AWS |

---

## Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set Supabase password
export SUPABASE_DB_PASSWORD='your_password'

# Run with PYTHONPATH from project root
PYTHONPATH=. python3 <script>
```
