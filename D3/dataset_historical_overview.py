# dataset_historical_overview.py
# Standalone application for Dataset Historical Overview
import os
import streamlit as st
import pandas as pd
import plotly.express as px

LOCAL_CSV_PATH = "HouseTS.csv"
RATIO_COL = "price_to_income_ratio"
AFFORDABILITY_THRESHOLD = 3.0
AFFORDABILITY_CATEGORIES = {
    "Affordable": (None, 3.0), "Moderately Unaffordable": (3.0, 4.0), 
    "Seriously Unaffordable": (4.0, 5.0), "Severely Unaffordable": (5.0, 8.9), 
    "Impossibly Unaffordable": (8.9, None),
}
AFFORDABILITY_COLORS = {
    "Affordable": "#4CAF50", "Moderately Unaffordable": "#FFC107", 
    "Seriously Unaffordable": "#FF9800", "Severely Unaffordable": "#E57373", 
    "Impossibly Unaffordable": "#B71C1C",
}

@st.cache_data(ttl=3600*24)
def load_data() -> pd.DataFrame:
    """Loads and standardizes data."""
    script_dir = os.path.dirname(__file__)
    local_file_path = os.path.join(script_dir, LOCAL_CSV_PATH)
    
    df = pd.DataFrame() 
    
    if os.path.exists(local_file_path):
        df = pd.read_csv(local_file_path)
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


# Make city view data
def make_city_view_data(df_full: pd.DataFrame, annual_income: float, year: int, budget_pct: float = 30):
    """Aggregates data for the bar chart."""
    df_year = df_full[df_full['year'] == year].copy()

    # Aggregate by the GeoJSON code ('city_geojson_code')
    city_agg = df_year.groupby("city_geojson_code").agg(
        median_sale_price=("median_sale_price", "median"), 
        per_capita_income=("per_capita_income", "median"), 
        city_full=("city_full", "first"), 
    ).reset_index()

    city_agg[RATIO_COL] = city_agg["median_sale_price"] / (city_agg["per_capita_income"] * 2.51)
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



# ---------- Global config ----------
st.set_page_config(page_title="Dataset Historical Overview", layout="wide")
st.title("Dataset Historical Overview")

# Inject CSS
st.markdown(
    """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    <style>
    [data-testid="stAlert"] { display: none !important; }
    /* Optional: Global tightening */
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_data(ttl=3600*24)
def get_data_cached():
    """Load and cache the data."""
    return load_data()

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

@st.cache_data
def calculate_median_ratio_history(dataframe):
    """Calculate median price-to-income ratio over time."""
    years = sorted(dataframe["year"].unique())
    history_data = []
    for yr in years:
        city_data_yr = make_city_view_data(dataframe, annual_income=0, year=yr, budget_pct=30)
        if not city_data_yr.empty and RATIO_COL in city_data_yr.columns:
            median_ratio = city_data_yr[RATIO_COL].median()
            history_data.append({"year": yr, "median_ratio": median_ratio})
    return pd.DataFrame(history_data)

@st.cache_data
def calculate_category_proportions_history(dataframe):
    """Calculates the % composition of affordability tiers over time."""
    years = sorted(dataframe["year"].unique())
    history_data = []
    
    def classify_strict(ratio):
        if ratio < 3.0: return "Affordable (<3.0)"
        elif ratio <= 4.0: return "Moderately Unaffordable (3.1-4.0)"
        elif ratio <= 5.0: return "Seriously Unaffordable (4.1-5.0)"
        elif ratio <= 9.0: return "Severely Unaffordable (5.1-9.0)" 
        else: return "Impossibly Unaffordable (>9.0)"

    category_order = [
        "Affordable (<3.0)", 
        "Moderately Unaffordable (3.1-4.0)", 
        "Seriously Unaffordable (4.1-5.0)", 
        "Severely Unaffordable (5.1-9.0)", 
        "Impossibly Unaffordable (>9.0)"
    ]

    for yr in years:
        city_data_yr = make_city_view_data(dataframe, annual_income=0, year=yr, budget_pct=30)
        if not city_data_yr.empty and RATIO_COL in city_data_yr.columns:
            city_data_yr["cat"] = city_data_yr[RATIO_COL].apply(classify_strict)
            counts = city_data_yr["cat"].value_counts(normalize=True) * 100
            for cat in category_order:
                history_data.append({
                    "year": yr,
                    "category": cat,
                    "percentage": counts.get(cat, 0.0)
                })

    return pd.DataFrame(history_data)


# ---------- Load data ----------
df = get_data_cached()
if df.empty:
    st.error("Application cannot run. Base data (df) is empty.")
    st.stop()


# ---------- Calculate Histories ----------
df_history = calculate_median_ratio_history(df)
df_prop_history = calculate_category_proportions_history(df)

# ---------- Dataset Historical Overview Section ----------
st.markdown("---")
st.markdown("### Dataset Historical Overview")

with st.container(border=True):

    st.markdown("##### Distribution of Affordability Categories Over Time")
        
    custom_colors = {
    "Affordable (<3.0)": "green",
    "Moderately Unaffordable (3.1-4.0)": "#FFD700",
    "Seriously Unaffordable (4.1-5.0)": "orange",
    "Severely Unaffordable (5.1-9.0)": "red",
    "Impossibly Unaffordable (>9.0)": "maroon"
    }

    fig_prop = px.line(
        df_prop_history,
        x="year",
        y="percentage",
        color="category",
        color_discrete_map=custom_colors,
        markers=True,
        labels={"percentage": "% of Metro Areas", "year": "Year", "category": "Category"},
        height=300
        )
    fig_prop.update_layout(
        margin=dict(l=20, r=20, t=10, b=10),
        yaxis_title="% of Cities",
        legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.6,
        xanchor="center",
        x=0.5
        )
    )
    st.plotly_chart(fig_prop, use_container_width=True)

