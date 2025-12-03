# app_d3.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import os
import time 

# --- RESTORED IMPORTS ---
from zip_module import load_city_zip_data, get_zip_coordinates
from dataprep import load_data, make_city_view_data, RATIO_COL, AFFORDABILITY_THRESHOLD, apply_income_filter, AFFORDABILITY_CATEGORIES, AFFORDABILITY_COLORS, classify_affordability, make_zip_view_data
from ui_components import income_control_panel, render_manual_input_and_summary, persona_income_slider


# ---------- Global config ----------
st.set_page_config(page_title="Design 3 – Price Affordability Finder", layout="wide")

# Navigation button to go back to home
with st.sidebar:
    if st.button("🏠 Back to Home", use_container_width=True, help="Navigate back to the main page"):
        st.switch_page("app_home.py")

st.title("Design 3 – Price Affordability Finder")

# --- HTML INTRO BLOCK ---
st.markdown(
    """
    <div style="border-top: 1px solid #e6e6e6; padding: 10px 0; margin-bottom: 10px;">
    Use this tool to compare cities by <strong> price-to-income ratio </strong>,then select a metro area to zoom into ZIP-code details.<br>
    <strong>Price-to-Income rule: </strong>
    We evaluate housing affordability using:
    <span style="background-color: #f0f2f6; padding: 2px 6px; border-radius: 4px;">
            <strong>Median Sale Price / Per Capita Income</strong>
    </span><br>
    <small>Lower ratios indicate better affordability. 
    In this dashboard, cities with a ratio &le; 3.0 are classified as <strong>"Affordable"</strong>.
    Those with a ratio between 3.1 to 4.0 inclusive are classified as <strong>"Moderately Unaffordable"</strong>.
    Those with a ratio between 4.1 to 5.0 inclusive are classified as <strong>"Seriously Unaffordable"</strong>.
    Those with a ratio between 5.1 to 8.9 inclusive are classified as <strong>"Severely Unaffordable"</strong>.
    Those with a ratios &ge; are classified as <strong>"Impossibly Unaffordable"</strong></small>.
    </div>
    """,
    unsafe_allow_html=True
)

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

MAX_ZIP_RATIO_CLIP = 15.0


# ---------- Function Definitions ----------
def year_selector(df: pd.DataFrame, key: str):
    years = sorted(df["year"].unique())
    if not years:
        return None
        
    # 1. Render the label manually with bigger font
    st.markdown("""
        <div style="font-size: 18px; font-weight: 600; margin-bottom: -15px;">
            Select Year
        </div>
    """, unsafe_allow_html=True)
    
    # 2. Render the selectbox with the label hidden
    return st.selectbox(
        "Select Year", 
        years, 
        index=len(years) - 1, 
        key=key, 
        label_visibility="collapsed" 
    )
    
@st.cache_data(ttl=3600*24)
def get_data_cached():
    return load_data()

@st.cache_data
def calculate_median_ratio_history(dataframe):
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

# Initialize session state
if 'last_drawn_city' not in st.session_state:
    st.session_state.last_drawn_city = None
if 'last_drawn_income' not in st.session_state: 
    st.session_state.last_drawn_income = 0


# =====================================================================
#   LAYOUT SETUP
# =====================================================================

# 1. Calculation Pre-requisites
final_income, persona = income_control_panel()
max_affordable_price = AFFORDABILITY_THRESHOLD * final_income
df_filtered_by_income = apply_income_filter(df, final_income)

# Calculate Histories
df_history = calculate_median_ratio_history(df)
df_prop_history = calculate_category_proportions_history(df)


# --- [FIX 1] CUSTOM DIVIDER TO REPLACE '---' (REMOVES WHITESPACE) ---
st.markdown("""
    <hr style="border: none; border-top: 1px solid #e6e6e6; margin-top: 5px; margin-bottom: 10px;">
    """, unsafe_allow_html=True)

header_row_main, header_row_year = st.columns([4, 1]) # Middle Header
main_col_left, main_col_right = st.columns([1, 1])    # Main Content


# =====================================================================
#   SECTION 2: HEADER & YEAR SELECTION
# =====================================================================

# 1. Render Widget FIRST
with header_row_year:
    selected_year = year_selector(df, key="year_main_selector") 

# --- [FIX 2] LOGIC SAFETY CHECK (PREVENTS 'NO OPTIONS' BUG) ---
if selected_year is None:
    selected_year = df["year"].max()

