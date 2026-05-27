# SESSION NOTES — SunnyBest AI Retail Forecasting System
> Running log of working sessions. Add a new entry at the top each time you sit down.

---

## 2026-05-27 (STOPPED HERE — resume from this point)

### What I worked on
- Updated PROJECT_PLAN.md — full state-of-the-art project plan with all workstreams, scripts, models, operations
- Created WEEKLY_OPERATIONS.md — step-by-step Saturday guide to follow every week
- Retrained v4 model — `weekly_model_v4_promotions_2026_05` (MAE 2.12, WAPE 14.77%) — v3 still best
- Updated model registry with date-based naming convention (YYYY_MM)
- Fixed model registry path issue — training script overwrites same .pkl file, registry must point to actual filename
- Successfully ran `generate_weekly_forecast.py` — generated forecast for **week commencing 2026-05-11**
- Understood the full forecasting loop end to end

### Key findings / decisions
- `generate_weekly_forecast.py` pulls data directly from Supabase (not processed CSVs) — always gets freshest lag features
- Processed CSVs are only needed for retraining, not for forecasting
- Supabase data ends at 2026-05-04 → forecast generated for 2026-05-11 (last known week + 7 days)
- Training script saves model to hardcoded filename — update `MODEL_PATH` in script before retraining to avoid overwriting old models
- Naming convention for models: `weekly_model_v3_calendar_YYYY_MM`

### EXACT NEXT STEPS (in order)

1. **Run model monitoring** — compare May 11 forecast against actuals:
   ```bash
   PYTHONPATH=. python3 src/monitoring/model_monitor.py
   ```
2. **Open notebook 14** — review WAPE for week of May 11, check which stores/products had worst errors
3. **Check WAPE decision:**
   - Below 20% → model is healthy, continue
   - Above 20% → investigate, consider retraining
4. **Upload actuals for May 18 and May 25** to Supabase (these weeks have passed)
5. **Re-run forecast script** — will generate forecast for the next available week
6. **Continue with remaining project work** — see PROJECT_PLAN.md "Remaining Work" section

---

## 2026-05-26 23:54

### What I worked on
- Understood the full retraining process end to end
- Understood temporal train/test split — train up to cutoff, test on unseen weeks after
- Understood the forecasting feedback loop — forecast → actuals come in → compare weekly in notebook 14 → retrain when WAPE breaches 20%
- Confirmed training scripts exist in `src/models/` — v2, v3, v4 and baseline
- Read `baseline_units_model.py` — confirmed it is a training script (misleading name), trains RandomForest, cutoff hardcoded at `2026-01-01`
- Discovered all 3 data scripts (`make_weekly_dataset.py`, `v2`, `v3_calendar`) were pointing to **localhost** — updated all 3 to use `src/data/db_connection.py` (Supabase)
- **Successfully refreshed all processed datasets from Supabase**

### Key findings / decisions
- Do NOT change the cutoff date to get a better WAPE — cutoff is a business decision, not a tuning knob
- Cutoff date in v3 training script is currently `2026-01-01` — needs updating before retraining
- New cutoff agreed: train `< 2026-03-31`, test `>= 2026-04-01` (5 weeks of April–May as unseen test)
- Data now refreshed: `data/processed/weekly_sales_v3_calendar.csv` covers **2020-12-28 → 2026-05-04** (was March 23, gained 6 extra weeks)
- v3 training script is open and ready — just needs the 1-line cutoff change before running

### EXACT NEXT STEPS (in order)

1. ✅ Updated cutoff in `train_weekly_model_v3_calendar.py` — train `< 2026-03-31`, test `>= 2026-04-01`
2. ✅ Retrained model — new performance: **MAE 2.1093, WAPE 14.71%** (improved from MAE 2.37, WAPE 15.00%)
3. ✅ Updated `models/model_registry.csv` — `weekly_model_retrained_v3_calendar` marked as `best`, old v3 archived
4. **Run `generate_weekly_forecast.py`** — will automatically pick up the new best model:
   ```bash
   PYTHONPATH=. python3 src/forecasting/generate_weekly_forecast.py
   ```
