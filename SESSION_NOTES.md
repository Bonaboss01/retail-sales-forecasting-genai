# SESSION NOTES — SunnyBest AI Retail Forecasting System
> Running log of working sessions. Add a new entry at the top each time you sit down.

---

## 2026-05-26 (STOPPED HERE — resume from this point)

### What I worked on
- Understood the full retraining process end to end
- Understood temporal train/test split — train up to cutoff, test on unseen weeks after
- Understood the forecasting feedback loop — forecast → actuals come in → compare weekly in notebook 14 → retrain when WAPE breaches 20%
- Confirmed training scripts exist in `src/models/` — v2, v3, v4 and baseline
- Read `baseline_units_model.py` — confirmed it is a training script (misleading name), trains RandomForest, cutoff hardcoded at `2026-01-01`

### Key findings / decisions
- Training scripts are well structured but NOT ready to run as-is — two things need fixing first:
  1. **Data is stale** — `data/processed/` CSVs end at 2026-03-23, need refreshing from Supabase
  2. **Cutoff date is hardcoded** — `baseline_units_model.py` uses `2026-01-01`, need to verify v3 and v4 scripts use the same and update accordingly
- Plan is to train on data up to ~March 23, test on last few weeks, then forecast April/May going forward
- As April/May actuals come in each Saturday, compare against forecasts in notebook 14 weekly

### EXACT NEXT STEPS (in order)

1. **Open `train_weekly_model_v3_calendar.py`** — check what cutoff date it uses and confirm it matches the plan
2. **Run `src/data/make_weekly_dataset_v4_promotions.py`** — refreshes `data/processed/` CSVs with latest data from Supabase
3. **Update the cutoff date** in the v3 training script to reflect the new train/test boundary
4. **Run `train_weekly_model_v3_calendar.py`** — retrain the model on fresh data
5. **Run `compare_models.py`** — compare new model WAPE vs old, confirm improvement
6. **Update `models/model_registry.csv`** — mark new retrained model as `best`, archive old v3
7. **Run `generate_weekly_forecast.py`** — generate forecast for week of 2026-05-26
8. **Run notebook 15** — visualise the new forecast
9. **Every Saturday going forward** — upload actuals, run notebook 14, check WAPE

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
