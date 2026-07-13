import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px


st.set_page_config(
    page_title="Delhi School Air Pollution Dashboard",
    page_icon="🌫️",
    layout="wide"
)

st.title("Delhi School Air Pollution Dashboard")
st.caption(
    "Estimated school exposure based on the nearest air-quality monitoring station in Delhi "
    "(season-wise station-linked exposure for 2025)"
)

st.markdown(
    """
    <style>
    .red-asterisk {
        color: #ff4b4b;
        font-weight: 700;
    }
    .metric-note {
        font-size: 0.9rem;
        color: #b0b0b0;
        margin-top: -0.25rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

AVG_ENROLMENT_DELHI = 808
ENROLMENT_SOURCE_URL = "https://education.economictimes.indiatimes.com/news/school-education/delhi-schools-face-infrastructure-strain-amid-rising-enrolment-report/129760660"

SEASON_LABELS = {
    "Winter": "winter",
    "Summer": "summer",
    "Monsoon": "monsoon",
    "Post-Monsoon": "post_monsoon"
}

POLLUTANT_PREFIX = {
    "PM2.5": "pm25_mean",
    "PM10": "pm10_mean",
    "NO2": "no2_mean"
}


@st.cache_data
def load_data():
    schools = pd.read_csv(DATA_DIR / "schools_with_exposure_seasonal_dashboard.csv")
    districts = pd.read_csv(DATA_DIR / "district_seasonal_summary_dashboard.csv")
    top_winter = pd.read_csv(DATA_DIR / "top_winter_pm25_schools.csv")
    top_jump = pd.read_csv(DATA_DIR / "top_pm25_seasonal_jump_schools.csv")
    return schools, districts, top_winter, top_jump


schools, district_summary, top_winter_reference, top_jump_reference = load_data()


def format_indian_number(n):
    n = int(round(n))
    s = str(n)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts + [last3])


def estimate_students_affected(school_count, avg_enrolment=AVG_ENROLMENT_DELHI):
    return int(round(school_count * avg_enrolment))


def season_col(prefix: str, season_key: str) -> str:
    return f"{prefix}_{season_key}"


def safe_series(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def add_selected_exposure_columns(df, season_key):
    out = df.copy()
    out["selected_pm25"] = safe_series(out, season_col("pm25_mean", season_key))
    out["selected_pm10"] = safe_series(out, season_col("pm10_mean", season_key))
    out["selected_no2"] = safe_series(out, season_col("no2_mean", season_key))
    return out


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

    existing_keep_cols = [c for c in keep_cols if c in out.columns]
    out = out[existing_keep_cols].rename(columns=rename_map)

    if "Distance to nearest station (km)" in out.columns:
        out["Distance to nearest station (km)"] = pd.to_numeric(
            out["Distance to nearest station (km)"], errors="coerce"
        ).round(2)

    if pollutant_label in out.columns:
        out[pollutant_label] = pd.to_numeric(out[pollutant_label], errors="coerce").round(1)

    out = out.reset_index(drop=True)
    out.index = out.index + 1
    return out


def format_district_table(df, pollutant_label):
    out = df.copy()
    out = out.rename(columns={
        "District": "District",
        "school_count": "Schools",
        "selected_pollutant_mean": f"Average {pollutant_label} exposure",
        "avg_pm25": "Average PM2.5 exposure",
        "avg_pm10": "Average PM10 exposure",
        "avg_no2": "Average NO2 exposure",
        "avg_distance_km": "Average distance to station (km)",
        "estimated_students_affected": "Estimated students affected*"
    })

    for col in [
        f"Average {pollutant_label} exposure",
        "Average distance to station (km)"
    ]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(2)

    if "Estimated students affected*" in out.columns:
        out["Estimated students affected*"] = out["Estimated students affected*"].apply(format_indian_number)

    out = out.reset_index(drop=True)
    out.index = out.index + 1
    return out


# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filter the dashboard")

selected_season_label = st.sidebar.selectbox(
    "Season",
    ["Winter", "Summer", "Monsoon", "Post-Monsoon"],
    index=0
)
selected_season = SEASON_LABELS[selected_season_label]

selected_pollutant = st.sidebar.selectbox(
    "Pollutant focus",
    ["PM2.5", "PM10", "NO2"],
    index=0
)

district_options = ["All districts"] + sorted(schools["District"].dropna().unique().tolist())
type_options = ["All school types"] + sorted(schools["Type"].dropna().unique().tolist())
confidence_options = ["All confidence levels"] + sorted(schools["exposure_confidence"].dropna().unique().tolist())

selected_district = st.sidebar.selectbox("District", district_options)
selected_type = st.sidebar.selectbox("School type", type_options)
selected_confidence = st.sidebar.selectbox("Confidence level", confidence_options)


# -----------------------------
# Filtered schools
# -----------------------------
filtered_schools = add_selected_exposure_columns(schools, selected_season)

if selected_district != "All districts":
    filtered_schools = filtered_schools[filtered_schools["District"] == selected_district]

if selected_type != "All school types":
    filtered_schools = filtered_schools[filtered_schools["Type"] == selected_type]

if selected_confidence != "All confidence levels":
    filtered_schools = filtered_schools[filtered_schools["exposure_confidence"] == selected_confidence]

if filtered_schools.empty:
    st.warning("No schools match the current filter selection.")
    st.stop()

selected_pollutant_col = {
    "PM2.5": "selected_pm25",
    "PM10": "selected_pm10",
    "NO2": "selected_no2"
}[selected_pollutant]


# -----------------------------
# Summary stats
# -----------------------------
total_schools = len(schools)
schools_in_view = len(filtered_schools)
total_students_affected = estimate_students_affected(total_schools)
students_affected_in_view = estimate_students_affected(schools_in_view)
filters_active = total_schools != schools_in_view

selected_pollutant_mean = pd.to_numeric(filtered_schools[selected_pollutant_col], errors="coerce").mean()
selected_pollutant_max = pd.to_numeric(filtered_schools[selected_pollutant_col], errors="coerce").max()

highest_pollutant_schools = filtered_schools[
    pd.to_numeric(filtered_schools[selected_pollutant_col], errors="coerce") == selected_pollutant_max
]["School Name"].dropna().tolist()

highest_pollutant_station_series = filtered_schools[
    pd.to_numeric(filtered_schools[selected_pollutant_col], errors="coerce") == selected_pollutant_max
]["nearest_station_name"].dropna()

highest_pollutant_station = highest_pollutant_station_series.iloc[0] if not highest_pollutant_station_series.empty else "NA"

avg_pm25 = pd.to_numeric(filtered_schools["selected_pm25"], errors="coerce").mean()
avg_pm10 = pd.to_numeric(filtered_schools["selected_pm10"], errors="coerce").mean()
avg_no2 = pd.to_numeric(filtered_schools["selected_no2"], errors="coerce").mean()
avg_distance = pd.to_numeric(filtered_schools["distance_km"], errors="coerce").mean()
max_distance = pd.to_numeric(filtered_schools["distance_km"], errors="coerce").max()


# -----------------------------
# KPI cards
# -----------------------------
st.subheader("Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Schools in this view", format_indian_number(schools_in_view))
col2.metric("Districts covered", filtered_schools["District"].nunique())
col3.metric("Monitoring stations linked", filtered_schools["nearest_station_id"].nunique())
col4.metric(
    f"Average {selected_pollutant} exposure ({selected_season_label})",
    f"{selected_pollutant_mean:.1f} µg/m³" if pd.notna(selected_pollutant_mean) else "NA"
)

col5, col6, col7, col8 = st.columns(4)
col5.metric("Average PM2.5 exposure", f"{avg_pm25:.1f} µg/m³" if pd.notna(avg_pm25) else "NA")
col6.metric("Average PM10 exposure", f"{avg_pm10:.1f} µg/m³" if pd.notna(avg_pm10) else "NA")
col7.metric("Average NO2 exposure", f"{avg_no2:.1f} µg/m³" if pd.notna(avg_no2) else "NA")
col8.metric("Average station distance", f"{avg_distance:.2f} km" if pd.notna(avg_distance) else "NA")

student_col1, student_col2 = st.columns(2)
student_col1.metric(
    "Students Affected*",
    format_indian_number(students_affected_in_view)
)
student_col2.metric(
    "Students Affected (full dataset)",
    format_indian_number(total_students_affected)
)

st.markdown(
    '<div class="metric-note"><span class="red-asterisk">*</span> Estimated using average enrolment of 808 students per school.</div>',
    unsafe_allow_html=True
)

if filters_active:
    st.info(
        f"Filters are active. The current view contains {format_indian_number(schools_in_view)} schools, "
        f"which corresponds to an estimated {format_indian_number(students_affected_in_view)} students affected*. "
        f"The full dataset reference remains {format_indian_number(total_students_affected)} students across "
        f"{format_indian_number(total_schools)} schools."
    )
else:
    st.info(
        f"No filters are active. The current view includes all {format_indian_number(total_schools)} schools in the dashboard, "
        f"corresponding to an estimated {format_indian_number(total_students_affected)} students affected*."
    )

st.markdown("---")


# -----------------------------
# Story highlights
# -----------------------------
st.subheader("Key highlights")

st.markdown(
    f"""
- **Selected season:** **{selected_season_label}**
- **Pollutant focus:** **{selected_pollutant}**
- **Highest estimated {selected_pollutant} exposure in this view:** **{selected_pollutant_max:.1f} µg/m³**
- **Nearest monitoring station behind that estimate:** **{highest_pollutant_station}**
- **Schools linked to that highest estimate:** **{", ".join(highest_pollutant_schools[:5]) if highest_pollutant_schools else "NA"}**
- **Estimated students represented in this view\\*:** **{format_indian_number(students_affected_in_view)}**
"""
)


# -----------------------------
# District chart
# -----------------------------
st.subheader(f"District-level {selected_pollutant} exposure — {selected_season_label}")

district_filtered = filtered_schools.groupby("District", dropna=False).agg(
    school_count=("School Name", "count"),
    selected_pollutant_mean=(selected_pollutant_col, "mean"),
    avg_distance_km=("distance_km", "mean")
).reset_index()

district_filtered["estimated_students_affected"] = district_filtered["school_count"].apply(estimate_students_affected)
district_filtered = district_filtered.sort_values("selected_pollutant_mean", ascending=False)

fig_district = px.bar(
    district_filtered.head(10),
    x="District",
    y="selected_pollutant_mean",
    title=f"Top districts by average {selected_pollutant} exposure ({selected_season_label})",
    labels={
        "selected_pollutant_mean": f"Average {selected_pollutant} exposure",
        "District": "District"
    },
    hover_data={
        "school_count": True,
        "estimated_students_affected": True,
        "selected_pollutant_mean": ":.2f",
        "avg_distance_km": ":.2f"
    }
)
st.plotly_chart(fig_district, use_container_width=True)

st.dataframe(
    format_district_table(district_filtered, selected_pollutant),
    use_container_width=True
)


# -----------------------------
# Top schools by selected pollutant
# -----------------------------
st.subheader(f"Schools with the highest estimated {selected_pollutant} exposure — {selected_season_label}")

top_selected_schools = (
    filtered_schools
    .sort_values(by=[selected_pollutant_col, "distance_km"], ascending=[False, True])
    .head(15)
)

st.dataframe(
    format_school_table(
        top_selected_schools,
        selected_pollutant_col,
        f"Estimated {selected_pollutant} exposure ({selected_season_label})"
    ),
    use_container_width=True
)


# -----------------------------
# Seasonal comparison tables
# -----------------------------
st.subheader("Winter burden comparison")

winter_compare_cols = [
    "School Name", "District", "Type", "nearest_station_name", "distance_km",
    "pm25_mean_winter", "pm25_mean_monsoon",
    "pm25_winter_minus_monsoon", "pm25_winter_to_monsoon_ratio",
    "exposure_confidence"
]

winter_compare_cols = [c for c in winter_compare_cols if c in filtered_schools.columns]

winter_jump_table = (
    filtered_schools[winter_compare_cols]
    .sort_values(by="pm25_winter_minus_monsoon", ascending=False)
    .head(15)
    .rename(columns={
        "School Name": "School",
        "Type": "School type",
        "nearest_station_name": "Nearest monitoring station",
        "distance_km": "Distance to nearest station (km)",
        "pm25_mean_winter": "PM2.5 Winter",
        "pm25_mean_monsoon": "PM2.5 Monsoon",
        "pm25_winter_minus_monsoon": "Winter - Monsoon",
        "pm25_winter_to_monsoon_ratio": "Winter / Monsoon",
        "exposure_confidence": "Confidence level"
    })
)

if "Distance to nearest station (km)" in winter_jump_table.columns:
    winter_jump_table["Distance to nearest station (km)"] = pd.to_numeric(
        winter_jump_table["Distance to nearest station (km)"], errors="coerce"
    ).round(2)

for col in ["PM2.5 Winter", "PM2.5 Monsoon", "Winter - Monsoon", "Winter / Monsoon"]:
    if col in winter_jump_table.columns:
        winter_jump_table[col] = pd.to_numeric(winter_jump_table[col], errors="coerce").round(2)

winter_jump_table = winter_jump_table.reset_index(drop=True)
winter_jump_table.index = winter_jump_table.index + 1

st.dataframe(winter_jump_table, use_container_width=True)


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

gap_table["Distance to nearest station (km)"] = pd.to_numeric(
    gap_table["Distance to nearest station (km)"], errors="coerce"
).round(2)
gap_table = gap_table.reset_index(drop=True)
gap_table.index = gap_table.index + 1

st.dataframe(gap_table, use_container_width=True)


# -----------------------------
# Reference seasonal tables
# -----------------------------
with st.expander("Reference tables: top winter and seasonal-jump schools"):
    st.markdown("**Top winter PM2.5 schools (citywide reference)**")
    st.dataframe(top_winter_reference.head(15), use_container_width=True, hide_index=True)

    st.markdown("**Top PM2.5 winter-vs-monsoon jump schools (citywide reference)**")
    st.dataframe(top_jump_reference.head(15), use_container_width=True, hide_index=True)


# -----------------------------
# Method note
# -----------------------------
st.markdown("---")
st.subheader("How to read this dashboard")

st.info(
    "These school-level pollution values are estimated exposure proxies, not direct measurements taken inside school campuses. "
    "The pollution data comes from daily 2025 readings collected at Delhi air-quality monitoring stations operated by CPCB, DPCC, and IITM. "
    "Each school was linked to its nearest monitoring station using latitude and longitude coordinates. "
    "For this seasonal dashboard, station pollution values were aggregated by season and assigned as each school's estimated exposure proxy for that season."
)

st.markdown(
    f"""
<div style="
    margin-top: 0.75rem;
    padding: 0.9rem 1rem;
    border-left: 4px solid #9aa0a6;
    background-color: rgba(240, 242, 246, 0.6);
    border-radius: 0.4rem;
    font-size: 0.92rem;
    line-height: 1.55;
">
<b>Dashboard note:</b> Student counts marked with <span style="color:#ff4b4b; font-weight:700;">*</span> are estimated using a Delhi-wide
average enrolment of <b>{AVG_ENROLMENT_DELHI}</b> students per school. This figure comes from reporting
that Delhi has <b>5,556 schools</b> serving <b>more than 44.9 lakh students</b>, which corresponds to an
average enrolment of <b>{AVG_ENROLMENT_DELHI}</b> students per school.<br><br>

<b>How we calculated it:</b><br>
- Without filters: <b>Total schools in dashboard × {AVG_ENROLMENT_DELHI}</b><br>
- With filters applied: <b>Schools in current filtered view × {AVG_ENROLMENT_DELHI}</b><br><br>

This is an estimated student exposure proxy, not school-wise observed enrolment data.<br>
<b>Source:</b> <a href="{ENROLMENT_SOURCE_URL}" target="_blank">ET Education</a>
</div>
""",
    unsafe_allow_html=True
)