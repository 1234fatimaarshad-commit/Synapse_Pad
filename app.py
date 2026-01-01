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
        st.error(f"⚠️ AI Alert: This exceeds the 16-hour limit ({current_total + minutes} mins). Please reschedule some items!")
        return False
    
    cursor.execute("INSERT INTO items(name, type, minutes, item_date) VALUES (?,?,?,?)",
                   (name, item_type, minutes, sel_date))
    conn.commit()
    st.success(f"{item_type} Added successfully!")
    return True

# ------------------- Page Functions -------------------

def dashboard_page():
    st.title("🗓️ Intelligent 16-Hour Scheduler")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📅 Plan Your Day")
        sel_date = st.date_input("Select Date", date.today()).strftime("%Y-%m-%d")
        
        # Calculate Progress based on 16 hours
        mins_used = get_total_minutes(sel_date)
        progress = min(mins_used / LIMIT_MINUTES, 1.0)
        
        # Color the bar based on load
        if progress < 0.7:
            st.progress(progress) # Blue/Green
        else:
            st.progress(progress) # Progress bar stays blue, but we add a warning
            st.warning("High workload detected!")

        st.write(f"**AI Capacity Used:** {mins_used} / {LIMIT_MINUTES} minutes (16hr Cap)")
        
        st.divider()
        
        # Inputs
        item_name = st.text_input("Lecture or Task Name")
        duration = st.number_input("Duration (Minutes)", min_value=15, max_value=480, step=15, value=60)
        item_type = st.selectbox("Type", ["Lecture", "Task"])
        
        if st.button("Add to Schedule", use_container_width=True):
            if add_schedule_item(item_name, duration, sel_date, item_type):
                st.rerun()

    with col2:
        st.subheader(f"📋 Timeline for {sel_date}")
        cursor.execute("SELECT name, type, minutes FROM items WHERE item_date=?", (sel_date,))
        daily_items = cursor.fetchall()
        
        if not daily_items:
            st.info("No items scheduled. Start planning your day!")
        else:
            for name, itype, mins in daily_items:
                icon = "🏫" if itype == "Lecture" else "🧠"
                st.info(f"**{icon} {name}** — {mins} mins")

def subject_folder_page(choice):
    st.title(f"📁 Folder: {choice}")
    
    col_del1, col_del2 = st.columns([3,1])
    with col_del2:
        if st.button("
