# plots.py
import plotly.express as px
import numpy as np


def make_city_bar_plot(city_agg):
    fig = px.bar(
        city_agg,
        x="city",
        y="gap_for_plot",
        color="affordable",
        color_discrete_map={True: "green", False: "red"},
        hover_data={
            "median_rent": True,
            "per_capita_income": True,
            "afford_gap": True,
            "total_zips": True
        },
        labels={
            "gap_for_plot": "Affordability boundary distance",
            "city": "City"
        },
        height=520
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def make_zip_choropleth(df_city_zip, zip_geojson, feature_prop, center_lat, center_lon):
    fig = px.choropleth_mapbox(
        df_city_zip,
        geojson=zip_geojson,
        locations="zip_code_str",
        featureidkey=feature_prop,
        color="affordability_norm",
        color_continuous_scale=["red", "yellow", "green"],
        range_color=(0, 1),
        mapbox_style="carto-positron",
        hover_name="zip_code_str",
        hover_data={
            "median_rent": ":.0f",
            "per_capita_income": ":.0f",
            "affordability_ratio": ":.2f"
        },
        center={"lat": center_lat, "lon": center_lon},
        zoom=10,
        height=650
    )

    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig
