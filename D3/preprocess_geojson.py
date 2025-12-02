# Part of Jason's code finished on Nov 25
import os
import geopandas as gpd
import pandas as pd

HOUSE_CSV = "HouseTS.csv"
ZCTA_SHP = "cb_2018_us_zcta510_500k/cb_2018_us_zcta510_500k.shp"
CITY_GEOJSON_DIR = "city_geojson"

os.makedirs(CITY_GEOJSON_DIR, exist_ok=True)

print("Loading shapefile (this may take ~20–40 seconds)...")
gdf = gpd.read_file(ZCTA_SHP)
gdf["ZCTA"] = gdf["ZCTA5CE10"].astype(str).str.zfill(5)

df = pd.read_csv(HOUSE_CSV)
df["zip_code_str"] = df["zipcode"].astype(str).str.zfill(5)
cities = sorted(df["city"].unique())
print(f"Found {len(cities)} cities. Creating per-city GeoJSON files...")

for city in cities:
    city_zips = df[df["city"] == city]["zip_code_str"].unique()
    subset = gdf[gdf["ZCTA"].isin(city_zips)]
    out_path = os.path.join(CITY_GEOJSON_DIR, f"{city}.geojson")
    subset.to_file(out_path, driver="GeoJSON")
    print(f"  ✓ Saved {city} → {out_path} ({len(subset)} ZIPs)")
print("Done.")
