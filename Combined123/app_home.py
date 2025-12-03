# app_home.py
# Combined 1 and 2, used as home page


import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.express as px
import streamlit.components.v1 as components

from config_data import (
    get_global_theme_css,
    get_dynamic_css,
    get_colorscale,
    load_all_data,
    compute_pti,
    compute_rankings,
    get_metro_yoy,
    US_BOUNDS,
    US_CENTER_LAT,
    US_CENTER_LON,
    US_ZOOM_LEVEL,
)
from geo_utils import load_cbsa_shapes, load_zcta_shapes, get_zip_polygons_for_metro
from charts import create_city_choropleth, create_zip_choropleth, create_history_chart
from events import extract_city_from_event, extract_zip_from_event

# =========================================================================
# 1. Page config
# =========================================================================
st.set_page_config(
    page_title="Interactive Metro → ZIP Sale Price Map",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================================
# 2. Sidebar theme controls (must come before CSS + layout)
# =========================================================================
with st.sidebar:
    st.title("🧭 Control Panel")
    theme_choice = st.radio("Appearance", ["Light", "Dark"], horizontal=True)

is_dark_mode = theme_choice == "Dark"

# Inject global + dynamic theme CSS
st.markdown(get_global_theme_css(is_dark_mode), unsafe_allow_html=True)
st.markdown(get_dynamic_css(is_dark_mode), unsafe_allow_html=True)

# Base map style (can be overridden by sidebar control later)
map_style = "carto-darkmatter" if is_dark_mode else "carto-positron"

# =========================================================================
# 3. Session state init
# =========================================================================
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "city"
if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = None
if "selected_zip" not in st.session_state:
    st.session_state["selected_zip"] = None


# =========================================================================
# 4. Helper functions
# =========================================================================
def render_single_metro_trend(metro_name, ratio_agg, is_dark_mode, selected_year):
    df_metro = ratio_agg[ratio_agg["city_full"] == metro_name].copy()
    if df_metro.empty:
        st.info("No affordability data available for this metro.")
        return

    fig = px.line(
        df_metro,
        x="year",
        y="Price_Income_Ratio",
        markers=True,
        title="Price-to-Income Ratio Over Time",
    )

    if selected_year in df_metro["year"].values:
        year_value = (
            df_metro[df_metro["year"] == selected_year]["Price_Income_Ratio"].iloc[0]
        )

        fig.add_hline(
            y=year_value,
            line_dash="dash",
            line_color="#D96D00",
            line_width=3,
            opacity=0.8,
        )

        fig.add_annotation(
            x=df_metro["year"].max(),
            y=year_value,
            text=f"Ratio: {year_value:.2f}",
            showarrow=False,
            font=dict(color="#D96D00", size=14),
            xanchor="left",
            yanchor="bottom",
            bgcolor=None,
            bordercolor=None,
            borderwidth=1,
            borderpad=4,
        )

    fig.update_layout(
        yaxis_title="Price to Income Ratio",
        xaxis_title="Year",
        template="plotly_dark" if is_dark_mode else "plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(show_spinner="Loading required data...")
def load_affordability_data():
    df = pd.read_csv("data/house_ts_agg.csv")
    df = df.fillna(0)

    # Price to Income Data Preparation
    df["Price_Income_Ratio"] = df["median_sale_price"] / df["per_capita_income"]

    ratio_agg = (
        df.groupby(["city_full", "year"], as_index=False).agg(
            {
                "Price_Income_Ratio": "median",
                "median_sale_price": "median",
                "per_capita_income": "median",
            }
        )
    )

    ratio_agg["Affordability"] = [""] * len(ratio_agg)
    for i in range(len(ratio_agg)):
        ratio = ratio_agg["Price_Income_Ratio"][i]
        # Fix ChainedAssignmentError that comes up.
        if 0.0 <= ratio < 3.0:
            # ratio_agg["Affordability"][i] = "Affordable"
            ratio_agg.loc[i, "Affordability"] = "Affordable"
        elif 3.0 <= ratio < 4.0:
            # ratio_agg["Affordability"][i] = "Moderately Unaffordable"
            ratio_agg.loc[i, "Affordability"] = "Moderately Unaffordable"
        elif 4.0 <= ratio < 5.0:
            # ratio_agg["Affordability"][i] = "Seriously Unaffordable"
            ratio_agg.loc[i, "Affordability"] = "Seriously Unaffordable"
        elif 5.0 <= ratio < 9.0:
            # ratio_agg["Affordability"][i] = "Severly Unaffordable"
            ratio_agg.loc[i, "Affordability"] = "Severely Unaffordable"
        elif ratio >= 9.0:
            # ratio_agg["Affordability"][i] = "Impossibly Unaffordable"
            ratio_agg.loc[i, "Affordability"] = "Impossibly Unaffordable"

    city_order = sorted(df["city_full"].unique())

    # COVID-19 Price Changes Data Preparation
    prices_agg = (
        df.groupby(["city_full", "year"], as_index=False).agg(
            {"median_sale_price": "median"}
        )
    )

    prices_year = pd.pivot(
        prices_agg, index=["city_full"], columns="year", values="median_sale_price"
    )
    prices_year = prices_year.reset_index()
    prices_year.columns = prices_year.columns.astype(str)

    # 2020–2021 percent change
    prices_year["2020_2021_Percent_Change"] = (
        (prices_year["2021"] - prices_year["2020"]) / prices_year["2020"] * 100
    )
    prices_year = prices_year.sort_values(
        by="2020_2021_Percent_Change", ascending=False
    )

    return ratio_agg, city_order, prices_year


def render_affordability_sidebar(city_order):
    st.header("Select Metropolitan Area")
    selected_cities = st.multiselect(
        "Metropolitan Areas",
        options=city_order,
        default=city_order[:5],
    )

    show_legend = st.checkbox("Show Legend", value=True)
    return selected_cities, show_legend


def render_affordability_dashboard(selected_cities, show_legend, ratio_agg, prices_year):
    with st.expander("ℹ️ How to Interact with This Dashboard", expanded=False):
        st.markdown(
            """
        ### 💡 How to Use This Tool
        - 🎯 Pick any metropolitan area from the list above — the chart updates instantly.
        - 📊 Compare affordability across metropolitan area and over time.
        - 🔍 Hover for details.

        ### 🧮 What the Price-to-Income Ratio Means
        - Formula: **Home Sale Price ÷ Annual Income**
        - Affordability levels:
            - **0.0-2.9:** Affordable
            - **3.0-3.9:** Moderately Unaffordable
            - **4.0-4.9:** Seriously Unaffordable
            - **5.0-8.9:** Severely Unaffordable
            - **9.0+:** Impossibly Unaffordable

        Enjoy exploring! 🚀
        """
        )

    st.info(
        "📈 **Multi-Metro Comparison** · "
        "Hover for details · Select metros in left panel"
    )

    if len(selected_cities) == 0:
        st.warning("Please select at least one metropolitan area.")
        return

    # ===================================
    # Price to Income Ratio Visualization
    # ===================================
    price_income = ratio_agg[ratio_agg["city_full"].isin(selected_cities)].copy()
    customdata = price_income[
        ["per_capita_income", "median_sale_price", "Affordability"]
    ].values

    colors = px.colors.qualitative.Plotly
    color_map = {city: colors[i % len(colors)] for i, city in enumerate(selected_cities)}

    price_income_fig = px.line(
        price_income,
        x="year",
        y="Price_Income_Ratio",
        color="city_full",
        color_discrete_map=color_map,
        markers=True,
    )

    for i, trace in enumerate(price_income_fig.data):
        city_name = trace.name
        mask = price_income["city_full"] == city_name
        price_income_fig.data[i].customdata = customdata[mask.values]

    price_income_fig.add_hline(
        y=3,
        line_width=2,
        line_dash="dash",
        line_color="silver",
        annotation_text="0.0-2.9: Affordable",
        annotation_position="bottom right",
    )
    price_income_fig.add_hrect(
        y0=0.0,
        y1=3.0,
        line_width=0,
        fillcolor="Green",
        layer="below",
        opacity=0.2,
    )

    price_income_fig.add_hline(
        y=4,
        line_width=2,
        line_dash="dash",
        line_color="silver",
        annotation_text="3.0-3.9: Moderately Unaffordable",
        annotation_position="bottom right",
    )
    price_income_fig.add_hrect(
        y0=3.0,
        y1=4.0,
        line_width=0,
        fillcolor="Yellow",
        layer="below",
        opacity=0.2,
    )

    price_income_fig.add_hline(
        y=5,
        line_width=2,
        line_dash="dash",
        line_color="silver",
        annotation_text="4.0-4.9: Seriously Unaffordable",
        annotation_position="bottom right",
    )
    price_income_fig.add_hrect(
        y0=4.0,
        y1=5.0,
        line_width=0,
        fillcolor="Orange",
        layer="below",
        opacity=0.2,
    )

    price_income_fig.add_hline(
        y=9,
        line_width=2,
        line_dash="dash",
        line_color="silver",
        annotation_text="5.0-8.9: Severely Unaffordable",
        annotation_position="bottom right",
    )
    price_income_fig.add_hrect(
        y0=5.0,
        y1=9.0,
        line_width=0,
        fillcolor="Red",
        layer="below",
        opacity=0.2,
    )

    ymax = price_income["Price_Income_Ratio"].max() + 1
    price_income_fig.add_hline(
        y=ymax,
        line_width=2,
        line_dash="dash",
        line_color="silver",
        annotation_text="9.0+: Impossibly Unaffordable",
        annotation_position="bottom right",
    )
    price_income_fig.add_hrect(
        y0=9.0,
        y1=ymax,
        line_width=0,
        fillcolor="DarkRed",
        layer="below",
        opacity=0.2,
    )

    price_income_fig.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "%{customdata[2]}<br>"
            "Year: %{x}<br>"
            "Ratio: %{y:.2f}<br>"
            "Median Income: %{customdata[0]:.0f}<br>"
            "Median Sale Price: %{customdata[1]:.0f}<extra></extra>"
        )
    )

    price_income_fig.update_layout(
        title={
            "text": (
                "Median Housing Price to Median Income Ratio:"
                "<br>U.S. Metropolitan Areas from 2012 to 2023"
            ),
            "font": {"size": 28},
        },
        yaxis_title="Price to Income Ratio",
        xaxis_title="Year",
        hovermode="closest",
        template="plotly_white",
        legend=dict(
            title="Metro Area",
            bgcolor="rgba(255,255,255,0.5)",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
        ),
        height=600,
        margin=dict(l=20, r=20, t=120, b=20),
        font=dict(size=14),
        showlegend=show_legend,
    )

    # ====================================
    # COVID-19 Price Changes Visualization
    # ====================================
    covid_changes = prices_year[prices_year["city_full"].isin(selected_cities)]

    covid_change_fig = px.bar(
        covid_changes,
        y="city_full",
        x="2020_2021_Percent_Change",
        title="Covid Price Changes (2020-2021)",
        orientation="h",
        color="city_full",
        color_discrete_map=color_map,
    )

    covid_change_fig.update_traces(
        width=0.7,
        hovertemplate=(
            "<extra></extra>"
            "<b>%{y}</b><br>"
            "Percent Price Change: %{x:.2f}<br>"
        ),
    )

    covid_change_fig.update_layout(
        title={
            "text": (
                "Selected Metro Areas:<br>Housing Price Percent Changes"
                "<br>During Covid (2020-2021)"
            ),
            "font": {"size": 20},
        },
        yaxis_title="Metro Area",
        xaxis_title="Percent",
        hovermode="closest",
        template="plotly_white",
        autosize=True,
        height=500,
        margin=dict(l=120, t=120),
        font=dict(size=14),
        showlegend=False,
    )

    # ====================================
    # Dashboard Display
    # ====================================
    col1, col2 = st.columns([5, 2], vertical_alignment="center")
    with col1:
        st.plotly_chart(price_income_fig, use_container_width=True)
        st.write(
            "*Affordability levels were provided by the Center for Demographics and Policy "
            "([Demographia International Housing Affordability, 2025 Edition]"
            "(https://www.chapman.edu/communication/_files/"
            "Demographia-International-Housing-Affordability-2025-Edition.pdf)).*"
        )
    with col2:
        st.write(
            "During the COVID-19 pandemic, U.S. cities experienced sharp increases in housing prices. "
            "The bar graph below illustrates the percent change in housing prices from 2020 to 2021 in selected cities."
        )
        st.plotly_chart(covid_change_fig, use_container_width=True)


