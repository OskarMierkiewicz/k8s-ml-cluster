import os
import glob
import pandas as pd
from fastapi import FastAPI, HTTPException

#TODO check app

app = FastAPI()

PUBLISHED_DIR = "/app/data/published"

def latest_pred_file() -> str:
    files = sorted(glob.glob(os.path.join(PUBLISHED_DIR, "pred_powiat_*_Q*.csv")))
    return files[-1] if files else ""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/latest")
def latest():
    f = latest_pred_file()
    if not f:
        raise HTTPException(404, "Brak plików w data/published. Uruchom trening.")
    return {"file": os.path.basename(f)}

@app.get("/prices")
def prices(year: int | None = None, quarter: int | None = None):
    """
    Zwraca listę: powiat_code, predicted_price_m2 dla wskazanego year+quarter.
    Jeśli brak parametrów -> bierze najnowszy plik.
    """
    if year is None or quarter is None:
        f = latest_pred_file()
        if not f:
            raise HTTPException(404, "Brak plików w data/published. Uruchom trening.")
        df = pd.read_csv(f)
        return df.to_dict(orient="records")

    f = os.path.join(PUBLISHED_DIR, f"pred_powiat_{year}_Q{quarter}.csv")
    if not os.path.exists(f):
        raise HTTPException(404, f"Nie znaleziono: {os.path.basename(f)}")
    df = pd.read_csv(f)
    return df.to_dict(orient="records")