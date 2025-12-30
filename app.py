import streamlit as st
import sqlite3
from datetime import datetime, date

st.set_page_config(page_title="Synapse Pad", layout="wide")

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


# ---------- SIDEBAR ----------
st.sidebar.title("🧠 Synapse Pad")
st.session_state.page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Subject Explorer", "Global AI"]
)

# ---------- PAGE ROUTER ----------
if st.session_state.page == "Dashboard":
    st.title("📊 Main Dashboard")
    st.write("Dashboard will be expanded next")

elif st.session_state.page == "Subject Explorer":
    st.title("📚 Subject Explorer")

    subject_name = st.text_input("New Subject")

    if st.button("Create Subject"):
        add_subject(subject_name)
        st.success("Subject created")

    st.markdown("---")

    for subject in st.session_state.subjects:
        st.subheader(subject)
attendance_percent = get_attendance_percentage(subject)
st.progress(attendance_percent / 100)
st.write(f"Attendance: {attendance_percent}%")
score = efficiency_score(subject)
st.metric("Efficiency Score", score)

        today = date.today().isoformat()
        cursor.execute(
            "SELECT present FROM attendance WHERE subject=? AND date=?",
            (subject, today)
        )
        record = cursor.fetchone()

        if record is None:
            if attendance_allowed():
                def get_attendance_percentage(subject):
    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE subject=?",
        (subject,)
    )
    total = cursor.fetchone()[0]

    if total == 0:
        return 0

    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE subject=? AND present=1",
        (subject,)
    )
    present = cursor.fetchone()[0]

    return round((present / total) * 100, 2)

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
            st.info("Attendance already marked")

elif st.session_state.page == "Global AI":
    st.title("🤖 Global AI")
    st.write("AI tools coming soon")
