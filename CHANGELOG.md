# CHANGELOG — SunnyBest AI Retail Forecasting System

---

## [Unreleased]

---

## 2026-05-25

### Added
- `16_demand_sensing.ipynb` — demand sensing notebook (short-term signal detection)
- `17_inventory_optimisation.ipynb` — inventory optimisation notebook

---

## 2026-05 (Recent Sprint)

### Added
- `15_weekly_forecast_analysis.ipynb` — weekly forecast visualisation (by store, category, product heatmap)
- `14_model_monitoring.ipynb` — forecast vs actuals monitoring with WAPE alert threshold (20%)
- `src/monitoring/model_monitor.py` — model monitoring script
- `data/outputs/weekly_forecasts.csv` — forecast output file (2,520 rows across 3 weeks)
- `data/outputs/weekly_actuals.csv` — actuals for monitoring comparison
- `data/outputs/weekly_model_monitoring.csv` / `weekly_monitoring_summary.csv` — monitoring outputs

### Changed
- `src/forecasting/generate_weekly_forecast.py` — updated weekly forecast generation pipeline
- `src/data/make_weekly_dataset_v4_promotions.py` — updated feature engineering with promotions
- Various notebook cleanup and housekeeping

---

## 2026-04 (Forecasting Sprint)

### Added
- `weekly_model_v4_promotions` — model trained with promotion features (WAPE 0.1655, archived)
- `weekly_model_v3_calendar` — model with calendar features, marked as **BEST** (WAPE 0.1500)
- `weekly_model_v2` — second iteration model (WAPE 0.1502, archived)
- Forecast run for week of **2026-03-30** using v4_promotions model (13,571 units predicted)
- Forecast runs for **2026-05-04** and **2026-05-11** using v3_calendar model

### Changed
- `models/model_registry.csv` — v3_calendar promoted to "best"; v4_promotions archived

---

## Earlier

### Added
- `01_data_understanding.ipynb` — EDA
- `02_baseline_forecast.ipynb` — naïve, moving average, exponential smoothing baselines
- `03_ml_forecasting.ipynb` — LinearRegression, RandomForest, XGBoost, LightGBM
- `04_stockout_classification.ipynb` — binary stockout classifier
- `05_promo_uplift_causal.ipynb` — causal promotion uplift
- `06_genai_rag_experiments.ipynb` — RAG pipeline experiments
- `07_price_elasticity.ipynb` — price elasticity
- `08_pricing_optimization.ipynb` — pricing optimisation
- `09_spark_data_processing.ipynb` — Spark data processing
- `10_validate_data.ipynb` — data validation & sanity checks
- `11_store_stockout_analysis.ipynb` — store-level stockout analysis
- `12_product_stockout_analysis.ipynb` — product-level stockout analysis
- `13_timing_drivers_stockout.ipynb` — stockout timing & drivers
- `src/api/app.py` and `src/api/app_genai.py` — FastAPI application (in progress)
- `src/genai/` — GenAI assistant, RAG, tools, prompts
- `docker-compose.yml` — Docker setup
- `weekly_baseline_model` — first model (WAPE 0.9982, archived)