# =========================================================================
# 5. Load metro/ZIP data
# =========================================================================
try:
    df_all = load_all_data()
except Exception as e:
    st.error(f"❌ Failed to read Databricks tables: {e}")
    st.stop()

if df_all.empty:
    st.warning("⚠️ No data loaded from database.")
    st.stop()

min_year = int(df_all["year"].min())
max_year = int(df_all["year"].max())

ratio_agg, city_order, prices_year = load_affordability_data()

# =========================================================================
# 6. Sidebar controls (time, metric, search, navigation)
# =========================================================================
with st.sidebar:
    with st.expander("🗺️ Metro & Map Controls", expanded=False):
        st.markdown("### ⏱ Time & Metric")
        selected_year = st.slider("Year", min_year, max_year, max_year)
        st.caption(f"Data range: {min_year} – {max_year}")

        metric_type = st.radio(
            "Metric",
            ["Median Sale Price", "Price-to-Income Ratio (PTI)"],
            index=0,
            help="Price: median home sale price\nPTI: affordability (lower = more affordable)",
        )

        use_street_map = st.checkbox("🗺 Use Real Street Map (OSM)", value=False)

        # Override map style
        map_style = (
            "open-street-map"
            if use_street_map
            else ("carto-darkmatter" if is_dark_mode else "carto-positron")
        )

        # ZIP-mode navigation
        if st.session_state["view_mode"] == "zip":
            st.markdown("---")
            st.markdown("### 🔙 Navigation")
            if st.button("⬅️ Back to All Metros"):
                st.session_state["view_mode"] = "city"
                st.session_state["selected_city"] = None
                st.session_state["selected_zip"] = None
                st.rerun()

        # Metro search (for city view)
        if st.session_state["view_mode"] == "city":
            st.markdown("---")
            st.markdown("### 🔍 Quick Metro Search")

            df_filtered_sidebar = df_all[df_all["year"] == selected_year].copy()
            if not df_filtered_sidebar.empty:
                df_city_sidebar = (
                    df_filtered_sidebar.groupby(
                        ["city", "city_full"], as_index=False
                    ).agg(avg_median_sale_price=("median_sale_price", "mean"))
                )

                metro_list = (
                    df_city_sidebar.drop_duplicates(subset=["city_full"])
                    .sort_values("city_full")["city_full"]
                    .tolist()
                )

                selected_metro = st.selectbox(
                    "Select metro",
                    [""] + metro_list,
                    format_func=lambda x: "Type to search..."
                    if x == ""
                    else f"📍 {x}",
                )

                if selected_metro and st.button("➡️ View ZIP codes"):
                    city_match = df_city_sidebar[
                        df_city_sidebar["city_full"] == selected_metro
                    ]["city"].iloc[0]
                    st.session_state["selected_city"] = city_match
                    st.session_state["view_mode"] = "zip"
                    st.session_state["selected_zip"] = None
                    st.rerun()

    # keep this in sidebar as well
    if st.session_state["view_mode"] == "city":
        with st.expander("📈 Multi-Metro Affordability Comparison", expanded=False):
            selected_cities, show_legend = render_affordability_sidebar(city_order)
    else:
        selected_cities, show_legend = [], True
    
    # Navigation button to app_d3.py
    st.markdown("---")
    if st.button("🔍 Price Affordability Finder", use_container_width=True, help="Navigate to the Price Affordability Finder tool"):
        st.switch_page("pages/app_d3.py")

