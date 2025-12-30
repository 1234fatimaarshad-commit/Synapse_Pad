import streamlit as st
import sqlite3
from datetime import datetime, date

st.set_page_config(page_title="Synapse Pad", layout="wide")
if "page" not in st.session_state:
    st.session_state.page = "Main Dashboard"

if "daily_tasks" not in st.session_state:
    st.session_state.daily_tasks = []


# ---------- DATABASE ----------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    name TEXT PRIMARY KEY,
    quiz_avg REAL DEFAULT 0,
    self_quiz REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    subject TEXT,
    date TEXT,
    present INTEGER,
    PRIMARY KEY (subject, date)
)
""")

conn.commit()

# ---------- SESSION STATE ----------
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "subjects" not in st.session_state:
    st.session_state.subjects = {}

# ---------- FUNCTIONS ----------
def add_subject(name):
    if not name:
        return
    if name in st.session_state.subjects:
        return
    if len(st.session_state.subjects) >= 100:
        st.error("Maximum 100 subjects allowed")
        return

    cursor.execute(
        "INSERT OR IGNORE INTO subjects (name) VALUES (?)",
        (name,)
    )
    conn.commit()
    st.session_state.subjects[name] = True

def attendance_allowed():
    return datetime.now().time() < datetime.strptime("00:00", "%H:%M").time()


def efficiency_score(subject):
    cursor.execute(
        "SELECT quiz_avg, self_quiz FROM subjects WHERE name=?",
        (subject,)
    )
    result = cursor.fetchone()

    if result is None:
        quiz_avg, self_quiz = 0, 0
    else:
        quiz_avg, self_quiz = result

    attendance = get_attendance_percentage(subject)

    score = (
        (quiz_avg * 0.4) +
        (attendance * 0.3) +
        (self_quiz * 0.3)
    )

    return round(score, 2)


def update_streak(tasks):
    if len(tasks) == 0:
        return 0

    completed = all(task.get("completed", False) for task in tasks)

    return 1 if completed else -1

def difficulty_to_minutes(level):
    if level == "Easy":
        return 30
    elif level == "Medium":
        return 60
    elif level == "Hard":
        return 90
    return 0


def total_scheduled_minutes(tasks):
    today = date.today()
    return sum(
        difficulty_to_minutes(t["difficulty"])
        for t in tasks
        if t.get("date") == today
    )
def difficulty_minutes(level):
    if level == "Easy":
        return 25
    elif level == "Medium":
        return 45
    elif level == "Hard":
        return 75
    return 0


def total_scheduled_minutes(tasks):
    return sum(task["minutes"] for task in tasks)

# ---------- SIDEBAR ----------
st.sidebar.title("🧠 Synapse Pad")
st.session_state.page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Subject Explorer", "Global AI"]
)
# ================= PAGE ROUTER =================

if st.session_state.page == "Main Dashboard":
    st.title("📊 Synapse Pad Dashboard")

    col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📅 Calendar / To-Do")
    st.info("Tasks will appear here")

with col2:
    pass  # placeholder so Python is happy

with col3:
    st.subheader("📚 Subjects")
    st.info("Subject blocks here")


elif st.session_state.page == "Subject Explorer":
    st.title("📚 Subject Explorer")
    st.info("Click a subject to open its page")


elif st.session_state.page == "Global AI":
    st.title("🌍 Global AI")
    st.info("Global AI assistant will live here")

