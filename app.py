import streamlit as st
import sqlite3
from datetime import datetime, date

st.set_page_config(page_title="Synapse Pad", layout="wide")

# ---------- DATABASE ----------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    name TEXT PRIMARY KEY
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
            st.info("Attendance already marked")

elif st.session_state.page == "Global AI":
    st.title("🤖 Global AI")
    st.write("AI tools coming soon")
