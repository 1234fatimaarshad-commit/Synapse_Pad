import streamlit as st
import sqlite3
from datetime import datetime, date, timedelta

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
    attendance INTEGER DEFAULT 0,
    total_study_time INTEGER DEFAULT 0
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

# ------------------- Session State Init -------------------
if "page" not in st.session_state:
    st.session_state.page = "Main Dashboard"

if "subjects" not in st.session_state:
    st.session_state.subjects = []
    cursor.execute("SELECT name FROM subjects")
    for row in cursor.fetchall():
        st.session_state.subjects.append(row[0])

if "daily_tasks" not in st.session_state:
    st.session_state.daily_tasks = []

# ------------------- Helper Functions -------------------
def difficulty_minutes(level):
    return {"Easy": 25, "Medium": 45, "Hard": 75}.get(level, 0)

def total_scheduled_minutes(tasks):
    return sum(task["minutes"] for task in tasks)

def attendance_allowed():
    return datetime.now().time() < datetime.strptime("00:00","%H:%M").time()

def get_attendance_percentage(subject):
    cursor.execute("SELECT attendance FROM subjects WHERE name=?", (subject,))
    res = cursor.fetchone()
    return res[0] if res else 0

def efficiency_score(subject):
    cursor.execute("SELECT quiz_avg, self_quiz FROM subjects WHERE name=?", (subject,))
    res = cursor.fetchone()
    quiz_avg, self_quiz = res if res else (0,0)
    attendance = get_attendance_percentage(subject)
    score = (quiz_avg*0.4) + (attendance*0.3) + (self_quiz*0.3)
    return round(score,2)

def update_streak(tasks):
    if len(tasks)==0:
        return 0
    completed_all = all(task.get("completed", False) for task in tasks)
    return 1 if completed_all else -1

def add_subject(name):
    cursor.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (name,))
    conn.commit()
    if name not in st.session_state.subjects:
        st.session_state.subjects.append(name)

def add_task(name, difficulty, task_date):
    minutes = difficulty_minutes(difficulty)
    cursor.execute("INSERT INTO tasks (name, difficulty, minutes, task_date) VALUES (?,?,?,?)",
                   (name,difficulty,minutes,task_date))
    conn.commit()

def get_tasks_for_date(selected_date):
    cursor.execute("SELECT id,name,difficulty,minutes,completed FROM tasks WHERE task_date=?", (selected_date,))
    rows = cursor.fetchall()
    tasks=[]
    for row in rows:
        tasks.append({"id":row[0], "name":row[1], "difficulty":row[2], "minutes":row[3], "completed": bool(row[4])})
    return tasks

def toggle_task_completion(task_id, completed):
    cursor.execute("UPDATE tasks SET completed=? WHERE id=
