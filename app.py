import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

st.write("App started successfully")

st.set_page_config(
    page_title="Delhi School Air Pollution Dashboard",
    page_icon="🌫️",
    layout="wide"
)

st.title("Delhi School Air Pollution Dashboard")
st.caption("Estimated school exposure based on the nearest air-quality monitoring station in Delhi (for data 2025)")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"


@st.cache_data
def load_data():
    schools = pd.read_csv(DATA_DIR / "schools_with_exposure.csv")
    return schools


schools = load_data()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filter the dashboard")

district_options = ["All districts"] + sorted(schools["District"].dropna().unique().tolist())
type_options = ["All school types"] + sorted(schools["Type"].dropna().unique().tolist())
confidence_options = ["All confidence levels"] + sorted(schools["exposure_confidence"].dropna().unique().tolist())

selected_district = st.sidebar.selectbox("District", district_options)
selected_type = st.sidebar.selectbox("School type", type_options)
selected_confidence = st.sidebar.selectbox("Confidence level", confidence_options)

filtered_schools = schools.copy()

if selected_district != "All districts":
    filtered_schools = filtered_schools[filtered_schools["District"] == selected_district]

if selected_type != "All school types":
    filtered_schools = filtered_schools[filtered_schools["Type"] == selected_type]

if selected_confidence != "All confidence levels":
    filtered_schools = filtered_schools[filtered_schools["exposure_confidence"] == selected_confidence]

# -----------------------------
# Helper formatting
# -----------------------------
def format_school_table(df, pollutant_col, pollutant_label):
    out = df.copy()

    rename_map = {
        "School Name": "School",
        "District": "District",
        "Type": "School type",
        "nearest_station_name": "Nearest monitoring station",
        "distance_km": "Distance to nearest station (km)",
        "exposure_confidence": "Confidence level",
        pollutant_col: pollutant_label,
    }

    keep_cols = [
        "School Name",
        "District",
        "Type",
        "nearest_station_name",
        "distance_km",
        pollutant_col,
        "exposure_confidence"
    ]

    out = out[keep_cols].rename(columns=rename_map)
    out["Distance to nearest station (km)"] = out["Distance to nearest station (km)"].round(2)
    out[pollutant_label] = out[pollutant_label].round(1)
    out = out.reset_index(drop=True)
    out.index = out.index + 1
    return out


def format_district_table(df):
    out = df.copy()
    out = out.rename(columns={
        "District": "District",
        "school_count": "Schools",
        "avg_pm25": "Average PM2.5 exposure",
        "avg_pm10": "Average PM10 exposure",
        "avg_no2": "Average NO2 exposure",
        "avg_distance_km": "Average distance to station (km)"
    })

    for col in ["Average PM2.5 exposure", "Average PM10 exposure", "Average NO2 exposure", "Average distance to station (km)"]:
        out[col] = out[col].round(2)

    out = out.reset_index(drop=True)
    out.index = out.index + 1
    return out


# -----------------------------
# Summary stats
# -----------------------------
if filtered_schools.empty:
    st.warning("No schools match the current filter selection.")
    st.stop()

highest_pm25_value = filtered_schools["PM2.5 (µg/m³)_mean"].max()
highest_pm10_value = filtered_schools["PM10 (µg/m³)_mean"].max()
highest_no2_value = filtered_schools["NO2 (µg/m³)_mean"].max()

highest_pm25_schools = filtered_schools[
    filtered_schools["PM2.5 (µg/m³)_mean"] == highest_pm25_value
]["School Name"].tolist()

highest_pm25_station = filtered_schools[
    filtered_schools["PM2.5 (µg/m³)_mean"] == highest_pm25_value
]["nearest_station_name"].iloc[0]

# -----------------------------
# KPI cards
# -----------------------------
st.subheader("Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Schools in this view", f"{len(filtered_schools):,}")
col2.metric("Districts covered", filtered_schools["District"].nunique())
col3.metric("Monitoring stations linked", filtered_schools["nearest_station_id"].nunique())
col4.metric("Average PM2.5 exposure", f"{filtered_schools['PM2.5 (µg/m³)_mean'].mean():.1f} µg/m³")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Average PM10 exposure", f"{filtered_schools['PM10 (µg/m³)_mean'].mean():.1f} µg/m³")
col6.metric("Average NO2 exposure", f"{filtered_schools['NO2 (µg/m³)_mean'].mean():.1f} µg/m³")
col7.metric("Average station distance", f"{filtered_schools['distance_km'].mean():.2f} km")
col8.metric("Farthest school from station", f"{filtered_schools['distance_km'].max():.2f} km")

