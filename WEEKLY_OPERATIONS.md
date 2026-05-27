# Weekly Operations Guide — SunnyBest Forecasting System
> Follow this every Saturday without skipping steps.

---

## Every Saturday — Step by Step

### PART 1 — Generate This Week's Forecast
> Do this first thing on Saturday morning, before the week's sales are uploaded.

**Step 1 — Refresh data from Supabase**
```bash
PYTHONPATH=. python3 src/data/make_weekly_dataset.py
PYTHONPATH=. python3 src/data/make_weekly_dataset_v2.py
PYTHONPATH=. python3 src/data/make_weekly_dataset_v3_calendar.py
```

**Step 2 — Generate the forecast**
```bash
PYTHONPATH=. python3 src/forecasting/generate_weekly_forecast.py
```
Check the output — it should print the forecast week date and confirm 840 rows saved.

**Step 3 — Visualise the forecast**
- Open `notebooks/15_weekly_forecast_analysis.ipynb`
- Run all cells
- Review: which stores are predicted to sell the most? Any unusual numbers?

---

### PART 2 — Evaluate Last Week's Forecast
> Do this after uploading last week's actual sales to Supabase.

**Step 4 — Upload last week's actuals to Supabase**
- Run your actuals upload script
- Confirm data is in `core.fact_sales`

**Step 5 — Run the model monitor**
```bash
PYTHONPATH=. python3 src/monitoring/model_monitor.py
```
This compares last week's forecast against real sales and saves results to `data/outputs/`.

**Step 6 — Review monitoring results**
- Open `notebooks/14_model_monitoring.ipynb`
- Run all cells
- Check the WAPE for last week

---

### PART 3 — Decision Point

```
Is WAPE below 20%?
│
├── YES → Model is healthy. You're done for this Saturday. ✅
│
└── NO  → Investigate:
          - Which stores/products had the worst errors?
          - Was there a promotion or unusual event that week?
          - Is it a one-off spike or a trend over multiple weeks?
          
          If WAPE is consistently bad over 2+ weeks → Retrain (see below)
```

---

## Retraining (When WAPE Exceeds 20%)

**Step 1 — Refresh all data**
```bash
PYTHONPATH=. python3 src/data/make_weekly_dataset.py
PYTHONPATH=. python3 src/data/make_weekly_dataset_v2.py
PYTHONPATH=. python3 src/data/make_weekly_dataset_v3_calendar.py
```

**Step 2 — Update the cutoff date in the training script**
- Open `src/models/train_weekly_model_v3_calendar.py`
- Update line 84 — set train cutoff to ~6 weeks before today, test from there to now

**Step 3 — Retrain**
```bash
PYTHONPATH=. python3 src/models/train_weekly_model_v3_calendar.py
```
Note down the MAE and WAPE printed at the end.

**Step 4 — Update model registry**
- Open `models/model_registry.csv`
- Add new row: `weekly_model_v3_calendar_YYYY_MM,models/weekly_model_retrained_v3_calendar.pkl,best,<MAE>,<WAPE>`
- Change old best model status from `best` → `archived`
- Only ONE model should have status = `best` at a time

**Step 5 — Go back to Part 1** and generate a fresh forecast with the new model

---

## Quick Reference — Key Scripts

| What | Command |
|------|---------|
| Refresh data | `PYTHONPATH=. python3 src/data/make_weekly_dataset_v3_calendar.py` |
| Generate forecast | `PYTHONPATH=. python3 src/forecasting/generate_weekly_forecast.py` |
| Run monitoring | `PYTHONPATH=. python3 src/monitoring/model_monitor.py` |
| Retrain v3 | `PYTHONPATH=. python3 src/models/train_weekly_model_v3_calendar.py` |
| Retrain v4 | `PYTHONPATH=. python3 src/models/train_weekly_model_v4_promotions.py` |

## Quick Reference — Key Files

| What | Location |
|------|---------|
| Forecasts | `data/outputs/weekly_forecasts.csv` |
| Monitoring results | `data/outputs/weekly_model_monitoring.csv` |
| Monitoring summary | `data/outputs/weekly_monitoring_summary.csv` |
| Model registry | `models/model_registry.csv` |
| Forecast visualisation | `notebooks/15_weekly_forecast_analysis.ipynb` |
| Monitoring review | `notebooks/14_model_monitoring.ipynb` |

---

## Rules to Remember

- **Never change the cutoff date to get a better WAPE** — it is a business decision, not a tuning knob
- **Only one model can be `best`** in the registry at a time
- **Name retrained models** with the date: `weekly_model_v3_calendar_YYYY_MM`
- **Run all scripts from the project root** with `PYTHONPATH=.`
- **Don't skip Saturday uploads** — if actuals are missing, notebook 14 cannot evaluate the forecast
