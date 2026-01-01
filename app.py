import streamlit as st
import sqlite3
import requests
from datetime import datetime, date

# v8.0 - SYNAPSE AI VERSION
st.set_page_config(page_title="Synapse Pad", layout="wide")

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY, attendance INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, minutes INTEGER, item_date TEXT)")
conn.commit()

# ------------------- Session State -------------------
if "subjects" not in st.session_state:
    try:
        cursor.execute("SELECT name FROM subjects")
        st.session_state.subjects = [row[0] for row in cursor.fetchall()]
    except:
        st.session_state.subjects = []

# ------------------- Sidebar -------------------
with st.sidebar:
    st.title("🚀 Synapse Pad")
    st.write("System Status: **Active**")
    search_query = st.text_input("🔍 Search Folders", "").lower()
    st.divider()
    # RENAMED: Global AI -> Synapse AI
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    filtered_subs = [s for s in st.session_state.subjects if search_query in s.lower()]

# ------------------- Dashboard -------------------
if page == "📊 Dashboard":
    st.title("📊 Main Dashboard")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🗓️ Daily Planner")
        sel_date = st.date_input("Select Date", date.today()).strftime("%Y-%m-%d")
        
        # 16 HOUR LOGIC (960 Minutes)
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        res = cursor.fetchone()
        mins_used = res[0] if res[0] else 0
        progress = min(mins_used / 960, 1.0)
        
        st.write(f"**AI Capacity:** {mins_used} / 960 mins")
        st.progress(progress)
        
        st.divider()
        st.subheader("📝 To-Do List")
        item_name = st.text_input("Name (Lecture/Task)")
        duration = st.number_input("Minutes", min_value=15, step=15, value=60)
        item_type = st.selectbox("Type", ["Task", "Lecture"])
        
        if st.button("Add to Schedule"):
            if item_name.strip():
                if (mins_used + duration) > 960:
                    st.error("⚠️ AI Alert: Capacity Exceeded!")
                else:
                    cursor.execute("INSERT INTO items(name, type, minutes, item_date) VALUES (?,?,?,?)", (item_name, item_type, duration, sel_date))
                    conn.commit()
                    st.rerun()

    with col2:
        st.subheader(f"📋 Timeline: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins in cursor.fetchall():
            icon = "🧠" if i_type == "Task" else "🏫"
            c1, c2 = st.columns([5, 1])
            c1.info(f"{icon} **{i_name}** ({i_mins}m)")
            if c2.button("🗑️", key=f"del_{i_id}"):
                cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                conn.commit()
                st.rerun()

# ------------------- Synapse AI (Formerly Global AI) -------------------
elif page == "🤖 Synapse AI":
    st.title("🤖 Synapse AI Assistant")
    st.write("Ask your personalized study assistant anything.")
    
    user_q = st.text_input("Message Synapse AI:")
    if st.button("Generate"):
        if not user_q:
            st.warning("Please type a message first.")
        else:
            try:
                hf_token = st.secrets["HF_TOKEN"]
                # Using the stable 2026 router endpoint
                API_URL = "https://router.huggingface.co/v1/chat/completions"
                headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
                payload = {
                    "model": "meta-llama/Llama-3.2-3B-Instruct", 
                    "messages": [{"role": "user", "content": user_q}]
                }
                with st.spinner("Synapse is thinking..."):
                    res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
                    if res.status_code == 200:
                        st.markdown(f"### 🤖 Synapse Response:\n{res.json()['choices'][0]['message']['content']}")
                    else:
                        st.error("Synapse AI is currently overloaded. Please try again.")
            except:
                st.error("Connection Error: Ensure your HF_TOKEN is correctly set in Streamlit Secrets.")

# ------------------- Subject Explorer -------------------
elif page == "📂 Subject Explorer":
    st.title("📂 Subject Explorer")
    if not filtered_subs:
        st.info("No folders found. Create one in the Dashboard!")
    else:
        choice = st.selectbox("Open Folder:", filtered_subs)
        st.header(f"📁 Folder: {choice}")
        
        if st.button("🗑️ Delete Folder"):
            cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
            conn.commit()
            st.session_state.subjects.remove(choice)
            st.rerun()
            
        st.divider()
        cursor.execute("SELECT attendance FROM subjects WHERE name=?", (choice,))
        res = cursor.fetchone()
        att = res[0] if res else 0
        st.metric("Total Attendance", att)
        if st.button("Mark Attendance"):
            cursor.execute("UPDATE subjects SET attendance = attendance + 1 WHERE name=?", (choice,))
            conn.commit()
            st.rerun()
