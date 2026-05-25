# SESSION NOTES — SunnyBest AI Retail Forecasting System
> Running log of working sessions. Add a new entry at the top each time you sit down.

---

## 2026-05-25

### What I worked on
- Created `16_demand_sensing.ipynb` — demand sensing notebook
- Created `17_inventory_optimisation.ipynb` — inventory optimisation notebook
- Reviewed forecast pipeline and `weekly_forecasts.csv`

### Key findings
- Forecast file (`data/outputs/weekly_forecasts.csv`) has 3 weeks: 2026-03-30, 2026-05-04, 2026-05-11
- All 3 are now in the past — actuals can be uploaded and monitoring run
- Current best model: `weekly_model_v3_calendar` (WAPE 0.1500). Note: v4_promotions was used for the March forecast but is now archived (worse WAPE: 0.1655)
- `15_weekly_forecast_analysis.ipynb` has a potential issue — needs investigation

### Left off at / To pick up next
- Review outputs of notebooks 16 and 17
- Investigate issue in `15_weekly_forecast_analysis.ipynb`
- Generate forecast for week of 2026-05-19 and 2026-05-26
- Run `14_model_monitoring.ipynb` against all 3 past forecast weeks

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
