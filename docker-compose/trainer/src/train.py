import argparse
import os
import json
import joblib
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor

from src.build_dataset import build_dataset

def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))

def main(from_year: int, to_year: int):
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    exp_name = os.environ.get("MLFLOW_EXPERIMENT_NAME", "housing-pl")

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(exp_name)

    #TODO 1) Zbuduj dataset (tu podmień na swoje realne pliki)
    dataset_path = "/app/data/processed/dataset_powiat_q.csv"
    if not os.path.exists(dataset_path):
        build_dataset(
            prices_path="/app/data/raw/prices_powiat_q.csv",
            inflation_path="/app/data/raw/inflacja_kwartalna_model.csv",
            out_path=dataset_path,
        )

    df = pd.read_csv(dataset_path)
    
    #TODO Check 
    # Minimalne wymagane kolumny:
    # powiat_code, year, quarter, price_m2, inflation_core_q
    required = {"powiat_code", "year", "quarter", "price_m2", "inflation_core_q"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Brakuje kolumn w dataset: {missing}")

    df = df[(df["year"] >= from_year) & (df["year"] <= to_year)].copy()
    df = df.sort_values(["year", "quarter", "powiat_code"]).reset_index(drop=True)

    # Cechy (na start minimalnie):
    feature_cols = ["inflation_core_q", "year", "quarter"]
    X = df[feature_cols]
    y = df["price_m2"].astype(float)

    # TimeSeriesSplit po czasie (prosto, bez grupowania po powiatach)
    tscv = TimeSeriesSplit(n_splits=5)

    model = RandomForestRegressor(
        n_estimators=400,
        random_state=42,
        n_jobs=-1
    )

    #TODO 2) Trening + walidacja
    rmses, maes, r2s = [], [], []
    for train_idx, test_idx in tscv.split(X):
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        pred = model.predict(X.iloc[test_idx])

        rmses.append(rmse(y.iloc[test_idx], pred))
        maes.append(float(mean_absolute_error(y.iloc[test_idx], pred)))
        r2s.append(float(r2_score(y.iloc[test_idx], pred)))

    metrics = {
        "rmse_mean": float(np.mean(rmses)),
        "mae_mean": float(np.mean(maes)),
        "r2_mean": float(np.mean(r2s)),
    }

    # 3) Fit na całości
    model.fit(X, y)

    # 4) Log do MLflow
    with mlflow.start_run(run_name="rf_powiat_q"):
        mlflow.log_params({
            "model": "RandomForestRegressor",
            "features": ",".join(feature_cols),
            "from_year": from_year,
            "to_year": to_year,
        })
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, artifact_path="model")

        #TODO 5) Zapis modelu lokalnie (opcjonalnie)
        os.makedirs("/app/models", exist_ok=True)
        joblib.dump(model, "/app/models/model.joblib")

        os.makedirs("/app/reports", exist_ok=True)
        with open("/app/reports/metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

    # 6) Export predykcji do mapy: powiat + ostatni kwartał w danych
    last = df.sort_values(["year", "quarter"]).iloc[-1][["year", "quarter"]]
    last_year, last_q = int(last["year"]), int(last["quarter"])

    df_last = df[(df["year"] == last_year) & (df["quarter"] == last_q)].copy()
    X_last = df_last[feature_cols]
    df_last["predicted_price_m2"] = model.predict(X_last)

    out_dir = "/app/data/published"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"pred_powiat_{last_year}_Q{last_q}.csv")
    df_last[["powiat_code", "year", "quarter", "predicted_price_m2"]].to_csv(out_path, index=False)

    print("DONE. Metrics:", metrics)
    print("Published:", out_path)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-year", type=int, default=2010)
    ap.add_argument("--to-year", type=int, default=2025)
    args = ap.parse_args()
    main(args.from_year, args.to_year)