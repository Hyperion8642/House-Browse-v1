# Code Jason finished on Nov 25
import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from streamlit_plotly_events import plotly_events
from data_loader import load_house_data, load_city_geojson 

# --- Configuration ---
st.set_page_config(page_title="Design 3 – Price Affordability Finder", layout="wide")
st.title("Design 3 – Price Affordability Finder")

# Define new ratio column names for consistency
PRICE_COL = "Median Sale Price"
INCOME_COL = "Per Capita Income"
RATIO_COL = "price_to_income_ratio"


# --- Cached Data Loading Functions ---
@st.cache_data(ttl=24*3600)
def cached_house_data():
    df = load_house_data()
    # Ensure necessary columns are present and correctly named
    df = df.rename(columns={
        "median_sale_price": PRICE_COL, # New column for sale price
        "per_capita_income": INCOME_COL,
        "median_rent": "Median Rent Old" # Keep old rent data for reference if needed
    })
    
    # Calculate the Price-to-Income ratio on the base data (ZIP level)
    # Use 10x multiplier to make the ratio values more interpretable (e.g., house price is X times annual income)
    df[RATIO_COL] = df[PRICE_COL] / df[INCOME_COL]
    
    return df

@st.cache_data(ttl=24*3600)
def cached_city_geojson(city):
    return load_city_geojson(city)

# --- Load Base Data ---
with st.spinner("Loading housing data…"):
    df = cached_house_data()


# ----------------------------------------------------
#               I. Sidebar & Top Controls
# ----------------------------------------------------

# --- A. Sidebar: Persona + Income (Simplified) ---
st.sidebar.header("Who are you?")
persona = st.sidebar.radio("Choose a profile", ["Student", "Young professional", "Family"], index=1, key="persona")
st.sidebar.header("Budget settings")
final_income = st.sidebar.number_input(
    "Annual Income ($)", 
    min_value=10000, 
    max_value=300000, 
    value=90000, 
    step=1000,
    key="final_income_input"
)
st.sidebar.markdown(
    """
    **Ratio Rule**
    We assume lower ratios are better for home price affordability (Sale Price / Per Capita Income).
    """
)
# Since we are focusing on Price-to-Income ratio, max_rent calculation is irrelevant to charts, 
# but kept to satisfy profile card display logic.
monthly_inc = final_income / 12.0
max_rent = monthly_inc * 0.3


# --- B. Top Controls: Year selector & Sort option ---
top_col1, top_col2 = st.columns([1, 2])
with top_col1:
    years = sorted(df["year"].unique())
    selected_year = st.selectbox("Year", years, index=len(years) - 1, key="year_main")

with top_col2:
    sort_option = st.selectbox(
        "Sort cities by",
        ["City name", "Price to Income Ratio", PRICE_COL, INCOME_COL], # Updated options
        key="sort_main",
    )

# --- Filter Data by Year ---
dfy = df[df["year"] == selected_year].copy()


# ----------------------------------------------------
#           II. Data Aggregation & Sorting (Price-to-Income)
# ----------------------------------------------------

with st.spinner("Aggregating city-level data…"):
    # Aggregate city-level data: Median Price and Income
    city_agg = (
        dfy.groupby("city", as_index=False)
            .agg(
                **{
                    PRICE_COL: (PRICE_COL, "median"), # Aggregate median sale price
                    INCOME_COL: (INCOME_COL, "median"), # Aggregate median per capita income
                    "total_zips": ("zip_code_str", "nunique")
                }
            )
    )
    
    # Calculate the Price-to-Income ratio at the city level
    city_agg[RATIO_COL] = city_agg[PRICE_COL] / city_agg[INCOME_COL]
    
    # Affordability Metric (Arbitrary threshold for coloring: e.g., ratio < 5.0 is 'affordable')
    AFFORDABILITY_THRESHOLD = 5.0 
    city_agg["affordable"] = city_agg[RATIO_COL] < AFFORDABILITY_THRESHOLD
    
    # gap_for_plot is now just the ratio itself for easy sorting/plotting
    city_agg["gap_for_plot"] = city_agg[RATIO_COL] 
    city_agg["city_clean"] = city_agg["city"]

