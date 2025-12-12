# retail-sales-forecasting-genai
## 📦 SunnyBest Telecommunications – AI Retail Forecasting & GenAI System

This project builds an end-to-end AI-driven forecasting and analytics platform for **SunnyBest Telecommunications**, a consumer electronics & telecom retailer operating across:

**Benin, Ekpoma, Auchi, Irrua, Igueben, Agenebode, Ogwa (Edo State, Nigeria).**

### 🔍 What this project includes

- ✔ Synthetic retail dataset (sales, weather, promotions, inventory)  
- ✔ Exploratory Data Analysis (EDA)  
- ✔ Time-series forecasting (baseline + machine learning models)  
- ✔ Stock-out prediction (classification)  
- ✔ GenAI Insight Assistant (RAG + LLM for natural-language analytics)  
- ✔ FastAPI backend for forecasts + explanations  
- ✔ Docker + AWS deployment  

---

## 🧭 Project Phases Overview

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| **Phase 1** | Data Generation | Synthetic SunnyBest dataset, folders, scripts |
| **Phase 2** | Exploratory Data Analysis | EDA notebook, findings, visualizations |
| **Phase 3** | Forecasting Models | Baseline + ML models, saved artifacts |
| **Phase 4** | Stock-Out Prediction | Classification model + evaluation |
| **Phase 5** | GenAI Assistant | RAG pipeline + LLM insight engine |
| **Phase 6** | Deployment | FastAPI, Docker, AWS EC2 |
| **Phase 7** | Documentation | README, plan, diagrams |

---

## 📅 Roadmap (Live Project Status)

| Task | Status |
|------|--------|
| Repository setup | ✅ Completed |
| Data generation script | ✅ Completed |
| Synthetic dataset created | ✅ Completed |
| EDA notebook | ✅ Completed |
| Baseline forecasting | ✅ Completed |
| ML forecasting | ✅ Completed |
| Stock-out classifier | ✅ Completed |
| GenAI insight assistant | ✅ Completed |
| FastAPI backend | ⏳ Pending |
| Dockerization | ⏳ Pending |
| AWS Deployment | ⏳ Pending |
| Documentation polish | ⏳ Pending |

---

## 📁 Project Structure

retail-sales-forecasting-genai/
├── README.md
├── pyproject.toml                 
├── setup.cfg                      
├── requirements.txt
├── .gitignore

├── data/
│   ├── raw/                      
│   ├── processed/                 
│   └── external/                  

├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_baseline_forecast.ipynb
│   ├── 03_ml_forecast_xgboost.ipynb
│   ├── 04_stockout_classification.ipynb
│   ├── 05_promo_uplift_causal.ipynb
│   ├── 06_genai_rag_experiments.ipynb
│   ├── 07_price_elasticity.ipynb
│   ├── 08_pricing_optimization.ipynb
│   └── 09_spark_data_processing.ipynb

├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   └── config.yaml
│   │
│   ├── data/
│   │   ├── make_dataset.py
│   │   └── simulate_data.py
│   │
│   ├── features/
│   │   └── build_features.py
│   │
│   ├── models/
│   │   ├── train_forecast.py
│   │   ├── train_stockout.py
│   │   └── predict.py
│   │
│   ├── pricing/
│   │   ├── elasticity_model.py
│   │   ├── optimize_prices.py
│   │   ├── simulate_price_scenarios.py
│   │   └── utils.py
│   │
│   ├── genai/
│   │   ├── rag_index.py
│   │   ├── rag_qa.py
│   │   ├── explain_forecast.py
│   │   └── explain_pricing.py
│   │
│   ├── dashboards/
│   │   └── streamlit_app.py
│   │
│   ├── api/
│   │   └── app.py
│   │
│   ├── spark/
│   │   ├── spark_session.py
│   │   ├── spark_etl.py
│   │   ├── spark_aggregations.py
│   │   └── spark_feature_engineering.py
│   │
│   └── warehouse/
│       ├── snowflake_schema.sql
│       ├── staging_load.sql
│       ├── marts.sql
│       └── queries.sql

├── docker/
│   └── Dockerfile

├── infra/
│   └── terraform/

├── models/
│   ├── xgb_revenue_forecast.pkl
│   └── stockout_classifier.pkl

├── mlruns/                       # gitignored (MLflow)

├── tests/
│   ├── test_features.py
│   ├── test_models.py
│   ├── test_api.py
│   └── test_pricing.py

└── assets/
    ├── architecture.png
    └── screenshots/
