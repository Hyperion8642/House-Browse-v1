# Part of Jason's code finished on Nov 25 2025
import pandas as pd
import numpy as np
import os
import json
import streamlit as st

HOUSE_CSV = "HouseTS.csv"
CITY_GEOJSON_DIR = "city_geojson"

@st.cache_data(ttl=24*3600)
def load_house_data():
    df = pd.read_csv(HOUSE_CSV)
    
    rename_map = {}
    if "Median Rent" in df.columns:
        rename_map["Median Rent"] = "median_rent"
    if "Per Capita Income" in df.columns:
        rename_map["Per Capita Income"] = "per_capita_income"
    if "zip_code" in df.columns and "zipcode" not in df.columns:
        rename_map["zip_code"] = "zipcode"
    df = df.rename(columns=rename_map)

    df["zip_code_str"] = df["zipcode"].astype(str).str.zfill(5)
    df["monthly_income"] = df.get("per_capita_income", pd.Series(np.nan)) / 12.0
    df["ratio"] = df["median_rent"] / (0.3 * df["monthly_income"])
    df["ratio"] = df["ratio"].replace([np.inf, -np.inf], np.nan)
    
    if "city" not in df.columns:
        raise KeyError("HouseTS.csv must contain a 'city' column.")
    
    return df

@st.cache_data(ttl=24*3600)
def build_city_bars(df):
    return (
        df.groupby("city", as_index=False)
          .agg(
              avg_ratio=("ratio", "median"),
              avg_rent=("median_rent", "median"),
              avg_income=("monthly_income", "median"),
              count=("zip_code_str", "nunique")
          )
          .sort_values("avg_ratio", ascending=False)
    )

@st.cache_data(ttl=24*3600)
def load_city_geojson(city):
    path = os.path.join(CITY_GEOJSON_DIR, f"{city}.geojson")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
