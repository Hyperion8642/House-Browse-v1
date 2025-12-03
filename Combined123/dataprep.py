# dataprep.py

# --- File: dataprep.py (Final Fix for Bar Chart Data) ---
import pandas as pd
import numpy as np
import os
import streamlit as st
from typing import Optional

# --- Define Constants at the TOP LEVEL ---
LOCAL_CSV_PATH = "HouseTS.csv"
CSV_URL = "https://github.com/yyy1029/House-Browse/releases/download/v1.0/HouseTS.csv"
RATIO_COL = "price_to_income_ratio"
RATIO_COL_ZIP = "price_to_income_ratio_zip"
AFFORDABILITY_THRESHOLD = 3.0
AFFORDABILITY_CATEGORIES = {
    "Affordable": (None, 3.0), "Moderately Unaffordable": (3.0, 4.0), 
    "Seriously Unaffordable": (4.0, 5.0), "Severely Unaffordable": (5.0, 8.9), 
    "Impossibly Unaffordable": (8.9, None),
}
AFFORDABILITY_COLORS = {
    "Affordable": "green", "Moderately Unaffordable": "yellowgreen", 
    "Seriously Unaffordable": "orange", "Severely Unaffordable": "red", 
    "Impossibly Unaffordable": "darkred",
}

def classify_affordability(ratio: float) -> str:
    """Classifies a price-to-income ratio."""
    if pd.isna(ratio): return "N/A"
    
    sorted_categories = sorted(AFFORDABILITY_CATEGORIES.items(), 
                               key=lambda item: item[1][1] if item[1][1] is not None else float('inf'))

    for category, (lower, upper) in sorted_categories:
        if category == "Affordable":
            if ratio <= upper: return category
        elif lower is not None and upper is None:
            if ratio > lower: return category
        elif lower is not None and upper is not None:
            if lower < ratio <= upper: return category
            
    return "Uncategorized"

@st.cache_data(ttl=3600*24)
def load_data() -> pd.DataFrame:
    """Loads and standardizes data."""
    script_dir = os.path.dirname(__file__)
    local_file_path = os.path.join(script_dir, LOCAL_CSV_PATH)
    
    df = pd.DataFrame() 
    
    if os.path.exists(local_file_path):
        df = pd.read_csv(local_file_path)
        # st.info("Loaded data from local file: HouseTS.csv")
    else:
        try:
            df = pd.read_csv(CSV_URL)
            st.warning(f"Local file not found. Loaded data from URL: {CSV_URL}")
        except Exception as e:
            st.error(f"🔴 CRITICAL: Failed to load data from local path or URL. Check file path/internet: {e}")
            return pd.DataFrame() 

    if df.empty:
        st.error("🔴 CRITICAL: Data file is empty after loading.")
        return pd.DataFrame()

    # --- Standardize Column Names ---
    df.rename(
        columns={
            "median_sale_price": "median_sale_price",
            "per_capita_income": "per_capita_income",
            "Median Sale Price": "median_sale_price",
            "Per Capita Income": "per_capita_income",
            "city": "city_geojson_code"  # Preserve original code (ATL) here
        },
        inplace=True,
    )
    
    if "city_full" not in df.columns:
        df["city_full"] = df["city_geojson_code"] + " Metro Area"

    df['city_clean'] = df['city_geojson_code'] 

    df["monthly_income_pc"] = df["per_capita_income"] / 12.0

    return df


def apply_income_filter(df: pd.DataFrame, annual_income: float) -> pd.DataFrame:
    """Returns the base DataFrame (no hard filter) for map context."""
    return df.copy() # NOTE: Returns copy of full data for map context


@st.cache_data(ttl=3600*24)
def make_city_view_data(df_full: pd.DataFrame, annual_income: float, year: int, budget_pct: float = 30):
    """Aggregates data for the bar chart."""
    df_year = df_full[df_full['year'] == year].copy()

    # Aggregate by the GeoJSON code ('city_geojson_code')
    city_agg = df_year.groupby("city_geojson_code").agg(
        median_sale_price=("median_sale_price", "median"), 
        per_capita_income=("per_capita_income", "median"), 
        city_full=("city_full", "first"), 
    ).reset_index()

    city_agg[RATIO_COL] = city_agg["median_sale_price"] / city_agg["per_capita_income"]
    city_agg["affordability_rating"] = city_agg[RATIO_COL].apply(classify_affordability)
    city_agg["affordable"] = city_agg[RATIO_COL] <= AFFORDABILITY_THRESHOLD

    # Rename columns for display in charts/tables
    city_agg.rename(
        columns={
            "median_sale_price": "Median Sale Price", "per_capita_income": "Per Capita Income",
            "city_geojson_code": "city", # 'city' holds the GeoJSON code (e.g., ATL) for bar chart x-axis
        },
        inplace=True,
    )

    return city_agg


def make_city_history(df: pd.DataFrame, city_name: str) -> pd.DataFrame:
    """
    Return year-level history for a selected city:
    """
    # NOTE: This uses the GeoJSON code for filtering
    tmp = df[df["city_geojson_code"] == city_name].copy() 

    if tmp.empty:
        return tmp

    denom = tmp["per_capita_income"].replace(0, np.nan)
    tmp["price_to_income_ratio_by_year"] = tmp["median_sale_price"] / denom

    hist = (
        tmp.groupby("year", as_index=False)
        .agg(
            {
                "median_sale_price": "median",
                "per_capita_income": "median",
                "price_to_income_ratio_by_year": "median",
            }
        )
        .sort_values("year")
    )
    return hist


def make_zip_view_data(
    df: pd.DataFrame,
    city_name: str,
    annual_income: float,
    year: Optional[int] = None,
    budget_pct: float = 30.0,
) -> pd.DataFrame:
    """
    Produce ZIP-level price-to-income ratio for a given city & year.
    (This function is defined but unused, as the logic is in zip_module)
    """
    # This function is a placeholder definition required for app_v2.py imports
    return pd.DataFrame()


