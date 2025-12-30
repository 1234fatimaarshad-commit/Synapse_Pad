import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Synapse Pad",
    layout="wide"
)

# ---------------- SESSION STATE INIT ----------------
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "subjects" not in st.session_state:
    st.session_state.subjects = {}  # max 100 subjects

if "streak" not in st.session_state:
    st.session_state.streak = 0

if "daily_tasks" not in st.session_state:
    st.session_state.daily_tasks = []

# ---------------- SIDEBAR ----------------
st.sidebar.title("🧠 Synapse Pad")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Subject Explorer", "Global AI"]
)

st.session_state.page = page

# ---------------- PAGE ROUTER ----------------
if st.session_state.page == "Dashboard":
    st.title("📊 Main Dashboard")
    st.write("Calendar • Strong AI • Subjects")

elif st.session_state.page == "Subject Explorer":
    st.title("📚 Subject Explorer")
    st.write("Up to 100 Subjects")

elif st.session_state.page == "Global AI":
    st.title("🤖 Global AI")
    st.write("Quiz • Flashcards • Study Help")
