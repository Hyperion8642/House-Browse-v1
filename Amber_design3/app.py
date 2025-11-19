# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from dataprep import load_data, make_city_view_data
from ui_components import income_control_panel


# ---------- Load data ----------
@st.cache_data
def get_data():
    return load_data("HouseTS.csv")


df = get_data()

st.title("Design 3 – Affordability Finder")


# ---------- Sidebar: persona + income ----------
final_income, persona = income_control_panel()


# ---------- Year selector ----------
def year_selector(df: pd.DataFrame, key: str):
    years = sorted(df["year"].unique())
    return st.selectbox("Year", years, index=len(years) - 1, key=key)


top_col1, top_col2 = st.columns([1, 2])
with top_col1:
    selected_year = year_selector(df, key="year_main")

with top_col2:
    sort_option = st.selectbox(
        "Sort cities by",
        ["City name", "Affordability gap", "Median rent", "Per capita income"],
        key="sort_main",
    )


# ---------- Prepare city-level data ----------
city_data = make_city_view_data(
    df,
    annual_income=final_income,
    year=selected_year,
    budget_pct=30,
)

# gap_for_plot
dist = city_data["afford_gap"].abs()
city_data["gap_for_plot"] = np.where(city_data["affordable"], dist, -dist)

# Sort
if sort_option == "Affordability gap":
    sorted_data = city_data.sort_values("gap_for_plot", ascending=True)
elif sort_option == "Median rent":
    sorted_data = city_data.sort_values("Median Rent", ascending=False)
elif sort_option == "Per capita income":
    sorted_data = city_data.sort_values("Per Capita Income", ascending=False)
else:  # City name
    sorted_data = city_data.sort_values("city_clean")

max_rent = final_income * 0.3 / 12.0

# ---------- Layout: left profile card + main right ----------
col1, col2 = st.columns([1, 2])

with col1:
    # Profile 
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
            <p style="margin:0.1rem 0;"><strong>Housing budget:</strong> 30% of income</p>
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
    st.subheader("Affordability gap by city")

    fig = px.bar(
        sorted_data,
        x="city_clean",
        y="gap_for_plot",
        color="affordable",
        color_discrete_map={True: "green", False: "red"},
        labels={
            "city_clean": "City",
            "gap_for_plot": "Distance from affordability boundary "
                            "(+ affordable, − unaffordable)",
        },
        hover_data={
            "city_clean": True,
            "Median Rent": ":.0f",
            "Per Capita Income": ":.0f",
            "afford_gap": ":.2f",
        },
        height=500,
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        margin=dict(l=20, r=20, t=40, b=80),
    )

    st.plotly_chart(fig, use_container_width=True)


# ------------ Split ------------
split = st.button("Split affordability chart")

if split:
    affordable_data = sorted_data[sorted_data["affordable"]]
    unaffordable_data = sorted_data[~sorted_data["affordable"]]

    st.subheader("Affordable cities (green, above 0)")
    fig_aff = px.bar(
        affordable_data,
        x="city_clean",
        y="gap_for_plot",
        color="affordable",
        color_discrete_map={True: "green", False: "red"},
        labels={
            "city_clean": "City",
            "gap_for_plot": "Distance from affordability boundary",
        },
        hover_data={
            "city_clean": True,
            "Median Rent": ":.0f",
            "Per Capita Income": ":.0f",
            "afford_gap": ":.2f",
        },
        height=380,
    )
    fig_aff.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_aff, use_container_width=True)

    st.subheader("Unaffordable cities (red, below 0)")
    fig_unaff = px.bar(
        unaffordable_data,
        x="city_clean",
        y="gap_for_plot",
        color="affordable",
        color_discrete_map={True: "green", False: "red"},
        labels={
            "city_clean": "City",
            "gap_for_plot": "Distance from affordability boundary",
        },
        hover_data={
            "city_clean": True,
            "Median Rent": ":.0f",
            "Per Capita Income": ":.0f",
            "afford_gap": ":.2f",
        },
        height=380,
    )
    fig_unaff.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_unaff, use_container_width=True)
