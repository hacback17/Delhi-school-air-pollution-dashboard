import streamlit as st
from pathlib import Path
import pandas as pd

st.title("Debug test")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

st.write("App file loaded")
st.write("Base dir:", str(BASE_DIR))
st.write("Data dir exists:", DATA_DIR.exists())

target_file = DATA_DIR / "schools_with_exposure.csv"
st.write("schools_with_exposure.csv exists:", target_file.exists())

if target_file.exists():
    df = pd.read_csv(target_file)
    st.write("CSV loaded successfully")
    st.write("Rows:", len(df))
    st.dataframe(df.head())
else:
    st.error("CSV file not found")