# --- Sort Data ---
if sort_option == "Price to Income Ratio":
    # Ascending=True places lower ratios (more affordable) at the top/right
    sorted_data = city_agg.sort_values(RATIO_COL, ascending=True) 
elif sort_option == PRICE_COL:
    sorted_data = city_agg.sort_values(PRICE_COL, ascending=False)
elif sort_option == INCOME_COL:
    sorted_data = city_agg.sort_values(INCOME_COL, ascending=False)
else:  # City name
    sorted_data = city_agg.sort_values("city_clean")


# ----------------------------------------------------
#           III. Layout: Profile Card & Bar Chart
# ----------------------------------------------------

col1, col2 = st.columns([1, 2])

with col1:
    # Profile Card (Still shows the Rent Budget as a placeholder)
    st.markdown(
        """
        <div style="
            padding: 1.2rem 1.4rem;
            background-color: #f7f7fb;
            border-radius: 12px;
            border: 1px solid #e0e0f0;
            ">
            <h3 style="margin-top:0;margin-bottom:0.6rem;">Profile &amp; budget</h3>
            <p style="margin:0.1rem 0;"><strong>Profile:</strong> {persona}</p>
            <p style="margin:0.1rem 0;"><strong>Annual income:</strong> ${income:,}</p>
            <p style="margin:0.1rem 0;"><strong>Housing budget (Rent):</strong> 30% of income</p>
            <p style="margin:0.1rem 0;"><strong>Max affordable rent:</strong> ≈ ${rent:,.0f} / month</p>
            <p style="margin:0.4rem 0 0.1rem 0;"><strong>Selected year:</strong> {year}</p>
        </div>
        """.format(
            persona=persona,
            income=int(final_income),
            rent=max_rent,
            year=selected_year,
        ),
        unsafe_allow_html=True,
    )

with col2:
    st.subheader("Price to Income Ratio by City")

    # Bar chart for Price-to-Income Ratio
    fig = px.bar(
        sorted_data,
        x="city_clean",
        y=RATIO_COL,
        color="affordable",
        color_discrete_map={True: "green", False: "red"},
        labels={
            "city_clean": "City",
            RATIO_COL: "Price to Income Ratio (Median Sale Price / Per Capita Income)",
        },
        hover_data={
            "city_clean": True,
            PRICE_COL: ":,.0f",
            INCOME_COL: ":,.0f",
            RATIO_COL: ":.2f",
        },
        height=500,
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        margin=dict(l=20, r=20, t=40, b=80),
    )

    clicked = plotly_events(fig, click_event=True, key="bar_chart", override_height=500)
    
    if clicked:
        st.session_state.selected_city = clicked[0]["x"]


# ----------------------------------------------------
#           IV. Split Chart Feature
# ----------------------------------------------------

if 'split_view' not in st.session_state:
    st.session_state.split_view = False

if st.button("Split affordability chart"):
    st.session_state.split_view = not st.session_state.split_view


if st.session_state.split_view:
    # Affordability is now based on Ratio < Threshold
    affordable_data = sorted_data[sorted_data["affordable"]].sort_values(RATIO_COL, ascending=True)
    unaffordable_data = sorted_data[~sorted_data["affordable"]].sort_values(RATIO_COL, ascending=False)

    # --- Affordable Cities Chart ---
    st.subheader(f"More Affordable Cities (Ratio < {AFFORDABILITY_THRESHOLD})")
    fig_aff = px.bar(
        affordable_data,
        x="city_clean",
        y=RATIO_COL,
        color="affordable",
        color_discrete_map={True: "green", False: "red"},
        labels={"city_clean": "City", RATIO_COL: "Price to Income Ratio"},
        hover_data={
            "city_clean": True,
            PRICE_COL: ":,.0f",
            INCOME_COL: ":,.0f",
            RATIO_COL: ":.2f",
        },
        height=380,
    )
    fig_aff.update_layout(xaxis_tickangle=-45)
    
    clicked_aff = plotly_events(fig_aff, click_event=True, key="bar_chart_aff", override_height=380)
    if clicked_aff:
        st.session_state.selected_city = clicked_aff[0]["x"]


    # --- Unaffordable Cities Chart ---
    st.subheader(f"Less Affordable Cities (Ratio ≥ {AFFORDABILITY_THRESHOLD})")
    fig_unaff = px.bar(
        unaffordable_data,
        x="city_clean",
        y=RATIO_COL,
        color="affordable",
        color_discrete_map={True: "green", False: "red"},
        labels={"city_clean": "City", RATIO_COL: "Price to Income Ratio"},
        hover_data={
            "city_clean": True,
            PRICE_COL: ":,.0f",
            INCOME_COL: ":,.0f",
            RATIO_COL: ":.2f",
        },
        height=380,
    )
    fig_unaff.update_layout(xaxis_tickangle=-45)
    
    clicked_unaff = plotly_events(fig_unaff, click_event=True, key="bar_chart_unaff", override_height=380)
    if clicked_unaff:
        st.session_state.selected_city = clicked_unaff[0]["x"]


