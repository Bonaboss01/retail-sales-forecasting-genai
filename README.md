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
| EDA notebook | 🔄 In Progress |
| Baseline forecasting | ⏳ Pending |
| ML forecasting | ⏳ Pending |
| Stock-out classifier | ⏳ Pending |
| GenAI insight assistant | ⏳ Pending |
| FastAPI backend | ⏳ Pending |
| Dockerization | ⏳ Pending |
| AWS Deployment | ⏳ Pending |
| Documentation polish | ⏳ Pending |

---

## 📁 Recommended Project Structure

```text
retail-sales-forecasting-genai/
├── README.md
├── pyproject.toml / setup.cfg        # package config (or requirements.txt)
├── requirements.txt
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
│   └── 06_genai_rag_experiments.ipynb
├── src/
│   ├── config/
│   │   └── config.yaml
│   ├── data/
│   │   ├── make_dataset.py
│   │   └── simulate_data.py
│   ├── features/
│   │   └── build_features.py
│   ├── models/
│   │   ├── train_forecast.py
│   │   ├── train_stockout.py
│   │   └── predict.py
│   ├── evaluation/
│   │   └── evaluate_models.py
│   ├── api/
│   │   └── app.py          # FastAPI endpoints
│   ├── genai/
│   │   ├── rag_index.py
│   │   ├── rag_qa.py
│   │   └── explain_forecast.py
│   └── dashboards/
│       └── streamlit_app.py
├── mlruns/                  # MLflow tracking (gitignored)
├── docker/
│   └── Dockerfile
├── infra/
│   └── terraform/           # optional
├── tests/
│   ├── test_features.py
│   ├── test_models.py
│   └── test_api.py
└── assets/
    ├── architecture.png
    └── screenshots/

