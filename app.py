import streamlit as st
import sqlite3
import requests
from datetime import datetime, date

# ------------------- Page Config -------------------
st.set_page_config(page_title="Synapse Pad", layout="wide")

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()

# Table for Subjects
cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    name TEXT PRIMARY KEY,
    attendance INTEGER DEFAULT 0
)
""")

# Unified Table for Lectures and Tasks
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT, 
    minutes INTEGER,
    item_date TEXT
)
""")
conn.commit()

# ------------------- Session State -------------------
if "subjects" not in st.session_state:
    try:
        cursor.execute("SELECT name FROM subjects")
        st.session_state.subjects = [row[0] for row in cursor.fetchall()]
    except:
        st.session_state.subjects = []

# ------------------- AI Scheduling Logic (16 Hour Limit) -------------------
LIMIT_MINUTES = 960  # 16 Hours

def get_total_minutes(sel_date):
    cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
    res = cursor.fetchone()
    return res[0] if res[0] else 0

def add_schedule_item(name, minutes, sel_date, item_type):
    if not name.strip(): return False
    
    current_total = get_total_minutes(sel_date)
    
    if (current_total + minutes) > LIMIT_MINUTES:
        st.error(f"⚠️ AI Alert: This exceeds the 16-hour limit ({current_total + minutes} mins). Please reschedule!")
        return False
    
    cursor.execute("INSERT INTO items(name, type, minutes, item_date) VALUES (?,?,?,?)",
                   (name, item_type, minutes, sel_date))
    conn.commit()
    st.success(f"{item_type} Added!")
    return True

# ------------------- Page Functions -------------------

def dashboard_page():
    st.title("📊 Main Dashboard")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🗓️ Daily Planner")
        sel_date = st.date_input("Select Date", date.today()).strftime("%Y-%m-%d")
        
        # 16-hour Capacity tracker
        mins_used = get_total_minutes(sel_date)
        progress = min(mins_used / LIMIT_MINUTES, 1.0)
        
        st.write(f"**AI Capacity Used:** {mins_used} / {LIMIT_MINUTES} mins")
        st.progress(progress)
        
        if progress > 0.8:
            st.warning("Warning: You are approaching the 16-hour limit!")

        st.divider()
        
        # RENAMED SECTION: To-Do List
        st.subheader("📝 To-Do List")
        item_name = st.text_input("Entry Name (Lecture or Task)")
        duration = st.number_input("Duration (Minutes)", min_value=15, max_value=480, step=15, value=60)
        item_type = st.selectbox("Type", ["Task", "Lecture"])
        
        if st.button("Add to Schedule", use_container_width=True):
            if add_schedule_item(item_name, duration,
