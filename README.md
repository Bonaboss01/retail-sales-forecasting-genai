# 🧠 AI-Powered Retail Decision Intelligence Platform  
## 📦 SunnyBest Telecommunications *(Synthetic Case Study)*

An end-to-end **AI, Machine Learning, and Generative AI–driven retail analytics platform** built for a **telecom and consumer electronics retailer — SunnyBest Telecommunications**.

This project demonstrates how modern data science, forecasting, pricing analytics, and **Generative AI (RAG + LLMs)** can be combined into a single system to support **real-world retail decision-making**, rather than isolated models or dashboards.

---

## 🎯 Project Aim

The aim of this project is to demonstrate how an **AI-powered analytics platform** can support retail decision-making across **demand forecasting, inventory risk management, promotion effectiveness, and pricing optimisation**.

The system integrates traditional analytics, machine learning models, and **Generative AI (RAG + LLMs)** to produce **actionable and explainable insights** that are accessible to both **technical and non-technical stakeholders**.

---

## 🏪 Business Context

SunnyBest Telecommunications operates retail outlets across:

**Benin, Ekpoma, Auchi, Irrua, Igueben, Agenebode, Ogwa  
(Edo State, Nigeria)**

Like many multi-store retailers, the business faces recurring operational and strategic challenges:

- Demand volatility and strong seasonal patterns  
- Stock-outs leading to lost revenue and poor customer experience  
- Uncertainty around promotion effectiveness and return on investment  
- Pricing decisions that directly affect demand and profitability  
- Limited access to insights for non-technical decision-makers  

This project simulates how an **AI-enabled retail analytics platform** could address these challenges by turning raw data into **decision-ready intelligence**.

---

## 🎯 Project Objectives

- Design a **production-style analytics and ML system**, from raw data ingestion to business insights  
- Apply **time-series forecasting** techniques to model retail demand  
- Predict **stock-out risk** using supervised machine learning  
- Analyse **promotion uplift** and pricing behaviour through modelling and simulation  
- Experiment with **Generative AI (RAG + LLMs)** to translate analytical outputs into natural-language insights  
- Structure the project for **API, Docker, and cloud-ready deployment**  

---

## 🔍 What This Project Demonstrates

- ✔ Synthetic retail data generation (sales, inventory, promotions, weather, calendar effects)  
- ✔ Exploratory Data Analysis (EDA) to understand demand patterns and drivers  
- ✔ Baseline and machine-learning-based demand forecasting  
- ✔ Stock-out prediction using classification models  
- ✔ Pricing analytics, elasticity modelling, and optimisation experiments  
- ✔ GenAI-assisted analytics using Retrieval-Augmented Generation (RAG) concepts  
- ✔ A production-oriented project structure with clear separation between experimentation, modelling, and deployment  

---

## 🧩 How to Think About This Project

This is **not** a single-model or accuracy-focused exercise.  
It is a **decision intelligence system** that demonstrates how analytics, ML, and GenAI can work together to answer questions such as:

- *What will demand look like next month, and why?*  
- *Which products are at risk of stock-out?*  
- *Are promotions actually driving incremental sales?*  
- *How sensitive is demand to price changes?*  
- *How can insights be explained clearly to non-technical stakeholders?*  

---

### 📌 Notes

- All data used in this project is **synthetic** and created for demonstration purposes.  
- The architecture reflects how such a system could evolve in a real production environment, while keeping the core models lightweight and interpretable.


## 🚦 Implementation Status

| Component | Status | Notes |
|---------|--------|-------|
| Repository structure | ✅ Implemented | Modular, scalable layout |
| Synthetic data generation | ✅ Implemented | Retail-like dataset |
| Exploratory Data Analysis | ✅ Implemented | EDA notebooks completed |
| Baseline forecasting | ✅ Implemented | Statistical benchmarks |
| ML forecasting (XGBoost) | ✅ Implemented | Model trained & evaluated |
| Stock-out classification | ✅ Implemented | Binary classifier |
| Pricing analysis | ⚠️ Partial | Elasticity & optimisation notebooks |
| GenAI RAG experiments | ⚠️ Experimental | Notebook-based exploration |
| FastAPI backend | 🛠 Planned | API scaffold designed |
| Dockerisation | 🛠 Planned | To containerise API & dashboard |
| AWS deployment | 🛠 Planned | EC2 / S3 / future MLOps |

---

## 🧭 Analytical Components

### 📊 Forecasting
- Baseline statistical models
- Machine learning forecasting (XGBoost)
- Evaluation using appropriate error metrics

### 📦 Stock-Out Prediction
- Binary classification of stock-out risk
- Feature engineering from sales, inventory & promotions

### 💰 Pricing Analytics
- Price elasticity modelling
- Revenue / profit optimisation scenarios
- What-if pricing simulations

### 🤖 GenAI Insight Experiments
- Retrieval-Augmented Generation (RAG)
- Natural-language questions over retail data
- LLM-based explanation prototypes (experimental)

## 📁 Project Structure

### Version 1

```text
retail-sales-forecasting-genai/
├── README.md
├── pyproject.toml                 # Optional: packaging configuration
├── setup.cfg                      # Optional
├── requirements.txt               # Python dependencies
├── .gitignore                     # Files & folders ignored by Git

├── data/
│   ├── raw/                       # Generated CSVs (small mode)
│   ├── processed/                 # Feature-ready datasets / Parquet (large mode, gitignored)
│   └── external/                  # External docs, notes

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
│   ├── config/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── pricing/
│   ├── dashboards/
│   ├── api/
│   ├── spark/
│   ├── warehouse/
│   └── genai/
│       ├── copilot.py
│       ├── tools.py
│       ├── rag_index.py
│       ├── rag_qa.py
│       ├── prompts/
│       └── eval/

├── docker/
│   └── Dockerfile

├── infra/
│   └── terraform/

├── models/
│   ├── xgb_revenue_forecast.pkl
│   └── stockout_classifier.pkl

├── mlruns/
├── tests/
└── assets/
    ├── architecture.png
    └── screenshots/











### GenAI Agent (Planned Extension)

The `genai/agent/` module is intentionally included as a placeholder for future
work exploring autonomous and semi-autonomous AI agents (tool use, memory,
and policy control).

At the current stage of the project, GenAI is used primarily as an
**explanation and decision-support layer** (RAG + model explanations),
while agent-based orchestration is planned as a future enhancement.

## Optional Scaling Layer: Spark + Warehouse (Snowflake)

> **Note on Spark:**  
> This project does not strictly require Spark at its current scale. I included Spark as an optional processing layer to demonstrate how the pipeline could evolve in production as data volumes grow. The core modelling remains in pandas to support faster iteration during development.

---

### Why Spark?
As SunnyBest expands (more stores, more SKUs, higher transaction volume), batch ETL and feature engineering can exceed single-machine limits. Spark provides:
- Distributed data processing for large datasets
- Scalable ETL pipelines (joins, aggregations, feature generation)
- A clean path to production data platforms

### How this fits in the pipeline
- **Current (local / prototyping):** CSV → pandas notebooks → models  
- **Scaled (production concept):** Raw data → Spark ETL → curated tables → warehouse (e.g., Snowflake) → models & dashboards

### Repository components
- `notebooks/09_spark_data_processing.ipynb` – Spark ETL demonstration (optional)
- `src/spark/` – Spark utilities (session, ETL, aggregations, feature engineering)
- `src/warehouse/` – Example SQL for warehouse staging + marts (conceptual)
