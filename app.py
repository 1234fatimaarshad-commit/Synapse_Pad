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
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY, attendance INTEGER DEFAULT 0)")
# Unified Table for Items (Lectures/Tasks)
cursor.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, minutes INTEGER, item_date TEXT)")
conn.commit()

# ------------------- Session State -------------------
if "subjects" not in st.session_state:
    try:
        cursor.execute("SELECT name FROM subjects")
        st.session_state.subjects = [row[0] for row in cursor.fetchall()]
    except:
        st.session_state.subjects = []

# ------------------- AI Logic (16 Hour Limit) -------------------
LIMIT_MINUTES = 960  # 16 Hours

def get_total_minutes(sel_date):
    cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
    res = cursor.fetchone()
    return res[0] if res[0] else 0

# ------------------- Sidebar Navigation -------------------
with st.sidebar:
    st.title("🚀 Synapse Pad")
    # THE SEARCH BAR
    search_query = st.text_input("🔍 Search Folders", "").lower()
    
    st.divider()
    # Main Navigation
    page = st.radio("Navigate", ["📊 Dashboard", "🌍 Global AI", "📂 Subject Explorer"])
    
    # Filtered Subjects for the Explorer
    filtered_subs = [s for s in st.session_state.subjects if search_query in s.lower()]

# ------------------- Dashboard Page -------------------
if page == "📊 Dashboard":
    st.title("📊 Main Dashboard")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🗓️ Daily Planner")
        sel_date = st.date_input("Select Date", date.today()).strftime("%Y-%m-%d")
        
        mins_used = get_total_minutes(sel_date)
        progress = min(mins_used / LIMIT_MINUTES, 1.0)
        
        st.write(f"**AI Capacity:** {mins_used} / {LIMIT_MINUTES} mins (16hr)")
        st.progress(progress)
        
        st.divider()
        st.subheader("📝 To-Do List") # UPDATED NAME
        item_name = st.text_input("Lecture or Task Name")
        duration = st.number_input("Duration (Minutes)", min_value=15, step=15, value=60)
        item_type = st.selectbox("Type", ["Task", "Lecture"])
        
        if st.button("Add to Schedule"):
            if item_name.strip():
                if (mins_used + duration) > LIMIT_MINUTES:
                    st.error("⚠️ AI Alert: Exceeds 16-hour limit!")
                else:
                    cursor.execute("INSERT INTO items(name, type, minutes, item_date) VALUES (?,?,?,?)", (item_name, item_type, duration, sel_date))
                    conn.commit()
                    st.success("Added!")
                    st.rerun()

        st.divider()
        st.subheader("📁 New Folder")
        new_sub = st.text_input("Subject Name")
        if st.button("Create Folder"):
            if new_sub.strip():
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_sub,))
                conn.commit()
                if new_sub not in st.session_state.subjects: st.session_state.subjects.append(new_sub)
                st.rerun()

    with col2:
        st.subheader(f"📋 Timeline: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes FROM items WHERE item_date=?", (sel_date,))
        items = cursor.fetchall()
        for i_id, i_name, i_type, i_mins in items:
            icon = "🧠" if i_type == "Task" else "🏫"
            cols = st.columns([4, 1])
            cols[0].info(f"{icon} **{i_name}** ({i_mins}m)")
            if cols[1].button("🗑️", key=f"del_{i_id}"):
                cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                conn.commit()
                st.rerun()

# ------------------- Subject Explorer Page -------------------
elif page == "📂 Subject Explorer":
    st.title("📂 Subject Explorer")
    if not filtered_subs:
        st.info("No folders found matching your search.")
    else:
        choice = st.selectbox("Open Folder:", filtered_subs)
        st.header(f"📁 Folder: {choice}")
        
        if st.button("🗑️ Delete this Folder"):
            cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
            conn.commit()
            st.session_state.subjects.remove(choice)
            st.rerun()
            
        st.divider()
        cursor.execute("SELECT attendance FROM subjects WHERE name=?", (choice,))
        att = cursor.fetchone()[0]
        st.metric("Total Attendance", att)
        
        if st.button("Mark Attendance"):
            cursor.execute("UPDATE subjects SET attendance = attendance + 1 WHERE name=?", (choice,))
            conn.commit()
            st.rerun()

# ------------------- Global AI Page -------------------
elif page == "🌍 Global AI":
    st.title("🌍 Global AI Assistant")
    user_q = st.text_input("Ask Synapse AI:")
    if st.button("Generate"):
        try:
            hf_token = st.secrets["HF_TOKEN"]
            API_URL = "https://router.huggingface.co/v1/chat/completions"
            headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
            payload = {"model": "meta-llama/Llama-3.2-3B-Instruct", "messages": [{"role": "user", "content": user_q}]}
            res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
            st.write(res.json()['choices'][0]['message']['content'])
        except:
            st.error("Error connecting to AI. Check your Token.")
