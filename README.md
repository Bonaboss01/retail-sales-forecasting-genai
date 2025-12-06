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
│
├── data/
│   └── raw/
│
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_baseline_forecast.ipynb
│   ├── 03_ml_forecast.ipynb
│   ├── 04_stockout_classification.ipynb
│   └── 05_genai_assistant.ipynb
│
├── src/
│   ├── features/
│   ├── models/
│   ├── genai/
│   └── api/
│
├── models/
│
├── docs/
│   └── (architecture diagrams, screenshots, notes)
│
├── PROJECT_PLAN.md
├── ROADMAP.md
├── generate_sunnybest_data.py
├── requirements.txt
├── Dockerfile
└── README.md
