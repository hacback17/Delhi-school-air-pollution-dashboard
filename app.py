import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Optional
import plotly.express as px

st.set_page_config(
    page_title="Delhi School Air Pollution Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
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

SEASON_ORDER = ["Winter", "Post-Monsoon", "Summer", "Monsoon", "Rainy"]

WHO_GUIDELINES = {
    "pm25": {"annual": 5.0, "daily": 15.0, "label": "PM2.5"},
    "pm10": {"annual": 15.0, "daily": 45.0, "label": "PM10"},
    "no2": {"annual": 10.0, "daily": 25.0, "label": "NO₂"},
}


def load_css():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .metric-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 1rem 1rem 0.85rem 1rem;
            margin-bottom: 0.75rem;
            min-height: 116px;
        }
        .small-note {
            color: #A0A0A0;
            font-size: 0.9rem;
            margin-bottom: 0.3rem;
        }
        .school-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .metric-value {
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.35;
            word-break: break-word;
        }
        .metric-sub {
            font-size: 0.88rem;
            color: #C0C0C0;
            margin-top: 0.4rem;
        }
        </style>
        <style>
        div[data-testid="stDataFrame"] {
            padding-top: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def detect_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    lowered = {str(c).lower(): c for c in df.columns}

    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]

    for col in df.columns:
        col_l = str(col).lower()
        for cand in candidates:
            if cand.lower() in col_l:
                return col

    return None


def format_num(x, digits=1) -> str:
    if x is None or pd.isna(x):
        return "NA"
    try:
        return f"{float(x):,.{digits}f}"
    except Exception:
        return str(x)


def ratio_text(value: float, guideline: float) -> str:
    if value is None or pd.isna(value) or guideline in [None, 0]:
        return "NA"
    return f"{float(value) / guideline:.1f} times higher"


def concern_label(value: float, annual_guideline: float) -> str:
    if value is None or pd.isna(value):
        return "Unknown"
    ratio = float(value) / annual_guideline
    if ratio <= 1:
        return "Within guideline"
    if ratio <= 3:
        return "Elevated"
    if ratio <= 10:
        return "High concern"
    return "Very high concern"


def render_card(title: str, value: str, subtitle: Optional[str] = None):
    subtitle_html = f'<div class="metric-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="small-note">{title}</div>
            <div class="metric-value">{value}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_who_reference():
    st.markdown("### WHO benchmark values")
    cols = st.columns(3)

    benchmarks = [
        ("PM2.5", "5 µg/m³ annual mean", "15 µg/m³ daily (24-hour mean)"),
        ("PM10", "15 µg/m³ annual mean", "45 µg/m³ daily (24-hour mean)"),
        ("NO₂", "10 µg/m³ annual mean", "25 µg/m³ daily (24-hour mean)"),
    ]

    for col, (title, annual_text, daily_text) in zip(cols, benchmarks):
        with col:
            render_card(title, annual_text, daily_text)

    st.caption(
        "‘24-hour’ means a daily-average WHO benchmark for short-term exposure. "
        "This dashboard mainly uses seasonal exposure estimates, so the daily value is shown only as a health reference, not as a measured increase within the app."
    )


def school_options(df: pd.DataFrame, school_col: str) -> List[str]:
    return sorted(df[school_col].dropna().astype(str).unique().tolist())


