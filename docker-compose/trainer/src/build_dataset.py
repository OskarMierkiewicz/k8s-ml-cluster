import os
import pandas as pd

def build_dataset(
    prices_path: str,
    inflation_path: str,
    out_path: str,
) -> pd.DataFrame:
    """
    Oczekiwany output:
    powiat_code, year, quarter, price_m2 (y), inflation_core_q (X), ... inne X
    """
    prices = pd.read_csv(prices_path)
    infl = pd.read_csv(inflation_path)

    # Minimalny join po year+quarter (inflacja jest wspólna)
    df = prices.merge(infl, on=["year", "quarter"], how="left")

    # TODO: dodaj swoje cechy (transakcje, metraż, bezrobocie roczne -> na kwartały)
    # TODO: ujednolić kody powiatów, typy, brakujące wartości

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    return df

if __name__ == "__main__":
    #TODO Przykładowe ścieżki — dopasuj do swoich plików
    build_dataset(
        prices_path="/app/data/raw/prices_powiat_q.csv",
        inflation_path="/app/data/raw/inflacja_kwartalna_model.csv",
        out_path="/app/data/processed/dataset_powiat_q.csv",
    )