"""
train_stockout.py

Train and save the stockout classification model for SunnyBest.
"""

from __future__ import annotations

from pathlib import Path
import joblib
import numpy as np

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

# project imports
from src.data.make_dataset import build_merged_dataset
from src.features.build_features import build_stockout_features


# -----------------------------
# Config
# -----------------------------
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "stockout_classifier.pkl"
RANDOM_STATE = 42


# -----------------------------
# Training
# -----------------------------
def train_stockout_model() -> dict:
    """
    Train stockout classifier and save it.
    Returns training metrics.
    """

    # Load merged data
    df = build_merged_dataset(save=False)

    # Build features
    X, y = build_stockout_features(df, target="stockout_occurred")

    # If stockouts are extremely rare, model training can be unstable.
    # We'll check class balance so you see what is happening.
    pos_rate = float(y.mean())
    if pos_rate == 0.0:
        raise ValueError("No stockouts found (target all zeros). Regenerate data or adjust stockout logic.")
    if pos_rate == 1.0:
        raise ValueError("All rows are stockouts (target all ones). Data generation likely wrong.")

    # Train/validation split (stratified to keep class balance)
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y
    )

    # Model (handles imbalance via scale_pos_weight)
    # scale_pos_weight = negatives / positives
    n_pos = int(y_train.sum())
    n_neg = int((y_train == 0).sum())
    scale_pos_weight = n_neg / max(1, n_pos)

    model = XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        scale_pos_weight=scale_pos_weight
    )

    # Fit
    model.fit(X_train, y_train)

    # Predict
    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1]

    # Metrics
    acc = accuracy_score(y_val, y_pred)
    f1 = f1_score(y_val, y_pred)

    # ROC AUC only valid if both classes exist in y_val
    if len(np.unique(y_val)) == 2:
        auc = roc_auc_score(y_val, y_proba)
    else:
        auc = float("nan")

    # Save
    joblib.dump(model, MODEL_PATH)

    print(f"✅ Stockout model saved to: {MODEL_PATH}")
    print(f"Class positive rate (stockout): {pos_rate:.3%}")
    print(f"📊 Accuracy: {acc:.4f} | F1: {f1:.4f} | ROC-AUC: {auc:.4f}")

    return {
        "pos_rate": pos_rate,
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_features": X.shape[1],
    }


# -----------------------------
# CLI entry
# -----------------------------
if __name__ == "__main__":
    metrics = train_stockout_model()
    print("Training summary:", metrics)