# ----------------------------------------------------
#           V. ZIP Choropleth Map
# ----------------------------------------------------

st.subheader("ZIP-code Price Affordability Map")

city_clicked = st.session_state.get("selected_city")

if city_clicked is None:
    st.info("Click a city bar above to render the ZIP-level choropleth.")
else:
    st.markdown(f"### {city_clicked} ZIP-level Affordability")
    geojson = cached_city_geojson(city_clicked)
    
    # Filter data for the selected city and year
    df_city_year = dfy[dfy["city"] == city_clicked].copy()
    
    # Prepare ZIP-level data (using Price-to-Income ratio)
    df_zip_agg = df_city_year.groupby("zip_code_str", as_index=False).agg(
        median_sale_price=(PRICE_COL, "median"),
        per_capita_income=(INCOME_COL, "median"),
        price_to_income_ratio=(RATIO_COL, "median") # Use the pre-calculated ratio
    )
    
    # Clip extremes for better color scaling, using 15 as a max for a more reasonable scale
    MAX_RATIO_CLIP = 15.0
    df_zip_agg["ratio"] = df_zip_agg["price_to_income_ratio"].clip(0, MAX_RATIO_CLIP)
    
    if geojson is None:
        st.warning(f"No GeoJSON found for city **{city_clicked}**. Run `preprocess_geojson.py`.")
    else:
        center_lat = 39.8283  
        center_lon = -98.5795 
        
        fig_map = px.choropleth_mapbox(
            df_zip_agg,
            geojson=geojson,
            locations="zip_code_str",
            featureidkey="properties.ZCTA", 
            color="ratio",
            hover_data={
                "median_sale_price": ":,.0f",
                "per_capita_income": ":,.0f",
                "price_to_income_ratio": ":.2f",
                "zip_code_str": False
            },
            color_continuous_scale="RdYlGn_r", # Red=Bad (high ratio), Green=Good (low ratio)
            mapbox_style="carto-positron",
            zoom=8, 
            center={"lat": center_lat, "lon": center_lon},
            opacity=0.7,
            height=600,
            labels={"ratio": "Price to Income Ratio"}
        )
        
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        # Colorbar configuration adjusted for Price-to-Income
        # Typical long-term housing price-to-income ratio is around 3.0 to 5.0
        fig_map.update_coloraxes(
            cmin=0, 
            cmax=MAX_RATIO_CLIP,
            colorscale=[
                [0.0, 'green'], 
                [AFFORDABILITY_THRESHOLD / MAX_RATIO_CLIP, 'yellow'], # Set yellow point at 5.0
                [1.0, 'red'] 
            ],
            colorbar=dict(
                title="Ratio (Median Sale Price / P.C.I.)", 
                tickvals=[0.0, 3.0, 5.0, 10.0, MAX_RATIO_CLIP],
                ticktext=["0.0 (Very Cheap)", "3.0 (Affordable)", "5.0 (Borderline)", "10.0", f"{MAX_RATIO_CLIP} (Very Expensive)"]
            )
        )
        
        st.plotly_chart(fig_map, use_container_width=True)