def build_school_profile(df: pd.DataFrame, school_name: str) -> dict:
    school_df = df[df["School Name"] == school_name].copy()

    if school_df.empty:
        return {}

    season_rows = []
    for season_label, season_key in SEASON_LABELS.items():
        pm25_col = season_col("pm25_mean", season_key)
        pm10_col = season_col("pm10_mean", season_key)
        no2_col = season_col("no2_mean", season_key)

        row = school_df.iloc[0]
        season_rows.append({
            "Season": season_label,
            "PM2.5": pd.to_numeric(pd.Series([row.get(pm25_col)]), errors="coerce").iloc[0] if pm25_col in school_df.columns else np.nan,
            "PM10": pd.to_numeric(pd.Series([row.get(pm10_col)]), errors="coerce").iloc[0] if pm10_col in school_df.columns else np.nan,
            "NO2": pd.to_numeric(pd.Series([row.get(no2_col)]), errors="coerce").iloc[0] if no2_col in school_df.columns else np.nan,
        })

    seasonal_df = pd.DataFrame(season_rows)

    pm25_series = pd.to_numeric(seasonal_df["PM2.5"], errors="coerce")
    pm10_series = pd.to_numeric(seasonal_df["PM10"], errors="coerce")
    no2_series = pd.to_numeric(seasonal_df["NO2"], errors="coerce")

    worst_pm25_season = "NA"
    worst_pm25_value = np.nan
    if pm25_series.notna().sum() > 0:
        idx = int(pm25_series.idxmax())
        worst_pm25_season = seasonal_df.iloc[idx]["Season"]
        worst_pm25_value = pm25_series.iloc[idx]

    worst_pm10_value = np.nan
    if pm10_series.notna().sum() > 0:
        worst_pm10_value = pm10_series.max()

    worst_no2_value = np.nan
    if no2_series.notna().sum() > 0:
        worst_no2_value = no2_series.max()

    profile = {
        "School": school_name,
        "District": school_df["District"].dropna().iloc[0] if "District" in school_df.columns and school_df["District"].dropna().shape[0] else "NA",
        "School type": school_df["Type"].dropna().iloc[0] if "Type" in school_df.columns and school_df["Type"].dropna().shape[0] else "NA",
        "Nearest station": school_df["nearest_station_name"].dropna().iloc[0] if "nearest_station_name" in school_df.columns and school_df["nearest_station_name"].dropna().shape[0] else "NA",
        "Station distance": school_df["distance_km"].dropna().iloc[0] if "distance_km" in school_df.columns and school_df["distance_km"].dropna().shape[0] else np.nan,
        "Confidence": school_df["exposure_confidence"].dropna().iloc[0] if "exposure_confidence" in school_df.columns and school_df["exposure_confidence"].dropna().shape[0] else "NA",
        "Worst PM2.5 season": worst_pm25_season,
        "Worst PM2.5": worst_pm25_value,
        "Worst PM10": worst_pm10_value,
        "Worst NO2": worst_no2_value,
        "seasonal_df": seasonal_df
    }
    return profile


def render_parent_summary(profile: dict):
    if not profile:
        st.warning("No school profile available.")
        return

    st.markdown(f"<div class='school-title'>{profile['School']}</div>", unsafe_allow_html=True)

    row1 = st.columns(3)
    row2 = st.columns(3)
    row3 = st.columns(3)

    with row1[0]:
        render_card("District", str(profile.get("District", "NA")))

    with row1[1]:
        render_card("School type", str(profile.get("School type", "NA")))

    with row1[2]:
        render_card("Nearest station", str(profile.get("Nearest station", "NA")))

    with row2[0]:
        dist = profile.get("Station distance", np.nan)
        render_card("Station distance", f"{format_num(dist, 2)} km" if pd.notna(dist) else "NA")

    with row2[1]:
        render_card("Confidence", str(profile.get("Confidence", "NA")))

    with row2[2]:
        render_card(
            "Worst PM2.5 season",
            str(profile.get("Worst PM2.5 season", "NA")),
            f"{format_num(profile.get('Worst PM2.5', np.nan))} µg/m³"
        )

    with row3[0]:
        pm25 = profile.get("Worst PM2.5", np.nan)
        render_card(
            "Worst PM2.5",
            f"{format_num(pm25)} µg/m³",
            f"{ratio_text(pm25, WHO_GUIDELINES['pm25']['annual'])} of WHO annual"
        )

    with row3[1]:
        pm10 = profile.get("Worst PM10", np.nan)
        render_card(
            "Worst PM10",
            f"{format_num(pm10)} µg/m³",
            f"{ratio_text(pm10, WHO_GUIDELINES['pm10']['annual'])} of WHO annual"
        )

    with row3[2]:
        no2 = profile.get("Worst NO2", np.nan)
        render_card(
            "Worst NO₂",
            f"{format_num(no2)} µg/m³",
            f"{ratio_text(no2, WHO_GUIDELINES['no2']['annual'])} of WHO annual"
        )

    pm25 = profile.get("Worst PM2.5", np.nan)
    st.markdown("### Plain-language interpretation")
    st.info(
        f"The highest seasonal PM2.5 estimate for this school is **{format_num(pm25)} µg/m³** "
        f"in **{profile.get('Worst PM2.5 season', 'NA')}**, which is **{ratio_text(pm25, WHO_GUIDELINES['pm25']['annual'])}** "
        f"the WHO annual guideline and indicates **{concern_label(pm25, WHO_GUIDELINES['pm25']['annual']).lower()}** exposure relative to that benchmark."
    )


