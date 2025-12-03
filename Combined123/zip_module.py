# Updated code to add back zip code filtering when adjusting income slider

import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import pgeocode
from dataprep import RATIO_COL, RATIO_COL_ZIP, AFFORDABILITY_CATEGORIES 


# Helper function (copied from dataprep.py)
def classify_affordability_zip(ratio: float) -> str:
    """Classifies a price-to-income ratio using imported constants."""
    if pd.isna(ratio): return "N/A"
    
    sorted_categories = sorted(AFFORDABILITY_CATEGORIES.items(), 
                               key=lambda item: item[1][1] if item[1][1] is not None else float('inf'))

    for category, (lower, upper) in sorted_categories:
        if category == "Affordable":
            if ratio <= upper: return category
        elif lower is not None and upper is not None:
            if lower < ratio <= upper: return category
        elif lower is not None and upper is not None:
            if lower < ratio <= upper: return category
            
    return "Uncategorized"


@st.cache_data(ttl=3600)
def load_city_zip_data(city_geojson_code: str, df_full: pd.DataFrame, max_pci: float) -> pd.DataFrame:
    # ------------------------------------------------------------------------
    # FIX: Added max_pci argument for filtering
    # ------------------------------------------------------------------------
    """
    Filters the pre-loaded full DataFrame (df_full) to a single city 
    using the GeoJSON code (e.g., ATL) AND filters ZIP codes by max_pci.
    """
    # 1. Filter by City (GeoJSON Code)
    df_city_zip = df_full[df_full["city_geojson_code"] == city_geojson_code].copy()

    # 2. Hard Filter by Income (NEW LOGIC)
    # Only keep ZIP codes where the per_capita_income is <= user's annual income
    df_city_zip = df_city_zip[df_city_zip["per_capita_income"] <= max_pci].copy()


    # Ensure the required columns exist for subsequent steps
    required_cols = ["zipcode", "year", "median_sale_price", "per_capita_income", "city_full"]
    for col in required_cols:
        if col not in df_city_zip.columns:
            return pd.DataFrame() 

    # Ensure zip code columns exist
    df_city_zip["zip_code_int"] = df_city_zip["zipcode"].astype(str).str.zfill(5)
    df_city_zip["zip_code_str"] = df_city_zip["zipcode"].astype(str).str.zfill(5)

    return df_city_zip


@st.cache_data(ttl=3600*24)
def get_zip_coordinates(df_zip_data: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches ZIP-level data with coordinates and unconditionally calculates the ratio AND rating.
    """
    if df_zip_data.empty:
        return pd.DataFrame()

    out = df_zip_data.copy()
    
    # Use pgeocode for coordinates
    nomi = pgeocode.Nominatim("us")
    
    # Extract list of zip codes
    zip_list = out["zip_code_str"].tolist()
    
    # Query pgeocode for all ZIPs
    geo_df = nomi.query_postal_code(zip_list)
    
    # Add lat/lon back to DataFrame
    out["lat"] = geo_df["latitude"].values
    out["lon"] = geo_df["longitude"].values

    out = out.dropna(subset=["lat", "lon"]).copy()

    # Calculate ratio using standardized lowercase columns
    price_col = "median_sale_price"
    income_col = "per_capita_income"
    denom = out[income_col].replace(0, np.nan)
    
    out[RATIO_COL] = out[price_col] / denom # Generates 'price_to_income_ratio'
    out["affordability_rating"] = out[RATIO_COL].apply(classify_affordability_zip) # Generates rating
    
    # Ensure zip_code_int exists for Plotly location lookup
    out["zip_code_int"] = out["zip_code_str"].astype(int)
    
    return out
