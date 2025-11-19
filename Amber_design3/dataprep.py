# dataprep.py
"""
Data loading and preparation helpers for Design 3 (HouseTS dataset).
"""

import pandas as pd
import numpy as np

CSV_PATH = "HouseTS.csv"


def load_data(path: str = CSV_PATH) -> pd.DataFrame:
    """
    Load HouseTS.csv and compute key derived fields.

    Returns a row-level dataframe with:
    - parsed date
    - city_clean  (for plotting)
    - monthly_income_pc (Per Capita Income / 12)
    """
    df = pd.read_csv(path)

    # ensure datetime
    df["date"] = pd.to_datetime(df["date"])

    df["city_clean"] = df["city"]

    # per-capita monthly income
    df["monthly_income_pc"] = df["Per Capita Income"] / 12.0

    return df


def make_city_view_data(
    df: pd.DataFrame,
    annual_income: float,
    year: int | None = None,
    budget_pct: float = 30.0,
) -> pd.DataFrame:
    """
    Aggregate data to city level for a given income, year and housing budget %.

    Returns one row per city with at least:
    - city_clean
    - Median Rent
    - Per Capita Income
    - Total Population
    - monthly_income_city
    - afford_ratio_dyn   (rent / max_rent under current rule)
    - afford_gap         (afford_ratio_dyn - 1, >0 = unaffordable)
    - affordable         (True / False)
    - year, user_income, user_max_rent, budget_pct
    """
    if year is None:
        year = int(df["year"].max())

    # housing budget rule: max affordable monthly rent
    max_rent = annual_income * (budget_pct / 100.0) / 12.0

    tmp = df[df["year"] == year].copy()

    # aggregate by city 
    city_agg = (
        tmp.groupby("city", as_index=False)
        .agg(
            {
                "Median Rent": "median",
                "Per Capita Income": "median",
                "Total Population": "sum",
            }
        )
        .rename(columns={"city": "city_clean"})
    )

    # city-level monthly income
    city_agg["monthly_income_city"] = city_agg["Per Capita Income"] / 12.0

    # 动态 affordability ratio & gap
    city_agg["user_max_rent"] = max_rent
    city_agg["afford_ratio_dyn"] = city_agg["Median Rent"] / max_rent
    city_agg["afford_gap"] = city_agg["afford_ratio_dyn"] - 1.0  # >0 = unaffordable

    city_agg["affordable"] = city_agg["afford_ratio_dyn"] <= 1.0

    city_agg["budget_pct"] = budget_pct
    city_agg["year"] = year
    city_agg["user_income"] = annual_income

    return city_agg.sort_values("city_clean").reset_index(drop=True)


def make_city_history(df: pd.DataFrame, city_name: str) -> pd.DataFrame:
    """
    For a selected city, return year-level history (optional drill-down):

    - Median Rent
    - Per Capita Income
    - afford_ratio_30 (fixed 30% rule)
    """
    tmp = df[df["city"] == city_name].copy()

    tmp["monthly_income_city"] = tmp["Per Capita Income"] / 12.0
    tmp["max_rent_30"] = tmp["monthly_income_city"] * 0.3
    tmp["afford_ratio_30"] = tmp["Median Rent"] / tmp["max_rent_30"]

    hist = (
        tmp.groupby("year", as_index=False)
        .agg(
            {
                "Median Rent": "median",
                "Per Capita Income": "median",
                "afford_ratio_30": "median",
            }
        )
        .sort_values("year")
    )
    return hist


def make_zip_view_data(
    df: pd.DataFrame,
    city_name: str,
    annual_income: float,
    year: int | None = None,
    budget_pct: float = 30.0,
) -> pd.DataFrame:
    """
    Zip-level view inside a city for a given income & year.
    """
    if year is None:
        year = int(df["year"].max())

    max_rent = annual_income * (budget_pct / 100.0) / 12.0

    tmp = df[(df["city"] == city_name) & (df["year"] == year)].copy()

    if tmp.empty:
        return tmp

    zip_agg = (
        tmp.groupby("zipcode", as_index=False)
        .agg(
            {
                "Median Rent": "median",
                "Per Capita Income": "median",
            }
        )
    )
    zip_agg["user_max_rent"] = max_rent
    zip_agg["afford_ratio_zip"] = zip_agg["Median Rent"] / max_rent
    zip_agg["afford_gap_zip"] = zip_agg["afford_ratio_zip"] - 1.0
    zip_agg["affordable"] = zip_agg["afford_ratio_zip"] <= 1.0

    return zip_agg.sort_values("Median Rent")
