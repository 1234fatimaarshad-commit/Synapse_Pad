import streamlit as st
import sqlite3
import requests
from datetime import datetime, date

# ------------------- Page Config -------------------
st.set_page_config(page_title="Synapse Pad", layout="wide")

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    name TEXT PRIMARY KEY,
    quiz_avg REAL DEFAULT 0,
    self_quiz REAL DEFAULT 0,
    attendance INTEGER DEFAULT 0
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    difficulty TEXT,
    minutes INTEGER,
    task_date TEXT,
    completed INTEGER DEFAULT 0
)
""")
conn.commit()

# ------------------- Session State -------------------
if "page" not in st.session_state:
    st.session_state.page = "Main Dashboard"

if "subjects" not in st.session_state:
    st.session_state.subjects = []
    try:
        cursor.execute("SELECT name FROM subjects")
        rows = cursor.fetchall()
        st.session_state.subjects = [row[0] for row in rows]
    except:
        st.session_state.subjects = []

# ------------------- Helper Functions -------------------
def difficulty_minutes(level):
    return {"Easy":25,"Medium":45,"Hard":75}.get(level,0)

def get_attendance_percentage(subject):
    try:
        cursor.execute("SELECT attendance FROM subjects WHERE name=?",(subject,))
        res = cursor.fetchone()
        return res[0] if res else 0
    except:
        return 0

def efficiency_score(subject):
    try:
        cursor.execute("SELECT quiz_avg,self_quiz FROM subjects WHERE name=?",(subject,))
        res = cursor.fetchone()
        quiz_avg,self_quiz = res if res else (0,0)
        attendance = get_attendance_percentage(subject)
        score = (quiz_avg*0.4)+(attendance*0.3)+(self_quiz*0.3)
        return round(score,2)
    except:
        return 0

def add_subject(name):
    if not name.strip():
        return
    try:
        cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)",(name,))
        conn.commit()
        if name not in st.session_state.subjects:
            st.session_state.subjects.append(name)
            st.rerun()
    except:
        st.error("Failed to add subject.")

def add_task(name, difficulty, task_date):
    if not name.strip(): return
    minutes = difficulty_minutes(difficulty)
    
    # AI Logic: Check 8-hour limit
    tasks = get_tasks_for_date(task_date)
    current_mins = sum(t['minutes'] for t in tasks)
    if (current_mins + minutes) > 480:
        st.error("⚠️ Overbooked! AI suggests rescheduling (Limit 8 hours).")
        return

    cursor.execute("INSERT INTO tasks(name,difficulty,minutes,task_date) VALUES (?,?,?,?)",(name,difficulty,minutes,task_date))
    conn.commit()
    st.success("Task added!")

def get_tasks_for_date(task_date):
    cursor.execute("SELECT id,name,difficulty,minutes,completed FROM tasks WHERE task_date=?",(task_date,))
    rows = cursor.fetchall()
    return [{"id":r[0],"name":r[1],"difficulty":r[2],"minutes":r[3],"completed":bool(r[4])} for r in rows]

def toggle_task_completion(task_id,completed):
    cursor.execute("UPDATE tasks SET completed=? WHERE id=?",(int(completed),task_id))
    conn.commit()

# ------------------- Sidebar -------------------
with st.sidebar:
    st.title("Synapse Pad")
    st.session_state.page = st.radio("Navigate", ["Main Dashboard","Subject Explorer","Global AI"])

# ------------------- Page Router -------------------

if st.session_state.page == "Main Dashboard":
    st.title("📊 Synapse Pad Dashboard")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📅 Tasks")
        sel_date = st.date_input("Select Date", date.today())
        tasks = get_tasks_for_date(sel_date.strftime("%Y-%m-%d"))
        for t in tasks:
            if st.checkbox(f"{t['name']} ({t['minutes']}m)", value=t['completed'], key=f"t_{t['id']}"):
                toggle_task_completion(t['id'], True)

    with col2:
        st.subheader("🧠 AI Timer")
        t_name = st.text_input("Task Name")
        t_diff = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        if st.button("Add Task"):
            add_task(t_name, t_diff, sel_date.strftime("%Y-%m-%d"))
77777777
    with col3:
        st.subheader("📚 Subjects")
        new_sub = st.text_input("New Subject")
        if st.button("Create"):
            if len(st.session_state.subjects) < 100: add_subject(new_sub)

elif st.session_state.page == "Subject Explorer":
    st.title("📂 Subject Folders")
    if not st.session_state.subjects:
        st.info("Add a subject first!")
    else:
        # FOLDER LOGIC
        choice = st.selectbox("Open Folder:", st.session_state.subjects)
        st.header(f"Subject: {choice}")
        
        # Attendance + 12AM Lock
        st.write(f"Attendance: {get_attendance_percentage(choice)}%")
        hour = datetime.now().hour
        if hour == 0:
            st.warning("Locked at 12 AM")
            st.button("Mark Attendance", disabled=True)
        else:
            if st.button("Mark Attendance"):
                cursor.execute("UPDATE subjects SET attendance = attendance + 1 WHERE name=?",(choice,))
                conn.commit()
                st.rerun()

        st.file_uploader("Upload to Cloud Folder")
        st.write(f"Efficiency Score: {efficiency_score(choice)}")

elif st.session_state.page == "Global AI":
    st.title("🌍 Global AI Assistant")
    hf_token = "PASTE_YOUR_TOKEN_HERE"
    user_q = st.text_input("Ask AI:")
    if st.button("Generate"):
        if hf_token = st.secrets["HF_TOKEN"]:
            # Real AI API Call
            API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
            headers = {"Authorization": f"Bearer {hf_token}"}
            res = requests.post(API_URL, headers=headers, json={"inputs": user_q})
            st.write(res.json()[0]['generated_text'])
        else:
            st.error("Paste your token in the code first!")