# Fix multiselect text overflow
st.markdown(
    """
    <style>
        .stMultiSelect [data-baseweb=select] span{
            max-width: 400px;
            font-size: 1.0rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================================
# 7. Prepare data for selected year & metric
# =========================================================================
df_year = df_all[df_all["year"] == selected_year].copy()
if df_year.empty:
    st.warning(f"### ⚠️ No data available for {selected_year}")
    st.stop()

if metric_type == "Price-to-Income Ratio (PTI)":
    df_year = compute_pti(df_year)
    value_source_col = "PTI"
    if df_year.empty:
        st.warning(f"⚠️ PTI values out of range for {selected_year}.")
        st.stop()

    df_zip_metric = (
        df_year.groupby(
            ["city", "city_full", "city_clean", "zip_code_str", "year"],
            as_index=False,
        ).agg(
            metric_value=("PTI", "mean"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
    )

    df_city = (
        df_zip_metric.groupby(["city", "city_full", "city_clean"], as_index=False).agg(
            n=("zip_code_str", "count"),
            avg_metric_value=("metric_value", "mean"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
    )
else:
    df_year = df_year[df_year["median_sale_price"].notna()].copy()
    value_source_col = "median_sale_price"
    if df_year.empty:
        st.warning(f"⚠️ No valid price data for {selected_year}.")
        st.stop()

    df_zip_metric = (
        df_year.groupby(
            ["city", "city_full", "city_clean", "zip_code_str", "year"],
            as_index=False,
        ).agg(
            metric_value=("median_sale_price", "mean"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
    )

    df_city = (
        df_zip_metric.groupby(["city", "city_full", "city_clean"], as_index=False).agg(
            n=("zip_code_str", "count"),
            avg_metric_value=("metric_value", "mean"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
    )

df_city_map = df_city.copy().reset_index(drop=True)
df_city_map = compute_rankings(df_city_map, "avg_metric_value", "city")

metro_yoy = get_metro_yoy(df_all, selected_year, metric_type)

# =========================================================================
# 8. Layout: title + help
# =========================================================================
st.title("🏙️ Metro → ZIP Sale Price/PTI Explorer")
st.caption(f"Year: **{selected_year}** · Metric: **{metric_type}**")

with st.expander("ℹ️ How to Interact with This Map", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            ### **Navigation**
            - Hover over metros / ZIPs to preview basic statistics  
            - Use the **Year selector** in the sidebar to choose which year to visualize  
            - Click a **metro** to zoom in and view its ZIP code map  
            - Click a **ZIP code** to view detailed metrics for the selected year  
            - Use **Back to Metros** in the sidebar to return to the national view  
            """
        )

    with col2:
        st.markdown(
            """
        **Metrics**
        - **Median Sale Price**  
          - Metro view: average of ZIP-level *monthly median* sale prices (selected year)  
          - ZIP view: average *monthly median* sale price for this ZIP (selected year)  
        - **PTI (Price-to-Income Ratio)** = Price ÷ Income  
          - Metro view: average PTI across ZIPs in the metro  
          - ZIP view: PTI for this ZIP  
          - Lower PTI = more affordable
        """
        )

