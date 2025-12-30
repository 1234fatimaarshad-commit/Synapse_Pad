import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
# ---------------- DATABASE ----------------

conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    name TEXT PRIMARY KEY,
    attendance REAL DEFAULT 0,
    study_time INTEGER DEFAULT 0,
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
# ---------------- HELPER FUNCTIONS ----------------

def add_task(task_name, subject, difficulty):
    st.session_state.daily_tasks.append({
        "task": task_name,
        "subject": subject,
        "difficulty": difficulty,
        "completed": False,
        "date": date.today()
    })
def add_subject(subject_name):
    if subject_name and subject_name not in st.session_state.subjects:
        if len(st.session_state.subjects) >= 100:
            st.error("Maximum 100 subjects allowed")
            return

        cursor.execute(
            "INSERT OR IGNORE INTO subjects (name) VALUES (?)",
            (subject_name,)
        )
        conn.commit()

        st.session_state.subjects[subject_name] = True

# ---------------- PAGE ROUTER ----------------
if st.session_state.page == "Dashboard":
    st.title("📊 Main Dashboard")

    col1, col2, col3 = st.columns(3)

    # ---------------- COLUMN 1: CALENDAR / TO-DO ----------------
    with col1:
        st.subheader("📅 Daily Tasks")

        task_name = st.text_input("Task Name")
        subject = st.text_input("Subject Name")
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])

        if st.button("Add Task"):
            if task_name and subject:
                add_task(task_name, subject, difficulty)
                st.success("Task added")
            else:
                st.warning("Please fill all fields")

        st.markdown("---")

        for i, task in enumerate(st.session_state.daily_tasks):
            if task["date"] == date.today():
                checked = st.checkbox(
                    f"{task['task']} ({task['subject']})",
                    value=task["completed"],
                    key=f"task_{i}"
                )
                st.session_state.daily_tasks[i]["completed"] = checked

    # ---------------- COLUMN 2: STRONG AI ----------------
    with col2:
        st.subheader("⚡ Strong AI")

        st.button("📝 Generate Quiz")
        st.button("🧠 Generate Flashcards")

        st.info("AI logic will be connected in later steps")

    # ---------------- COLUMN 3: SUBJECT BLOCKS ----------------
    with col3:
        st.subheader("📚 Subjects Overview")

        if len(st.session_state.subjects) == 0:
            st.write("No subjects yet")

        for subject in st.session_state.subjects:
            st.markdown(f"""
            **{subject}**
            - Attendance: 0%
            - Study Time: 0 hrs
            """)


elif st.session_state.page == "Subject Explorer":
    st.title("📚 Subject Explorer")

    new_subject = st.text_input("Add New Subject")

    if st.button("Create Subject"):
        add_subject(new_subject)
        st.success("Subject created")
def attendance_allowed():
    current_time = datetime.now().time()
    lock_time = datetime.strptime("00:00", "%H:%M").time()
    return current_time < lock_time

    st.markdown("---")

    for subject in st.session_state.subjects:
        st.subheader(subject)

        today = date.today().isoformat()

        cursor.execute(
            "SELECT present FROM attendance WHERE subject=? AND date=?",
            (subject, today)
        )
        record = cursor.fetchone()

        if record is None:
            if attendance_allowed():
                if st.button(f"Mark Present ({subject})"):
                    cursor.execute(
                        "INSERT INTO attendance VALUES (?, ?, ?)",
                        (subject, today, 1)
                    )
                    conn.commit()
                    st.success("Attendance marked")
            else:
                st.warning("Attendance locked after 12:00 AM")
        else:
            st.info("Attendance already marked for today")

elif st.session_state.page == "Global AI":
    st.title("🤖 Global AI")
    st.write("Quiz • Flashcards • Study Help")
