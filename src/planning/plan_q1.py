# from __future__ import annotations

# import joblib

# from data.make_weekly_dataset import build_merged_dataset
# from src.features.build_features import build_forecast_features
# from src.forecasting.history_window import select_history_window
# from src.forecasting.future_frame import build_future_frame, BaselineAssumptions
# from src.forecasting.recursive_forecast import recursive_forecast_revenue
# from src.forecasting.aggregate import aggregate_monthly


# def run_revenue_plan(
#     *,
#     anchor_date: str,
#     start_date: str,
#     end_date: str,
#     history_months: int = 6,
#     discount_pct: float = 0.0,
#     promo_flag: int = 0,
#     model_path: str = "models/xgb_revenue_forecast.pkl",
# ) -> dict:
#     """
#     Planning runner:
#     Returns monthly totals for planning (AVW-style).
#     """

#     df = build_merged_dataset(save=False)

#     hist = select_history_window(df, months=history_months, anchor_date=anchor_date)

#     assumptions = BaselineAssumptions(promo_flag=promo_flag, discount_pct=discount_pct)
#     future = build_future_frame(hist, start_date, end_date, assumptions=assumptions)

#     model = joblib.load(model_path)

#     fut_pred = recursive_forecast_revenue(
#         history_df=hist,
#         future_df=future,
#         model=model,
#         build_features_fn=build_forecast_features,
#         target="revenue",
#     )

#     monthly_total = aggregate_monthly(fut_pred)

#     return {
#         "anchor_date": anchor_date,
#         "start_date": start_date,
#         "end_date": end_date,
#         "history_months": history_months,
#         "assumptions": {"promo_flag": promo_flag, "discount_pct": discount_pct},
#         "monthly_total": monthly_total.to_dict(orient="records"),
#     }