current_metro_name = None
if st.session_state["selected_city"]:
    row_sel = df_city_map[df_city_map["city"] == st.session_state["selected_city"]]
    if not row_sel.empty:
        current_metro_name = row_sel["city_full"].iloc[0]

# =========================================================================
# 9. Main view (metro / ZIP)
# =========================================================================
if st.session_state["view_mode"] == "city":
    # --------------------- METRO VIEW ---------------------
    st.info(
        f"📍 **Metro View ({selected_year}) · {metric_type}**  · "
        f"Hover for details · Click to drill down · Scroll to zoom"
    )

    st.markdown("#### 📊 National Summary")
    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)

    with col_s1:
        st.metric("Total Metros", len(df_city_map))

    with col_s2:
        avg_val = df_city_map["avg_metric_value"].mean()
        if metric_type == "Price-to-Income Ratio (PTI)":
            st.metric("Avg PTI", f"{avg_val:.2f}x")
        else:
            st.metric("Avg Price", f"${avg_val:,.0f}")

    with col_s3:
        top_metro = df_city_map.loc[df_city_map["avg_metric_value"].idxmax()]
        metro_label_high = top_metro["city_full"]
        if metric_type == "Price-to-Income Ratio (PTI)":
            st.metric("Highest PTI", f"{top_metro['avg_metric_value']:.2f}x")
        else:
            st.metric("Highest Price", f"${top_metro['avg_metric_value']:,.0f}")
        st.caption(f"Metro: **{metro_label_high}**")

    with col_s4:
        bottom_metro = df_city_map.loc[df_city_map["avg_metric_value"].idxmin()]
        metro_label_low = bottom_metro["city_full"]
        if metric_type == "Price-to-Income Ratio (PTI)":
            st.metric("Lowest PTI", f"{bottom_metro['avg_metric_value']:.2f}x")
        else:
            st.metric("Lowest Price", f"${bottom_metro['avg_metric_value']:,.0f}")
        st.caption(f"Metro: **{metro_label_low}**")

    with col_s5:
        if not metro_yoy.empty and "yoy_pct" in metro_yoy.columns:
            avg_yoy = metro_yoy["yoy_pct"].mean()
            if not pd.isna(avg_yoy):
                st.metric(
                    "Avg YoY Change",
                    f"{avg_yoy:+.1f}%",
                    delta="vs last year",
                    delta_color="off",
                )
            else:
                st.metric(
                    "Avg YoY Change",
                    "N/A",
                    delta="No prior year",
                    delta_color="off",
                )
        else:
            st.metric(
                "Avg YoY Change",
                "N/A",
                delta="No prior year",
                delta_color="off",
            )

    st.markdown("---")

    fig_city = None
    gdf_metro = None
    try:
        cbsa_shapes = load_cbsa_shapes()
        fig_city, gdf_metro = create_city_choropleth(
            df_city_map, cbsa_shapes, map_style, metric_type, is_dark_mode
        )
    except Exception as e:
        st.error(f"❌ Shapefile Error: {e}")

    if fig_city is not None and gdf_metro is not None:
        event = st.plotly_chart(
            fig_city,
            width="stretch",
            on_select="rerun",
            selection_mode="points",
            key=f"metro_map_{selected_year}_{metric_type}_{map_style}",
            config={"scrollZoom": True},
        )
        clicked_city = extract_city_from_event(event)
        if clicked_city and clicked_city != st.session_state["selected_city"]:
            st.session_state["selected_city"] = clicked_city
            st.session_state["selected_zip"] = None
            st.session_state["view_mode"] = "zip"
            st.rerun()

    st.markdown("---")

    st.markdown("## 📈 Multi-Metro Affordability Comparison Dashboard")

    # ----------------------- MULTI-METRO DASHBOARD ------------------------
    render_affordability_dashboard(selected_cities, show_legend, ratio_agg, prices_year)