def render_season_profile(seasonal_df: pd.DataFrame):
    st.markdown("### Season-wise school profile")

    if seasonal_df.empty:
        st.warning("No seasonal records available for this school.")
        return

    cols = st.columns(min(4, len(seasonal_df)))
    for i, (_, row) in enumerate(seasonal_df.iterrows()):
        with cols[i % len(cols)]:
            st.markdown(f"#### {row['Season']}")
            st.metric("PM2.5", f"{format_num(row.get('PM2.5', np.nan))} µg/m³")
            st.metric("PM10", f"{format_num(row.get('PM10', np.nan))} µg/m³")
            st.metric("NO₂", f"{format_num(row.get('NO2', np.nan))} µg/m³")

    st.dataframe(seasonal_df, use_container_width=True, hide_index=True)


def render_who_comparison(seasonal_df: pd.DataFrame):
    st.markdown("### WHO comparison by season")

    rows = []
    for _, row in seasonal_df.iterrows():
        rows.append({
            "Season": row["Season"],
            "PM2.5": format_num(row.get("PM2.5", np.nan)),
            "PM2.5 vs WHO annual": ratio_text(row.get("PM2.5", np.nan), WHO_GUIDELINES["pm25"]["annual"]),
            "PM10": format_num(row.get("PM10", np.nan)),
            "PM10 vs WHO annual": ratio_text(row.get("PM10", np.nan), WHO_GUIDELINES["pm10"]["annual"]),
            "NO2": format_num(row.get("NO2", np.nan)),
            "NO2 vs WHO annual": ratio_text(row.get("NO2", np.nan), WHO_GUIDELINES["no2"]["annual"]),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_sidebar_filters(enabled: bool):
    st.sidebar.header("Filter the dashboard")
    if not enabled:
        st.sidebar.caption("Filters are enabled only in the Analyst dashboard view.")

    selected_season_label = st.sidebar.selectbox(
        "Season",
        ["Winter", "Summer", "Monsoon", "Post-Monsoon"],
        index=0,
        disabled=not enabled,
        key="selected_season_label"
    )

    selected_pollutant = st.sidebar.selectbox(
        "Pollutant focus",
        ["PM2.5", "PM10", "NO2"],
        index=0,
        disabled=not enabled,
        key="selected_pollutant"
    )

    district_options = ["All districts"] + sorted(schools["District"].dropna().unique().tolist())
    type_options = ["All school types"] + sorted(schools["Type"].dropna().unique().tolist())
    confidence_options = ["All confidence levels"] + sorted(schools["exposure_confidence"].dropna().unique().tolist())

    selected_district = st.sidebar.selectbox(
        "District",
        district_options,
        disabled=not enabled,
        key="selected_district"
    )

    selected_type = st.sidebar.selectbox(
        "School type",
        type_options,
        disabled=not enabled,
        key="selected_type"
    )

    selected_confidence = st.sidebar.selectbox(
        "Confidence level",
        confidence_options,
        disabled=not enabled,
        key="selected_confidence"
    )

    return {
        "season_label": selected_season_label,
        "season_key": SEASON_LABELS[selected_season_label],
        "pollutant": selected_pollutant,
        "district": selected_district,
        "type": selected_type,
        "confidence": selected_confidence,
    }


def render_find_school_tab():
    st.markdown("## Find a school")

    school_col = "School Name"
    options = school_options(schools, school_col)

    left, right = st.columns([1.2, 1.8])

    with left:
        query = st.text_input(
            "Type part of a school name",
            placeholder="e.g. govt, delhi public, sarvodaya",
            key="school_search"
        ).strip()

    filtered = options
    if query:
        filtered = [s for s in options if query.lower() in s.lower()]

    with right:
        selected_school = st.selectbox(
            "Matching schools",
            filtered if filtered else ["No matches found"],
            index=0,
            key="school_select"
        )

    if not filtered:
        st.warning("No school matched your search. Try fewer words or a simpler spelling.")
        return

    profile = build_school_profile(schools, selected_school)
    render_parent_summary(profile)
    render_season_profile(profile["seasonal_df"])
    render_who_reference()
    render_who_comparison(profile["seasonal_df"])

    with st.expander("Technical details for this school"):
        st.dataframe(
            pd.DataFrame([{
                "School": profile.get("School"),
                "District": profile.get("District"),
                "School type": profile.get("School type"),
                "Nearest station": profile.get("Nearest station"),
                "Distance (km)": format_num(profile.get("Station distance"), 2),
                "Confidence": profile.get("Confidence"),
            }]),
            use_container_width=True,
            hide_index=True
        )


def render_compare_schools_tab():
    st.markdown("## Compare schools")

    selected = st.multiselect(
        "Choose up to 3 schools",
        options=school_options(schools, "School Name"),
        max_selections=3,
        placeholder="Search and select schools to compare",
        key="compare_school_select"
    )

    if len(selected) == 0:
        st.info("Choose up to 3 schools to compare.")
        return

    comparison_rows = []

    for school_name in selected:
        profile = build_school_profile(schools, school_name)

        if not profile:
            continue

        comparison_rows.append({
            "School": profile.get("School", "NA"),
            "District": profile.get("District", "NA"),
            "School type": profile.get("School type", "NA"),
            "Nearest station": profile.get("Nearest station", "NA"),
            "Distance (km)": format_num(profile.get("Station distance", np.nan), 2),
            "Confidence": profile.get("Confidence", "NA"),
            "Worst PM2.5 season": profile.get("Worst PM2.5 season", "NA"),
            "Worst PM2.5": format_num(profile.get("Worst PM2.5", np.nan), 1),
            "Worst PM10": format_num(profile.get("Worst PM10", np.nan), 1),
            "Worst NO₂": format_num(profile.get("Worst NO2", np.nan), 1),
        })

    if len(comparison_rows) == 0:
        st.warning("No comparable school records were found.")
        return

    comparison_df = pd.DataFrame(comparison_rows)
    st.write("Your selected schools")
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)


def render_analyst_dashboard_tab(filters: dict):
    st.markdown("## Analyst dashboard")
    st.caption(
        "Estimated school exposure based on the nearest air-quality monitoring station in Delhi "
        "(season-wise station-linked exposure for 2025)"
    )

    selected_season_label = filters["season_label"]
    selected_season = filters["season_key"]
    selected_pollutant = filters["pollutant"]
    selected_district = filters["district"]
    selected_type = filters["type"]
    selected_confidence = filters["confidence"]

    filtered_schools = add_selected_exposure_columns(schools, selected_season)

    if selected_district != "All districts":
        filtered_schools = filtered_schools[filtered_schools["District"] == selected_district]

    if selected_type != "All school types":
        filtered_schools = filtered_schools[filtered_schools["Type"] == selected_type]

    if selected_confidence != "All confidence levels":
        filtered_schools = filtered_schools[filtered_schools["exposure_confidence"] == selected_confidence]

    if filtered_schools.empty:
        st.warning("No schools match the current filter selection.")
        return

    selected_pollutant_col = {
        "PM2.5": "selected_pm25",
        "PM10": "selected_pm10",
        "NO2": "selected_no2"
    }[selected_pollutant]

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

    st.subheader("Overview")

    kpi_col1, kpi_col2 = st.columns(2)

    with kpi_col1:
        if pd.notna(selected_pollutant_mean):
            st.info(
                f"Schools in this view: {format_indian_number(schools_in_view)}\n\n"
                f"Districts covered: {filtered_schools['District'].nunique()}\n\n"
                f"Monitoring stations linked: {filtered_schools['nearest_station_id'].nunique()}\n\n"
                f"Average {selected_pollutant} exposure ({selected_season_label}): "
                f"{selected_pollutant_mean:.1f} µg/m³"
            )
        else:
            st.info(f"Schools in this view: {format_indian_number(schools_in_view)}")

    with kpi_col2:
        st.info(
            f"Average PM2.5 exposure: {avg_pm25:.1f} µg/m³\n\n"
            f"Average PM10 exposure: {avg_pm10:.1f} µg/m³\n\n"
            f"Average NO2 exposure: {avg_no2:.1f} µg/m³\n\n"
            f"Average station distance: {avg_distance:.2f} km\n\n"
            f"Farthest school from station: {max_distance:.2f} km"
        )

    student_col1, student_col2 = st.columns(2)
    with student_col1:
        st.info(f"Students Affected*: {format_indian_number(students_affected_in_view)}")
    with student_col2:
        st.info(f"Students Affected (full dataset): {format_indian_number(total_students_affected)}")

    st.caption("* Estimated using average enrolment of 808 students per school.")

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

    st.table(format_district_table(district_filtered, selected_pollutant))

    st.subheader(f"Schools with the highest estimated {selected_pollutant} exposure — {selected_season_label}")

    top_selected_schools = (
        filtered_schools
        .sort_values(by=[selected_pollutant_col, "distance_km"], ascending=[False, True])
        .head(15)
    )

    st.table(
        format_school_table(
            top_selected_schools,
            selected_pollutant_col,
            f"Estimated {selected_pollutant} exposure ({selected_season_label})"
        )
    )

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

    st.table(winter_jump_table)

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

    st.table(gap_table)

    with st.expander("Reference tables: top winter and seasonal-jump schools"):
        st.markdown("**Top winter PM2.5 schools (citywide reference)**")
        st.table(top_winter_reference.head(15))

        st.markdown("**Top PM2.5 winter-vs-monsoon jump schools (citywide reference)**")
        st.table(top_jump_reference.head(15))

    st.markdown("---")
    st.subheader("How to read this dashboard")

    st.info(
        "These school-level pollution values are estimated exposure proxies, not direct measurements taken inside school campuses. "
        "The pollution data comes from daily 2025 readings collected at Delhi air-quality monitoring stations operated by CPCB, DPCC, and IITM. "
        "Each school was linked to its nearest monitoring station using latitude and longitude coordinates. "
        "For this seasonal dashboard, station pollution values were aggregated by season and assigned as each school's estimated exposure proxy for that season."
    )

    st.info(
        f"Dashboard note: Student counts marked with * are estimated using a Delhi-wide average enrolment of "
        f"{AVG_ENROLMENT_DELHI} students per school. This figure comes from reporting that Delhi has 5,556 schools "
        f"serving more than 44.9 lakh students, which corresponds to an average enrolment of {AVG_ENROLMENT_DELHI} "
        f"students per school.\n\n"
        f"How we calculated it:\n"
        f"- Without filters: Total schools in dashboard × {AVG_ENROLMENT_DELHI}\n"
        f"- With filters applied: Schools in current filtered view × {AVG_ENROLMENT_DELHI}\n\n"
        f"This is an estimated student exposure proxy, not school-wise observed enrolment data.\n"
        f"Source: {ENROLMENT_SOURCE_URL}"
    )


def main():
    load_css()

    st.title("Delhi School Air Pollution Dashboard")
    st.caption(
        "Parent-facing school lookup plus full analyst dashboard with Delhi school exposure filters."
    )

    view = st.radio(
        "Choose view",
        ["Find a school", "Compare schools", "Analyst dashboard"],
        horizontal=True,
        label_visibility="collapsed"
    )

    filters = render_sidebar_filters(enabled=(view == "Analyst dashboard"))

    if view == "Find a school":
        render_find_school_tab()
    elif view == "Compare schools":
        render_compare_schools_tab()
    else:
        render_analyst_dashboard_tab(filters)


if __name__ == "__main__":
    main()