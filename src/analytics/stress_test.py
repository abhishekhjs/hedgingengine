"""Stress Testing Analytics — apply manual market shocks to the risk engine."""
import copy
import pandas as pd
from typing import Optional


def apply_stress_scenario(
    market_data: dict,
    shocks: list[dict],
) -> dict:
    """
    Apply manual market shocks to a market_data dict.

    shocks: list of dicts with keys:
        - asset:       e.g. "USDJPY", "COPPER"
        - shock_type:  "pct" or "absolute"
        - shock_value: float (e.g. -0.10 for -10%, or 160.0 for absolute)

    Returns a deep-copied, shocked market_data dict.
    """
    shocked = copy.deepcopy(market_data)
    for shock in shocks:
        asset = shock.get("asset", "").strip().upper()
        shock_type = shock.get("shock_type", "pct")
        shock_value = float(shock.get("shock_value", 0.0))

        if asset not in shocked:
            continue

        current = shocked[asset].get("price", shocked[asset].get("rate", 0.0))
        if shock_type == "pct":
            new_price = current * (1.0 + shock_value)
        else:
            new_price = shock_value

        # Update whichever key holds the price
        if "price" in shocked[asset]:
            shocked[asset]["price"] = new_price
        elif "rate" in shocked[asset]:
            shocked[asset]["rate"] = new_price

    return shocked


def build_shock_table(market_data: dict) -> pd.DataFrame:
    """
    Build the editable shock input DataFrame from current market data.
    Returns a DataFrame the user can edit in st.data_editor.
    """
    rows = []
    for asset, data in market_data.items():
        price = data.get("price") or data.get("rate") or 0.0
        rows.append({
            "Asset": asset,
            "Current Price": round(price, 4),
            "Shock Type": "pct",
            "Shock Value (%)": 0.0,
            "Shocked Price": round(price, 4),
        })
    return pd.DataFrame(rows)


def compute_shocked_price(row: pd.Series) -> float:
    """Compute the post-shock price for display in the grid."""
    current = row["Current Price"]
    shock_type = row["Shock Type"]
    value = row["Shock Value (%)"]
    if shock_type == "pct":
        return round(current * (1.0 + value / 100.0), 4)
    else:
        return round(value, 4)
