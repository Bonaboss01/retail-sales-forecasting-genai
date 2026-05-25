# NEXT STEPS — SunnyBest AI Retail Forecasting System
> Last updated: 2026-05-25

---

## Immediate (Pick up now)

- [ ] **Review notebooks 16 & 17** — `16_demand_sensing.ipynb` and `17_inventory_optimisation.ipynb` were just created. Review outputs, fix any issues, and confirm results make sense.
- [ ] **Generate latest forecast** — The most recent forecast only covers up to 2026-05-11. Run the forecast script to generate the week of 2026-05-19 and 2026-05-26:
  ```bash
  PYTHONPATH=. python src/forecasting/generate_weekly_forecast.py
  ```
- [ ] **Run model monitoring** — All 3 forecast weeks (Mar 30, May 4, May 11) are in the past. Upload actuals and run `14_model_monitoring.ipynb` to evaluate WAPE and identify any drift.
- [ ] **Investigate forecast_analysis notebook issue** — `15_weekly_forecast_analysis.ipynb` may have an issue (user flagged). Needs checking.

---

## Phase 5 — GenAI Assistant (In Progress)

- [ ] Complete RAG pipeline in `src/genai/rag/`
- [ ] Wire up `06_genai_rag_experiments.ipynb` findings into production code
- [ ] Test end-to-end: query → retrieval → LLM response
- [ ] Add example queries: forecast explanation, promo impact, product performance, what-if scenarios

---

## Phase 6 — API & Deployment (In Progress)

- [ ] Complete FastAPI endpoints in `src/api/app.py`:
  - `POST /forecast` — return weekly predictions
  - `POST /stockout-risk` — return stockout probability
  - `POST /genai/explain` — LLM forecast explanation
  - `POST /genai/qa` — RAG Q&A
- [ ] Test Docker build (`docker-compose.yml` exists)
- [ ] Deploy to AWS EC2 (or ECS + ECR)
- [ ] Add S3 model storage

---

## Phase 7 — Documentation

- [ ] Finalize `README.md` with system architecture diagram
- [ ] Add model pipeline diagram to `/docs`
- [ ] Add RAG flow diagram to `/docs`
- [ ] Write presentation deck for portfolio/interviews

---

## Ongoing / Recurring

- [ ] Run `generate_weekly_forecast.py` every Saturday to keep forecasts current
- [ ] Run `14_model_monitoring.ipynb` after each Saturday actuals upload
- [ ] Consider retraining model if WAPE rises above 20% alert threshold