else:
    # --------------------- ZIP VIEW ---------------------
    selected_city = st.session_state["selected_city"]
    if not selected_city:
        st.warning("⚠️ No metro selected. Please use the sidebar search to select a metro.")
        st.stop()

    st.markdown(
        f"### 🗺️ `USA` → `{current_metro_name or selected_city}` → `ZIP Codes`"
    )
    st.markdown("---")

    label = current_metro_name or selected_city
    st.info(
        f"📍 **{label}** ({selected_year}) · {metric_type}  · "
        f"Click ZIPs to see details · Scroll to zoom"
    )

    try:
        zcta_shapes = load_zcta_shapes()
        zip_df_city, gdf_merge = get_zip_polygons_for_metro(
            selected_city, zcta_shapes, df_zip_metric
        )
    except Exception as e:
        st.error(f"❌ ZIP Shapefile Error: {e}")
        zip_df_city, gdf_merge = pd.DataFrame(), gpd.GeoDataFrame()

    if gdf_merge.empty or zip_df_city.empty:
        st.warning(
            f"### ⚠️ No ZIP code data available for {selected_city} in {selected_year}"
        )
    else:
        # Only keep ZIPs that have metric values
        zip_df_city = zip_df_city[zip_df_city["metric_value"].notna()].copy()

        # Only keep ZIPs that appear in the polygon GeoDataFrame
        valid_zips = gdf_merge["zip_code_str"].unique()
        zip_df_city = zip_df_city[zip_df_city["zip_code_str"].isin(valid_zips)].copy()

        if zip_df_city.empty:
            st.warning(
                f"⚠️ No valid {metric_type} data for {selected_city} in {selected_year}."
            )
        else:
            # Rankings at ZIP level (within this metro)
            zip_df_city = compute_rankings(
                zip_df_city, "metric_value", "zip_code_str"
            )

            if st.session_state.get("selected_zip") is None and not zip_df_city.empty:
                st.session_state["selected_zip"] = zip_df_city["zip_code_str"].iloc[0]

            col_map, col_detail = st.columns([2.2, 1])

            with col_map:
                city_coords = None
                fig_zip, gdf_zip = create_zip_choropleth(
                    gdf_merge,
                    map_style,
                    city_coords,
                    zip_df_city,
                    metric_type,
                    is_dark_mode,
                )
                if fig_zip is not None and gdf_zip is not None:
                    event = st.plotly_chart(
                        fig_zip,
                        width="stretch",
                        on_select="rerun",
                        selection_mode="points",
                        key=(
                            f"zip_map_{selected_city}_{selected_year}_"
                            f"{metric_type}_{map_style}"
                        ),
                        config={"scrollZoom": True},
                    )
                    clicked_zip = extract_zip_from_event(event, gdf_zip)
                    if clicked_zip:
                        st.session_state["selected_zip"] = clicked_zip

            with col_detail:
                st.subheader("📋 ZIP Details")
                active_zip = st.session_state.get("selected_zip")
                if not active_zip:
                    st.info("👈 Click any ZIP on the map")
                else:
                    row_now = zip_df_city[
                        zip_df_city["zip_code_str"] == active_zip
                    ]
                    if row_now.empty:
                        st.warning(f"⚠️ No data for ZIP {active_zip}")
                    else:
                        metric_val = float(row_now["metric_value"].iloc[0])
                        metro_avg_now = float(zip_df_city["metric_value"].mean())
                        diff = metric_val - metro_avg_now
                        pct_diff = (
                            diff / metro_avg_now * 100 if metro_avg_now != 0 else 0.0
                        )
                        rank = int(row_now["rank"].iloc[0])
                        rank_total = int(row_now["rank_total"].iloc[0])
                        percentile = float(row_now["percentile"].iloc[0])
                        metro_name = row_now["city_full"].iloc[0]

                        st.markdown(f"### ZIP `{active_zip}`")
                        st.caption(metro_name)

                        # YoY for this ZIP
                        if metric_type == "Price-to-Income Ratio (PTI)":
                            zip_prev_raw = df_all[
                                (df_all["city"] == selected_city)
                                & (df_all["zip_code_str"] == active_zip)
                                & (df_all["year"] == selected_year - 1)
                            ].copy()
                            zip_prev_raw = (
                                compute_pti(zip_prev_raw)
                                if not zip_prev_raw.empty
                                else pd.DataFrame()
                            )
                            if not zip_prev_raw.empty:
                                prev_val = zip_prev_raw["PTI"].mean()
                                yoy_change = (
                                    (metric_val - prev_val) / prev_val * 100
                                )
                                main_value = f"{metric_val:.2f}x"
                                delta_text = f"{yoy_change:+.1f}% YoY"
                            else:
                                main_value = f"{metric_val:.2f}x"
                                delta_text = "No prior year"
                        else:
                            zip_prev = df_all[
                                (df_all["city"] == selected_city)
                                & (df_all["zip_code_str"] == active_zip)
                                & (df_all["year"] == selected_year - 1)
                                & df_all["median_sale_price"].notna()
                            ]
                            if not zip_prev.empty:
                                prev_val = zip_prev["median_sale_price"].mean()
                                yoy_change = (
                                    (metric_val - prev_val) / prev_val * 100
                                )
                                main_value = f"${metric_val:,.0f}"
                                delta_text = f"{yoy_change:+.1f}% YoY"
                            else:
                                main_value = f"${metric_val:,.0f}"
                                delta_text = "No prior year"

                        rank_percentile = 100 - percentile
                        if pct_diff > 5:
                            diff_label = f"{pct_diff:+.1f}% above metro avg"
                        elif pct_diff < -5:
                            diff_label = f"{pct_diff:+.1f}% below metro avg"
                        else:
                            diff_label = f"{pct_diff:+.1f}% vs metro avg"

                        st.markdown(
                            f"""
                            <div class="metric-card">
                                <div style="font-size: 0.8rem; text-transform: uppercase; color: #6b7280; margin-bottom: 0.25rem;">
                                    {'PTI Ratio' if 'PTI' in metric_type else 'Median Sale Price'}
                                </div>
                                <div style="font-size: 1.6rem; font-weight: 600; margin-bottom: 0.1rem;">
                                    {main_value}
                                </div>
                                <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 0.6rem;">
                                    {delta_text}
                                </div>
                                <div style="font-size: 0.9rem;">
                                    <b>Rank:</b> #{rank} of {rank_total} · Top {rank_percentile:.0f}% in this metro<br>
                                    <b>Relative to metro:</b> {diff_label}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.markdown("#### 📈 Trend")
                        if metric_type == "Price-to-Income Ratio (PTI)":
                            zip_hist_raw = df_all[
                                (df_all["city"] == selected_city)
                                & (df_all["zip_code_str"] == active_zip)
                            ].copy()
                            zip_hist_raw = compute_pti(zip_hist_raw)
                            if not zip_hist_raw.empty:
                                zip_hist = (
                                    zip_hist_raw.groupby(
                                        "year", as_index=False
                                    ).agg(PTI=("PTI", "mean")).sort_values("year")
                                )
                                if not zip_hist.empty:
                                    fig_hist = create_history_chart(
                                        zip_hist,
                                        metro_avg_now,
                                        metric_type,
                                        is_dark_mode,
                                    )
                                    if fig_hist:
                                        st.plotly_chart(
                                            fig_hist,
                                            width="stretch",
                                            config={"displayModeBar": False},
                                        )
                                else:
                                    st.caption("No historical data for this ZIP.")
                            else:
                                st.caption("No historical data for this ZIP.")
                        else:
                            zip_hist = (
                                df_all[
                                    (df_all["city"] == selected_city)
                                    & (df_all["zip_code_str"] == active_zip)
                                    & df_all["median_sale_price"].notna()
                                ]
                                .groupby("year", as_index=False)
                                .agg(price=("median_sale_price", "mean"))
                                .sort_values("year")
                            )
                            if not zip_hist.empty:
                                fig_hist = create_history_chart(
                                    zip_hist,
                                    metro_avg_now,
                                    metric_type,
                                    is_dark_mode,
                                )
                                if fig_hist:
                                    st.plotly_chart(
                                        fig_hist,
                                        width="stretch",
                                        config={"displayModeBar": False},
                                    )
                            else:
                                st.caption("No historical data for this ZIP.")

                        st.markdown("---")
                        csv = zip_df_city[
                            ["zip_code_str", "year", "metric_value", "city_full", "rank"]
                        ].to_csv(index=False)
                        st.download_button(
                            label="📥 Download ZIP-level data (CSV)",
                            data=csv,
                            file_name=(
                                f"{selected_city.replace(',', '_')}_"
                                f"{selected_year}_zipdata.csv"
                            ),
                            mime="text/csv",
                            use_container_width=True,
                        )

            st.markdown("---")
            st.markdown("#### 📊 Metro Summary")
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

            metro_full_name = current_metro_name or selected_city

            render_single_metro_trend(
                metro_name=metro_full_name,
                ratio_agg=ratio_agg,
                is_dark_mode=is_dark_mode,
                selected_year=selected_year,
            )

            values = zip_df_city["metric_value"]
            nonzero_values = values[values > 0]

            with col_m1:
                st.metric("ZIP Codes (on map)", len(zip_df_city))

            with col_m2:
                if metric_type == "Price-to-Income Ratio (PTI)":
                    st.metric("Metro Avg", f"{values.mean():.2f}x")
                else:
                    st.metric("Metro Avg", f"${values.mean():,.0f}")

            with col_m3:
                if metric_type == "Price-to-Income Ratio (PTI)":
                    st.metric(
                        "Max PTI",
                        f"{nonzero_values.max():.2f}x"
                        if not nonzero_values.empty
                        else "N/A",
                    )
                else:
                    st.metric(
                        "Max Price",
                        f"${nonzero_values.max():,.0f}"
                        if not nonzero_values.empty
                        else "N/A",
                    )

            with col_m4:
                if metric_type == "Price-to-Income Ratio (PTI)":
                    st.metric(
                        "Min PTI",
                        f"{nonzero_values.min():.2f}x"
                        if not nonzero_values.empty
                        else "N/A",
                    )
                else:
                    st.metric(
                        "Min Price",
                        f"${nonzero_values.min():,.0f}"
                        if not nonzero_values.empty
                        else "N/A",
                    )

            with col_m5:
                metro_row = (
                    metro_yoy[metro_yoy["city"] == selected_city]
                    if not metro_yoy.empty
                    else pd.DataFrame()
                )
                if not metro_row.empty and "yoy_pct" in metro_row.columns:
                    yoy_val = metro_row["yoy_pct"].iloc[0]
                    if not pd.isna(yoy_val):
                        st.metric("YoY Change", f"{yoy_val:+.1f}%")
                    else:
                        st.metric("YoY Change", "N/A")
                else:
                    st.metric("YoY Change", "N/A")