5. **Run notebook 15** — visualise the new forecast
6. **Optionally retrain v4** — same cutoff change in `train_weekly_model_v4_promotions.py`, run it, compare WAPE against retrained v3
7. **Every Saturday** — upload actuals, run notebook 14, check WAPE stays below 20%

---

## 2026-05-25

### What I worked on
- Reviewed the full forecast pipeline end-to-end
- Understood how `generate_weekly_forecast.py` works — picks the "best" model from `model_registry.csv` and forecasts 1 week ahead
- Understood why two model versions exist in `weekly_forecasts.csv` — registry changed between March and May runs
- Understood the difference between notebook 14 (was the model right?) and notebook 15 (what is it predicting?)
- Understood why `read_sql` is used in notebook 15 — to enrich forecast IDs with store/product names from Supabase
- Inspected `weekly_model_monitoring.csv` and `weekly_monitoring_summary.csv`

### Key findings / decisions
- `weekly_forecasts.csv` has 3 forecast weeks: 2026-03-30, 2026-05-04, 2026-05-11 (all now in the past)
- **CRITICAL: March 2026-03-30 WAPE = 1.358 (135%) — flagged "Check Model"** — model errors are larger than actual sales. This must be investigated before generating new forecasts.
- May 4 actuals are missing (`actual_sum = 0`) — actuals were never uploaded for that week
- May 11 is not in the monitoring file at all — also missing actuals
- Current best model: `weekly_model_v3_calendar` (WAPE 0.15 on validation). v4_promotions archived (worse WAPE 0.1655)
- Notebooks 16 (`demand_sensing`) and 17 (`inventory_optimisation`) were recently created — outputs not yet reviewed

### EXACT NEXT STEPS (in order)

1. **Investigate March WAPE** — open `14_model_monitoring.ipynb`, look at which stores/products had the worst errors. Is it a data problem (actuals loaded wrong) or a genuine model failure?
2. **Upload actuals for May 4 and May 11** — run the Saturday upload script so monitoring has real sales numbers
3. **Re-run `14_model_monitoring.ipynb`** — check WAPE for May 4 and May 11. If only March was bad → data issue. If all weeks are bad → retrain the model.
4. **Generate new forecasts** — only after confirming model is reliable, run:
   ```bash
   PYTHONPATH=. python src/forecasting/generate_weekly_forecast.py
   ```
   This will generate the week of 2026-05-26.
5. **Review notebooks 16 and 17** — check outputs of demand sensing and inventory optimisation
6. **Continue Phase 5** — GenAI assistant (`src/genai/`) and Phase 6 — API (`src/api/app.py`)

---

## [Template for new sessions — copy and paste to top]

## YYYY-MM-DD

### What I worked on
-

### Key findings / decisions
-

### Blockers / Issues
-

### Left off at / To pick up next
-

---

## Earlier Sessions (summary from git history)

| Date (approx) | Work Done |
|----------------|-----------|
| May 2026 | Built model monitoring (nb 14), weekly forecast analysis (nb 15), forecast generation script, model monitoring scripts |
| Apr 2026 | Trained v3_calendar and v4_promotions models; v3 selected as best; ran first forecasts |
| Mar–Apr 2026 | Store & product stockout analysis (nb 11, 12, 13); pricing optimization (nb 08); Spark processing (nb 09); data validation (nb 10) |
| Feb–Mar 2026 | GenAI RAG experiments (nb 06); price elasticity (nb 07); promo uplift (nb 05) |
| Jan–Feb 2026 | Baseline forecasting (nb 02); ML forecasting (nb 03); stockout classification (nb 04) |
| Jan 2026 | Project setup; data generation; EDA (nb 01) |
