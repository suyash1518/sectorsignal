# model/2_train_model.py  (improved — fixes class imbalance, better tuning)

import pandas as pd
import numpy as np
import pickle
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

FEATURE_COLS = [
    "pct_from_52w_high",
    "momentum_1m",
    "momentum_3m",
    "momentum_6m",
    "volatility",
    "mean_reversion",
    # Engineered features
    "mom_accel",        # momentum acceleration
    "vol_adj_mom",      # volatility-adjusted momentum
    "discount_score",   # how deep is the discount
]

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Momentum acceleration: is momentum improving?
    df["mom_accel"]     = df["momentum_1m"] - df["momentum_3m"] / 3
    # Volatility-adjusted momentum
    df["vol_adj_mom"]   = df["momentum_3m"] / (df["volatility"] + 1)
    # Discount score: deeper discount = higher score
    df["discount_score"] = df["pct_from_52w_high"].apply(lambda x: abs(min(x, 0)))
    return df

def load_data():
    df = pd.read_csv("training_data.csv", parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = engineer_features(df)
    print(f"Loaded {len(df)} rows with {len(FEATURE_COLS)} features")
    print(f"Label: BUY={df['label'].sum()} ({df['label'].mean()*100:.1f}%)  AVOID={(df['label']==0).sum()}")
    return df

def train_model(df: pd.DataFrame):
    X = df[FEATURE_COLS].fillna(0)
    y = df["label"]

    # Fix class imbalance with sample weights
    sample_weights = compute_sample_weight("balanced", y)

    tscv = TimeSeriesSplit(n_splits=5)

    # Scale = 3 because AVOID:BUY ratio ≈ 3:1
    scale = (y == 0).sum() / (y == 1).sum()

    models = {
        "XGBoost": XGBClassifier(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.7,
            scale_pos_weight=scale,   # fixes imbalance
            eval_metric="auc",
            random_state=42,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=3,
            class_weight="balanced",  # fixes imbalance
            random_state=42,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.03,
            subsample=0.8,
            random_state=42,
        ),
    }

    print("\n── Cross-validation (TimeSeriesSplit, 5 folds) ──")
    best_score, best_name, best_model = 0, None, None

    for name, model in models.items():
        scores = cross_val_score(model, X, y, cv=tscv, scoring="roc_auc")
        mean_score = scores.mean()
        print(f"  {name:20s} ROC-AUC: {mean_score:.3f} ± {scores.std():.3f}")
        if mean_score > best_score:
            best_score = mean_score
            best_name  = name
            best_model = model

    print(f"\nBest model: {best_name} (ROC-AUC: {best_score:.3f})")

    # Train on full data
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    best_model.fit(X_scaled, y, **({"sample_weight": sample_weights} if best_name != "GradientBoosting" else {}))

    # Evaluate on last 20% holdout
    split    = int(len(df) * 0.8)
    X_tr     = scaler.transform(X.iloc[:split])
    X_te     = scaler.transform(X.iloc[split:])
    y_tr     = y.iloc[:split]
    y_te     = y.iloc[split:]
    sw_tr    = sample_weights[:split]

    eval_model = type(best_model)(**best_model.get_params())
    eval_model.fit(X_tr, y_tr, **({"sample_weight": sw_tr} if best_name != "GradientBoosting" else {}))

    y_pred = eval_model.predict(X_te)
    y_prob = eval_model.predict_proba(X_te)[:, 1]

    accuracy = accuracy_score(y_te, y_pred)
    roc_auc  = roc_auc_score(y_te, y_prob)

    print(f"\n── Holdout Test Results (last 20%) ──")
    print(f"  Accuracy : {accuracy*100:.1f}%")
    print(f"  ROC-AUC  : {roc_auc:.3f}")
    print(f"\n{classification_report(y_te, y_pred, target_names=['AVOID','BUY'])}")

    return best_model, best_name, scaler, accuracy, roc_auc, y_te, y_pred, y_prob

def plot_confusion_matrix(y_test, y_pred, model_name):
    cm  = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["AVOID","BUY"], yticklabels=["AVOID","BUY"], ax=ax)
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("Actual", fontsize=12)
    ax.set_title(f"Confusion Matrix — {model_name}", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig("confusion_matrix.png", dpi=150)
    plt.close()
    print("Saved confusion_matrix.png")

def plot_feature_importance(model, model_name):
    if not hasattr(model, "feature_importances_"):
        return
    imp = model.feature_importances_
    feat_df = pd.DataFrame({"feature": FEATURE_COLS, "importance": imp}).sort_values("importance")
    colors  = ["#6366f1" if i == feat_df["importance"].idxmax() else "#94a3b8" for i in feat_df.index]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(feat_df["feature"], feat_df["importance"], color=colors)
    for bar, val in zip(bars, feat_df["importance"]):
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2, f"{val:.3f}", va="center", fontsize=9)
    ax.set_title(f"Feature Importance — {model_name}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Importance")
    plt.tight_layout()
    plt.savefig("feature_importance.png", dpi=150)
    plt.close()
    print("Saved feature_importance.png")

def save_model(model, scaler, model_name, accuracy, roc_auc):
    bundle = {
        "model": model, "scaler": scaler,
        "feature_cols": FEATURE_COLS,
        "model_name": model_name,
        "accuracy": accuracy, "roc_auc": roc_auc,
        "trained_at": pd.Timestamp.now().isoformat(),
        "buy_threshold": 0.45,
        "watch_threshold": 0.30,
    }
    with open("sector_model.pkl", "wb") as f:
        pickle.dump(bundle, f)
    print("Saved sector_model.pkl")

    with open("results.txt", "w") as f:
        f.write("SectorSignal — Model Results\n")
        f.write("="*40 + "\n")
        f.write(f"Model    : {model_name}\n")
        f.write(f"Accuracy : {accuracy*100:.1f}%\n")
        f.write(f"ROC-AUC  : {roc_auc:.3f}\n")
        f.write(f"Features : {', '.join(FEATURE_COLS)}\n")
        f.write(f"Fix      : class_weight=balanced (AVOID:BUY = 3:1)\n")
    print("Saved results.txt")

def main():
    print("="*60)
    print("SectorSignal — Model Training (Improved)")
    print("="*60)
    df = load_data()
    model, name, scaler, acc, auc, y_te, y_pred, y_prob = train_model(df)
    plot_confusion_matrix(y_te, y_pred, name)
    plot_feature_importance(model, name)
    save_model(model, scaler, name, acc, auc)
    print(f"\n{'='*60}")
    print(f"Done! Model: {name}  Accuracy: {acc*100:.1f}%  ROC-AUC: {auc:.3f}")
    print("Next: python 3_deploy_model.py")

if __name__ == "__main__":
    main()