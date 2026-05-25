# PROJECT STATUS — SunnyBest AI Retail Forecasting System
> Last updated: 2026-05-25

---

## Project Summary
AI forecasting and analytics platform for **SunnyBest Telecommunications** — 7 stores across Benin, Ekpoma, Auchi, Irrua, Igueben, Agenebode, and Ogwa (Edo State, Nigeria).

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Data Generation & Setup | ✅ Complete |
| 2 | Exploratory Data Analysis (EDA) | ✅ Complete |
| 3 | Forecasting Models | ✅ Complete |
| 4 | Stock-Out Prediction | ✅ Complete |
| 5 | GenAI Insight Assistant (RAG + LLM) | 🔄 In Progress |
| 6 | API + Deployment (FastAPI + Docker) | 🔄 In Progress |
| 7 | Documentation & Presentation | ⬜ Not Started |

---

## Notebooks

| Notebook | Description | Status |
|----------|-------------|--------|
| 01_data_understanding.ipynb | EDA — sales, stores, products | ✅ Done |
| 01_Bona_data_analysis.ipynb | Extended EDA | ✅ Done |
| 02_baseline_forecast.ipynb | Naïve, moving average, exponential smoothing | ✅ Done |
| 03_ml_forecasting.ipynb | LinearReg, RandomForest, XGBoost, LightGBM | ✅ Done |
| 04_stockout_classification.ipynb | Stockout binary classifier | ✅ Done |
| 05_promo_uplift_causal.ipynb | Causal promo uplift analysis | ✅ Done |
| 06_genai_rag_experiments.ipynb | RAG pipeline experiments | ✅ Done |
| 07_price_elasticity.ipynb | Price elasticity modelling | ✅ Done |
| 08_pricing_optimization.ipynb | Pricing optimisation | ✅ Done |
| 09_spark_data_processing.ipynb | Spark-based data processing | ✅ Done |
| 10_validate_data.ipynb | Data validation & sanity checks | ✅ Done |
| 11_store_stockout_analysis.ipynb | Store-level stockout patterns | ✅ Done |
| 12_product_stockout_analysis.ipynb | Product-level stockout analysis | ✅ Done |
| 13_timing_drivers_stockout.ipynb | Timing & drivers of stockouts | ✅ Done |
| 14_model_monitoring.ipynb | Forecast vs actuals monitoring (WAPE) | ✅ Done |
| 15_weekly_forecast_analysis.ipynb | Weekly forecast visualisation | ✅ Done |
| 16_demand_sensing.ipynb | Short-term demand sensing | 🔄 Recent — review outputs |
| 17_inventory_optimisation.ipynb | Inventory optimisation | 🔄 Recent — review outputs |

---

## Models

| Model | WAPE | MAE | Status |
|-------|------|-----|--------|
| weekly_baseline_model | 0.9982 | 1.05 | Archived |
| weekly_model_v2 | 0.1502 | 2.37 | Archived |
| weekly_model_v3_calendar | **0.1500** | 2.37 | **BEST (active)** |
| weekly_model_v4_promotions | 0.1655 | 2.61 | Archived |

- Best model file: `models/weekly_model_v3_calendar.pkl`
- Registry: `models/model_registry.csv`
- Note: v4_promotions has worse WAPE than v3 — v3 is correctly marked as best.

---

## Forecast Data

- File: `data/outputs/weekly_forecasts.csv` (2,520 rows)
- 7 stores × 120 products per week

| Forecast Week | Model Used | Total Units |
|---------------|------------|-------------|
| 2026-03-30 | weekly_model_v4_promotions | 13,571 |
| 2026-05-04 | weekly_model_v3_calendar | 12,138 |
| 2026-05-11 | weekly_model_v3_calendar | 12,525 |

- All 3 forecast weeks are now past — actuals should be uploadable for evaluation.
- Next forecast to generate: week of **2026-05-19** and **2026-05-26**.

---

## Source Code

| Module | Location | Status |
|--------|----------|--------|
| Forecast generation script | `src/forecasting/generate_weekly_forecast.py` | ✅ Working |
| FastAPI app | `src/api/app.py` | 🔄 In progress |
| GenAI API routes | `src/api/app_genai.py` | 🔄 In progress |
| GenAI RAG pipeline | `src/genai/rag/` | 🔄 In progress |
| GenAI assistant | `src/genai/assistant/` | 🔄 In progress |
| Model monitoring | `src/monitoring/model_monitor.py` | ✅ Working |
| Demand sensing | `src/planning/` | 🔄 Recent |