# 2. Render Header Text
with header_row_main:
    # --- [FIX 3] CUSTOM HEADER TO REMOVE TOP MARGIN ---
    st.markdown("""
        <h3 style="margin-top: -5px; padding-top: 0;">
            Compare metro areas by price-to-income ratio & toggle mini-map for zipcode level details
        </h3>
    """, unsafe_allow_html=True)


# 3. CALCULATE DATA
city_data = make_city_view_data(
    df, 
    annual_income=final_income,
    year=selected_year, 
    budget_pct=30,
)

# 4. Apply Column Fixes
if not city_data.empty:
    city_data["affordability_rating"] = city_data[RATIO_COL].apply(classify_affordability)
    gap = city_data[RATIO_COL] - AFFORDABILITY_THRESHOLD
    dist = gap.abs()
    city_data["gap_for_plot"] = np.where(city_data["affordable"], dist, -dist)


# =====================================================================
#   SECTION 3: MAIN CHARTS (City Bar & Map)
# =====================================================================

# --- LEFT COLUMN: CITY BAR CHART ---
with main_col_left:
    profile_settings_container = st.container(border=True)
    with profile_settings_container:
        st.markdown("### Your Profile & Budget Settings")
        render_manual_input_and_summary(final_income, persona, max_affordable_price)

    st.markdown("#### Metro Area Affordability Ranking")

    if city_data.empty:
        st.warning(f"No data available for {selected_year}.")
    else:
        unique_city_pairs = city_data[["city", "city_full"]].drop_duplicates().sort_values("city_full")
        full_to_clean_city_map = pd.Series(unique_city_pairs["city"].values, index=unique_city_pairs["city_full"]).to_dict()

        selected_full_metros = st.multiselect(
            "Filter Metro Areas (All selected by default):",
            options=unique_city_pairs["city_full"].tolist(), 
            default=unique_city_pairs["city_full"].tolist(), 
            key="metro_multiselect"
        )
        
        selected_clean_metros = [full_to_clean_city_map[f] for f in selected_full_metros]

        # Sort Option
        sort_option = st.selectbox(
            "Sort metro areas by",
            ["Metro Area Name", "Price to Income Ratio", "Median Sale Price", "Per Capita Income"],
            key="sort_bar_chart",
        )
        
        plot_data = city_data[city_data["city"].isin(selected_clean_metros)].copy()
        
        if plot_data.empty:
            st.warning("No cities match your current filter selection.")
        
        else:
            # Sort logic
            if sort_option == "Price to Income Ratio":
                sorted_data = plot_data.sort_values(RATIO_COL, ascending=True)
            elif sort_option == "Median Sale Price":
                sorted_data = plot_data.sort_values("Median Sale Price", ascending=False)
            elif sort_option == "Per Capita Income":
                sorted_data = plot_data.sort_values("Per Capita Income", ascending=False)
            else: 
                sorted_data = plot_data.sort_values("city_full") 

            # Color logic
            sorted_data["afford_label"] = sorted_data["affordability_rating"].astype('category')
            ordered_categories = list(AFFORDABILITY_CATEGORIES.keys())
            if 'N/A' in sorted_data["afford_label"].unique():
                ordered_categories.append('N/A')
            sorted_data["afford_label"] = pd.Categorical(sorted_data["afford_label"], categories=ordered_categories, ordered=True)

            if not sorted_data.empty:
                fig_city = px.bar(
                    sorted_data,
                    x="city",
                    y=RATIO_COL,
                    color="afford_label",
                    color_discrete_map=AFFORDABILITY_COLORS,
                    labels={
                        "city": "City",
                        RATIO_COL: "Price-to-income ratio",
                        "afford_label": "Affordability Rating",
                    },
                    hover_data={
                        "city_full": True,
                        "Median Sale Price": ":,.0f",
                        "Per Capita Income": ":,.0f",
                        RATIO_COL: ":.2f",
                        "afford_label": True,
                    },
                    height=520, 
                )
                
                # Threshold lines
                for i, (category, (lower, upper)) in enumerate(AFFORDABILITY_CATEGORIES.items()):
                    if upper is not None and category != "Affordable":
                        fig_city.add_hline(
                            y=upper,
                            line_dash="dot",
                            line_color="gray",
                            annotation_text=f"{category} threshold ({upper:.1f})",
                            annotation_position="top right" if i % 2 == 0 else "bottom right",
                            opacity=0.5
                        )

                fig_city.update_layout(
                    yaxis_title="Price-to-income ratio",
                    xaxis_tickangle=-45,
                    margin=dict(l=20, r=20, t=40, b=80),
                    bargap=0.05,
                    bargroupgap=0.0,
                )

                st.plotly_chart(fig_city, use_container_width=True)