st.markdown("---")

# -----------------------------
# Story highlights
# -----------------------------
st.subheader("Key highlights")

st.markdown(
    f"""
- **Highest estimated PM2.5 exposure in this view:** **{highest_pm25_value:.1f} µg/m³**
- **Nearest monitoring station behind that estimate:** **{highest_pm25_station}**
- **Schools linked to that highest PM2.5 estimate:** **{", ".join(highest_pm25_schools[:5])}**
"""
)

# -----------------------------
# District chart
# -----------------------------
st.subheader("District-level PM2.5 exposure")

district_filtered = (
    filtered_schools
    .groupby("District", dropna=False)
    .agg(
        school_count=("School Name", "count"),
        avg_pm25=("PM2.5 (µg/m³)_mean", "mean"),
        avg_pm10=("PM10 (µg/m³)_mean", "mean"),
        avg_no2=("NO2 (µg/m³)_mean", "mean"),
        avg_distance_km=("distance_km", "mean")
    )
    .reset_index()
    .sort_values("avg_pm25", ascending=False)
)

fig_district = px.bar(
    district_filtered.head(10),
    x="District",
    y="avg_pm25",
    title="Top districts by average PM2.5 exposure",
    labels={
        "avg_pm25": "Average PM2.5 exposure",
        "District": "District"
    }
)
st.plotly_chart(fig_district, use_container_width=True)

st.dataframe(format_district_table(district_filtered), use_container_width=True)

# -----------------------------
# Top PM2.5 schools
# -----------------------------
st.subheader("Schools with the highest estimated PM2.5 exposure")

top_pm25_schools = (
    filtered_schools
    .sort_values(by=["PM2.5 (µg/m³)_mean", "distance_km"], ascending=[False, True])
    .head(15)
)

st.dataframe(
    format_school_table(
        top_pm25_schools,
        "PM2.5 (µg/m³)_mean",
        "Estimated PM2.5 exposure (µg/m³)"
    ),
    use_container_width=True
)

# -----------------------------
# Top PM10 schools
# -----------------------------
st.subheader("Schools with the highest estimated PM10 exposure")

top_pm10_schools = (
    filtered_schools
    .sort_values(by=["PM10 (µg/m³)_mean", "distance_km"], ascending=[False, True])
    .head(15)
)

st.dataframe(
    format_school_table(
        top_pm10_schools,
        "PM10 (µg/m³)_mean",
        "Estimated PM10 exposure (µg/m³)"
    ),
    use_container_width=True
)

# -----------------------------
# Top NO2 schools
# -----------------------------
st.subheader("Schools with the highest estimated NO2 exposure")

top_no2_schools = (
    filtered_schools
    .sort_values(by=["NO2 (µg/m³)_mean", "distance_km"], ascending=[False, True])
    .head(15)
)

st.dataframe(
    format_school_table(
        top_no2_schools,
        "NO2 (µg/m³)_mean",
        "Estimated NO2 exposure (µg/m³)"
    ),
    use_container_width=True
)

# -----------------------------
# Monitoring gap schools
# -----------------------------
st.subheader("Schools farthest from a monitoring station")

farthest_schools = (
    filtered_schools
    .sort_values(by="distance_km", ascending=False)
    .head(15)
)

gap_table = farthest_schools[
    ["School Name", "District", "Type", "nearest_station_name", "distance_km", "exposure_confidence"]
].rename(columns={
    "School Name": "School",
    "District": "District",
    "Type": "School type",
    "nearest_station_name": "Nearest monitoring station",
    "distance_km": "Distance to nearest station (km)",
    "exposure_confidence": "Confidence level"
})

gap_table["Distance to nearest station (km)"] = gap_table["Distance to nearest station (km)"].round(2)
gap_table = gap_table.reset_index(drop=True)
gap_table.index = gap_table.index + 1

st.dataframe(gap_table, use_container_width=True)

# -----------------------------
# Method note
# -----------------------------
st.markdown("---")
st.subheader("How to read this dashboard")

st.info(
    "These school-level pollution values are estimated exposure proxies, not direct measurements taken inside school campuses. "
    "The pollution data comes from daily 2025 readings collected at Delhi air-quality monitoring stations operated by CPCB, DPCC, and IITM. "
    "Each school was linked to its nearest monitoring station using latitude and longitude coordinates, and the station's yearly mean pollution levels "
    "were assigned as the school's estimated exposure."
)