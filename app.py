import streamlit as st
import sqlite3
import requests
from datetime import datetime, date

# ------------------- Page Config -------------------
st.set_page_config(page_title="Synapse Pad", layout="wide")

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()

# Updated Subjects Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    name TEXT PRIMARY KEY,
    attendance INTEGER DEFAULT 0
)
""")

# Updated Tasks & Lectures Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT, -- 'Task' or 'Lecture'
    minutes INTEGER,
    item_date TEXT
)
""")
conn.commit()

# ------------------- Session State -------------------
if "subjects" not in st.session_state:
    st.session_state.subjects = []
    try:
        cursor.execute("SELECT name FROM subjects")
        st.session_state.subjects = [row[0] for row in cursor.fetchall()]
    except:
        st.session_state.subjects = []

# ------------------- AI Scheduling Logic -------------------
def get_total_minutes(sel_date):
    cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
    res = cursor.fetchone()
    return res[0] if res[0] else 0

def add_schedule_item(name, minutes, sel_date, item_type):
    if not name.strip(): return
    
    current_total = get_total_minutes(sel_date)
    limit = 480 # 8 Hours
    
    if (current_total + minutes) > limit:
        st.error(f"⚠️ AI Alert: Adding this {item_type} reaches {current_total + minutes} mins. (Max 480). Reschedule needed!")
        return False
    
    cursor.execute("INSERT INTO items(name, type, minutes, item_date) VALUES (?,?,?,?)",
                   (name, item_type, minutes, sel_date))
    conn.commit()
    st.success(f"{item_type} Added!")
    return True

# ------------------- Page Functions -------------------

def dashboard_page():
    st.title("🗓️ Intelligent Scheduler")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📅 Plan Your Day")
        sel_date = st.date_input("Select Date", date.today()).strftime("%Y-%m-%d")
        
        # Calculate Progress
        mins_used = get_total_minutes(sel_date)
        progress = min(mins_used / 480, 1.0)
        st.progress(progress)
        st.write(f"**AI Capacity Used:** {mins_used}/480 minutes")
        
        st.divider()
        
        # Inputs
        item_name = st.text_input("Lecture or Task Name")
        duration = st.number_input("Duration (Minutes)", min_value=15, step=15, value=60)
        item_type = st.selectbox("Type", ["Lecture", "Task"])
        
        if st.button("Add to Schedule"):
            if add_schedule_item(item_name, duration, sel_date, item_type):
                st.rerun()

    with col2:
        st.subheader(f"📋 Timeline for {sel_date}")
        cursor.execute("SELECT name, type, minutes FROM items WHERE item_date=?", (sel_date,))
        daily_items = cursor.fetchall()
        
        if not daily_items:
            st.info("No items scheduled for this day.")
        else:
            for name, itype, mins in daily_items:
                icon = "🏫" if itype == "Lecture" else "🧠"
                st.info(f"**{icon} {name}** | {mins} mins")

def subject_folder_page(choice):
    st.title(f"📁 Folder: {choice}")
    if st.button("🗑️ Delete Folder"):
        cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
        conn.commit()
        st.session_state.subjects.remove(choice)
        st.rerun()

    st.divider()
    # Attendance Logic
    st.subheader("📊 Attendance")
    cursor.execute("SELECT attendance FROM subjects WHERE name=?", (choice,))
    att = cursor.fetchone()[0]
    st.metric("Total Attended", att)
    
    if datetime.now().hour != 0:
        if st.button("Mark Lecture Attended"):
            cursor.execute("UPDATE subjects SET attendance = attendance + 1 WHERE name=?",(choice,))
            conn.commit()
            st.rerun()
    else:
        st.warning("Locked at Midnight")

def global_ai_page():
    st.title("🌍 Global AI Assistant")
    try:
        hf_token = st.secrets["HF_TOKEN"]
        user_q = st.text_input("Ask Synapse AI:")
        if st.button("Generate"):
            with st.spinner("AI Thinking..."):
                API_URL = "https://router.huggingface.co/v1/chat/completions"
                headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
                payload = {"model": "meta-llama/Llama-3.2-3B-Instruct", "messages": [{"role": "user", "content": user_q}]}
                response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
                st.markdown(f"### 🤖 Response:\n{response.json()['choices'][0]['message']['content']}")
    except:
        st.error("Check HF_TOKEN in Secrets!")

# ------------------- Navigation -------------------
with st.sidebar:
    st.header("🔍 Search Folders")
    search = st.text_input("Filter...", "").lower()

filtered_subs = [s for s in st.session_state.subjects if search in s.lower()]

pg_dash = st.Page(dashboard_page, title="Smart Scheduler", icon="🗓️")
pg_ai = st.Page(global_ai_page, title="Global AI", icon="🌍")

subject_pages = [st.Page(lambda s=sub: subject_folder_page(s), title=sub, icon="📁") for sub in filtered_subs]

nav_dict = {"Main Menu": [pg_dash, pg_ai], "Folders": subject_pages}
st.navigation(nav_dict).run()