# --- RIGHT COLUMN: MAP & FILTERS ---
with main_col_right:
    with st.container(border=True):
        st.markdown("### Adjust Map View Filters")
        persona_income_slider(final_income, persona) 

    st.markdown("#### ZIP-level Map (Select Metro Below)")

    # Ensure we use valid data for the map dropdown
    map_city_options_full = sorted(df_filtered_by_income["city_full"].unique()) 
    
    selected_map_metro_full = st.selectbox(
        "Choose Metro Area for Map:",
        options=map_city_options_full,
        index=0,
        key="map_metro_select"
    )
    
    city_clicked_df = df_filtered_by_income[df_filtered_by_income['city_full'] == selected_map_metro_full]
    
    if city_clicked_df.empty:
        st.warning("Selected metro area does not exist in the filtered data.")
        city_clicked = None
    else:
        geojson_code = city_clicked_df["city_geojson_code"].iloc[0]
        city_clicked = geojson_code

    if city_clicked is None:
        st.info("Select a Metro Area from the dropdown above to view the ZIP-code map.")
    else:
        map_selection_changed = (selected_map_metro_full != st.session_state.last_drawn_city)
        income_changed = (final_income != st.session_state.last_drawn_income)
        should_trigger_spinner = map_selection_changed or income_changed

        st.markdown(f"**Map for {selected_map_metro_full} ({selected_year})**")
        
        if should_trigger_spinner:
            loading_message_placeholder = st.empty()
            loading_message_placeholder.markdown(
                f'<div style="text-align: center; padding: 20px;">'
                f'<h3><i class="fas fa-spinner fa-spin"></i> Loading map...</h3>' 
                f'<p>Preparing map for {selected_map_metro_full}</p>'
                f'</div>', 
                unsafe_allow_html=True
            )
            time.sleep(0.5) 

        # Load Map Data
        df_zip = load_city_zip_data(city_clicked, df_full=df_filtered_by_income, max_pci=final_income)
        
        if "year" in df_zip.columns:
            df_zip = df_zip[df_zip["year"] == selected_year].copy() 

        if df_zip.empty:
            if should_trigger_spinner: loading_message_placeholder.empty()
            st.error("No ZIP-level data available for this city/year.")
        else:
            df_zip_map = get_zip_coordinates(df_zip) 
            price_col = "median_sale_price"
            income_col = "per_capita_income"

            if df_zip_map.empty or price_col not in df_zip_map.columns:
                if should_trigger_spinner: loading_message_placeholder.empty()
                st.error("Map data processing failed.")
            else:
                if RATIO_COL not in df_zip_map.columns:
                    denom_zip = df_zip_map[income_col].replace(0, np.nan)
                    df_zip_map[RATIO_COL] = df_zip_map[price_col] / denom_zip
                
                df_zip_map["affordability_rating"] = df_zip_map[RATIO_COL].apply(classify_affordability)
                df_zip_map["ratio_for_map"] = df_zip_map[RATIO_COL].clip(0, MAX_ZIP_RATIO_CLIP)

                # Fix path: go up one level from pages/ to Combined123/ directory
                geojson_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "city_geojson",
                    f"{city_clicked}.geojson", 
                )

                if not os.path.exists(geojson_path):
                    if should_trigger_spinner: loading_message_placeholder.empty()
                    st.error(f"GeoJSON file not found for {city_clicked}. Expected path: {geojson_path}")
                else:
                    with open(geojson_path, "r") as f:
                        zip_geojson = json.load(f)

                    # --- FIX START: FORCE STRING FORMAT WITH LEADING ZEROS ---
                    # Boston ZIPs are 02xxx. Integers (2xxx) won't match GeoJSON ("02xxx").
                    df_zip_map["zip_str_padded"] = df_zip_map["zip_code_int"].astype(str).str.zfill(5)
                    # --- FIX END --------------------------------------------

                    fig_map = px.choropleth_mapbox(
                        df_zip_map,
                        geojson=zip_geojson,
                        locations="zip_str_padded", # UPDATED: Use the padded string column
                        featureidkey="properties.ZCTA5CE10",
                        color="ratio_for_map", 
                        color_continuous_scale="RdYlGn_r",
                        range_color=[0, MAX_ZIP_RATIO_CLIP],
                        hover_name="zip_code_str",
                        hover_data={
                            price_col: ":,.0f",
                            income_col: ":,.0f",
                            RATIO_COL: ":.2f",
                            "affordability_rating": True,
                        },
                        mapbox_style="carto-positron",
                        center={
                            "lat": df_zip_map["lat"].mean(),
                            "lon": df_zip_map["lon"].mean(),
                        },
                        zoom=10,
                        height=520,
                    )

                    fig_map.update_layout(
                        margin=dict(l=0, r=0, t=0, b=0),
                        coloraxis_colorbar=dict(
                            title="Price-to-income ratio",
                            tickformat=".1f",
                        ),
                    )
                    
                    if should_trigger_spinner: loading_message_placeholder.empty() 

                    st.plotly_chart(fig_map, use_container_width=True, config={"scrollZoom": True})
                    
                    st.session_state.last_drawn_city = selected_map_metro_full 
                    st.session_state.last_drawn_income = final_income

        # --- CITY SNAPSHOT DETAILS ---
        st.markdown("")
        city_snapshot_container = st.container(border=True)
        with city_snapshot_container:
            city_row = city_data[city_data["city"] == city_clicked] 

            if not city_row.empty:
                row = city_row.iloc[0]
                st.markdown(f"#### Metro Area Snapshot: {row['city_full']} ({selected_year})")

                snap_col1, snap_col2 = st.columns([1, 2.2])

                with snap_col1:
                    st.markdown(
                        f"""
                        - Median sale price: **${row['Median Sale Price']:,.0f}**
                        - Per-capita income: **${row['Per Capita Income']:,.0f}**
                        - Metro-area price-to-income ratio: **{row[RATIO_COL]:.2f}**
                        - **Affordability Rating:** **{row['affordability_rating']}** """
                    )
                with snap_col2:
                    st.caption("The map displays price-to-income ratios calculated at the ZIP-code level.")

