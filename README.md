# Delhi School Air Pollution Dashboard

An interactive Streamlit dashboard that estimates school-level air pollution exposure across Delhi by linking each school to its nearest air-quality monitoring station.

## What this project does

This project combines school location data with Delhi air-quality monitoring data (2025) to estimate how much pollution schools are likely exposed to. It is designed as a public-facing dashboard and analysis workflow, not just a notebook exercise.

The pipeline:

1. Builds a clean master list of Delhi monitoring stations (2025). Source: https://airquality.cpcb.gov.in/ccr/#/repository/data
2. Ingests daily station pollution files and computes yearly pollutant summaries.
3. Links each school to its nearest monitoring station using geographic distance.
4. Produces district, school-type, and school-level exposure summaries.
5. Serves the results through a Streamlit dashboard.

Schools:
1. https://www.edudel.nic.in/mis/eis/frmSchoolList.aspx?type=nTH2RniV/856b7vqlJz82MWFG0Y5sfJown1h2Tv10v0=
2. https://www.edudel.nic.in/mis/eis/frmSchoolList.aspx?type=8v6AC39/z0ySjVIkvfDJzvxkdDvmSsz7pgALKMjL3UI=
## Main idea behind the exposure estimate

The dashboard does **not** claim that pollution was directly measured inside each school campus.

Instead, each school is assigned the yearly mean pollution levels of its **nearest monitoring station**, based on latitude and longitude coordinates. That means the values shown in the dashboard are best interpreted as:

- estimated school exposure,
- nearest-station pollution proxy values,
- or school-level exposure estimates derived from nearby monitoring stations.

## Data sources used

### School data
- Delhi school dataset with school names, addresses, district labels, school type, school level, and coordinates.

### Air pollution data
- Daily 2025 air-quality readings from Delhi monitoring stations operated by:
  - CPCB
  - DPCC
  - IITM

### Pollutants summarized
Depending on station availability, the processed station summaries include metrics such as:

- PM2.5
- PM10
- NO2
- NO
- NOx
- NH3
- SO2
- CO
- Ozone
- Benzene
- Toluene

## Project structure

```text
DELHI_SCHOOL_AIR_POLLUTION/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── raw/
│   ├── api/
│   └── processed/
│       ├── stations_master.csv
│       ├── station_pollution_stats.csv
│       ├── station_daily_combined.csv
│       ├── schools_with_exposure.csv
│       ├── district_exposure_summary.csv
│       ├── type_exposure_summary.csv
│       ├── level_exposure_summary.csv
│       ├── top_exposed_schools.csv
│       ├── farthest_schools.csv
│       ├── station_coverage_summary.csv
│       └── exposure_confidence_summary.csv
├── notebooks/
└── output/
```

## Key output files

| File | Meaning |
|---|---|
| `stations_master.csv` | Clean station directory with station IDs, names, networks, and coordinates |
| `station_pollution_stats.csv` | One row per station with yearly pollutant summary statistics |
| `station_daily_combined.csv` | Combined daily station-level pollution records |
| `schools_with_exposure.csv` | Main school-level file linking every school to its nearest station and estimated exposure |
| `district_exposure_summary.csv` | District-level exposure summary |
| `type_exposure_summary.csv` | School-type exposure summary |
| `level_exposure_summary.csv` | School-level category summary |
| `top_exposed_schools.csv` | Highest estimated exposure schools |
| `farthest_schools.csv` | Schools farthest from a monitoring station |
| `station_coverage_summary.csv` | Number of schools assigned to each station |
| `exposure_confidence_summary.csv` | Confidence buckets based on distance to nearest station |

## How the nearest-station mapping works

Each school is matched to the nearest monitoring station using latitude and longitude coordinates. The nearest-station distance is calculated geographically, and that station's pollution summary is then attached to the school.

A simple confidence rule is used:

- High confidence: school is within 5 km of the nearest station
- Medium confidence: school is between 5 and 10 km away
- Low confidence: school is more than 10 km away

This helps separate strong school-to-station matches from weaker monitoring coverage areas.

## Dashboard features

The Streamlit dashboard includes:

- Overall KPI cards
- District-level PM2.5 comparison
- School-type comparison
- Highest estimated PM2.5, PM10, and NO2 exposure schools
- Monitoring-gap schools farthest from stations
- Filter controls for district, school type, and confidence level
- Methodology note explaining how the exposure estimate was built

## Run locally

Create and activate a virtual environment, install dependencies, then run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If `streamlit` is not recognized in the shell, use:

```bash
python -m streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. Sign in to Streamlit Community Cloud with GitHub.
3. Create a new app.
4. Select this repository and branch.
5. Set the main file path to `app.py`.
6. Deploy.

## Important interpretation note

The dashboard should be read as a **school exposure estimation project**, not as a direct on-campus measurement project. The values shown for schools come from the nearest available station's processed pollution readings.

That means the dashboard is strongest for:

- hotspot detection,
- district comparison,
- school burden screening,
- and identifying monitoring gaps.

It is weaker for claims like “this exact pollution level was measured inside this exact school.”

## Possible next improvements

- Add an interactive map of schools and monitoring stations
- Add time-series views from the daily station data
- Add downloadable filtered tables
- Add district spotlight summaries and narrative annotations
- Add policy-oriented views for underserved monitoring zones