# =====================================================================
#   SECTION 4: OPTIONAL SPLIT CHART (BY CATEGORY)
# =====================================================================

st.markdown("---")
st.markdown("### Advanced Metro Area Comparisons by Affordability Category")

with st.expander("Show breakdown by Affordability Rating"):
    if 'sorted_data' in locals() and not sorted_data.empty:
        
        # Define the exact order and list of categories to iterate through
        categories_to_plot = [
            "Affordable",
            "Moderately Unaffordable",
            "Seriously Unaffordable",
            "Severely Unaffordable",
            "Impossibly Unaffordable"
        ]

        for cat in categories_to_plot:
            # Filter data for just this category
            cat_data = sorted_data[sorted_data["affordability_rating"] == cat].copy()
            
            # Create a visual header
            st.markdown(f"**{cat}**")
            
            if cat_data.empty:
                st.info(f"No cities in the current selection fall into the '{cat}' category.")
            else:
                # Sort by ratio for the chart (lowest to highest for that group)
                cat_data = cat_data.sort_values(RATIO_COL, ascending=True)
                
                fig_cat = px.bar(
                    cat_data,
                    x="city",
                    y=RATIO_COL,
                    color="affordability_rating",
                    color_discrete_map=AFFORDABILITY_COLORS,
                    # We hide the legend because the title explains the category
                    labels={"city": "City", RATIO_COL: "Price-to-income ratio"},
                    hover_data={
                        "city_full": True, 
                        "Median Sale Price": ":,.0f", 
                        RATIO_COL: ":.2f",
                        "affordability_rating": False # redundant in hover
                    },
                    height=300,
                )
                
                fig_cat.update_layout(
                    xaxis_tickangle=-45, 
                    bargap=0.2,
                    showlegend=False, # Hide legend as color is uniform per chart
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig_cat, use_container_width=True)
            
            # Add a small divider between charts
            st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)

    else:
        st.info("No data available to show advanced city comparisons based on current filters.")


# =====================================================================
#   SECTION 5: DATASET HISTORICAL OVERVIEW (MOVED TO BOTTOM)
# =====================================================================
st.markdown("---")
st.markdown("### Dataset Historical Overview")

with st.container(border=True):
    # Snapshot Metrics (Above the side-by-side plots)
    st.markdown(f"#### Dataset Snapshot ({selected_year})")

    # Side-by-Side Plots
    overall_median_ratio_left, afford_prop_ratio_right = st.columns([1, 1])

    # Left: Median Ratio History
    with overall_median_ratio_left:
        st.markdown("##### Median Affordability Multiplier Over Time")
        fig_history = px.line(
            df_history,
            x="year",
            y="median_ratio",
            markers=True,
            labels={"year": "Year", "median_ratio": "Median Ratio"},
            height=300,
        )
        fig_history.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            yaxis_range=[0, df_history['median_ratio'].max() * 1.1],
        )
        st.plotly_chart(fig_history, use_container_width=True)

    # Right: Proportions History
    with afford_prop_ratio_right:
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