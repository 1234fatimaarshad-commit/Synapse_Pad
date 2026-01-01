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
    if not name.strip(): return
    try:
        cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)",(name,))
        conn.commit()
        if name not in st.session_state.subjects:
            st.session_state.subjects.append(name)
            st.rerun()
    except:
        st.error("Failed to add subject.")

def delete_subject(name):
    try:
        cursor.execute("DELETE FROM subjects WHERE name=?", (name,))
        conn.commit()
        if name in st.session_state.subjects:
            st.session_state.subjects.remove(name)
        st.success(f"Deleted {name}")
        st.rerun()
    except:
        st.error("Delete failed.")

def add_task(name, difficulty, task_date):
    if not name.strip(): return
    minutes = difficulty_minutes(difficulty)
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

# ------------------- Page Functions -------------------

def dashboard_page():
    st.title("📊 Main Dashboard")
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

    with col3:
        st.subheader("📚 Create Folder")
        new_sub = st.text_input("Folder Name (Subject)")
        if st.button("Create"):
            if len(st.session_state.subjects) < 100: 
                add_subject(new_sub)

def subject_folder_page(choice):
    st.title(f"📁 Folder: {choice}")
    
    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("🗑️ Delete Folder", use_container_width=True):
            delete_subject(choice)

    st.divider()
    
    # Efficiency Metric
    score = efficiency_score(choice)
    st.metric("Subject Efficiency Score", f"{score}%", delta=f"{score-50}%" if score > 50 else f"{score-50}%")
    
    st.subheader("📊 Attendance Record")
    st.write(f"Attendance Rate: {get_attendance_percentage(choice)}%")
    if datetime.now().hour == 0:
        st.warning("Locked at 12 AM")
    else:
        if st.button("Mark Attendance"):
            cursor.execute("UPDATE subjects SET attendance = attendance + 1 WHERE name=?",(choice,))
            conn.commit()
            st.rerun()

    st.divider()
    st.subheader("📂 Files & Notes")
    st.file_uploader("Upload materials to this cloud folder")

def global_ai_page():
    st.title("🌍 Global AI Assistant")
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except:
        hf_token = "NOT_FOUND"
    
    user_q = st.text_input("Ask Synapse AI anything:")

    if st.button("Generate"):
        if hf_token == "NOT_FOUND":
            st.error("Missing Token in Secrets!")
        elif not user_q.strip():
            st.warning("Enter a question.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    API_URL = "https://router.huggingface.co/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
                    payload = {
                        "model": "meta-llama/Llama-3.2-3B-Instruct", 
                        "messages": [{"role": "user", "content": user_q}],
                        "max_tokens": 500
                    }
                    response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
                    if response.status_code == 200:
                        st.markdown("### 🤖 Response:")
                        st.write(response.json()['choices'][0]['message']['content'])
                    else:
                        st.error(f"AI Offline ({response.status_code})")
                except:
                    st.error("Connection failed.")

# ------------------- Navigation Tree -------------------

# Search Bar in Sidebar
with st.sidebar:
    st.header("🔍 Search Folders")
    search_query = st.text_input("Filter subjects...", "").lower()

# Filter subjects based on search
filtered_subs = [s for s in st.session_state.subjects if search_query in s.lower()]

# Main Pages
pg_dashboard = st.Page(dashboard_page, title="Main Dashboard", icon="📊", default=True)
pg_ai = st.Page(global_ai_page, title="Global AI Assistant", icon="🌍")

# Folder Sub-branches
subject_pages = []
for sub in filtered_subs:
    subject_pages.append(st.Page(lambda s=sub: subject_folder_page(s), title=sub, icon="📁"))

# Build Navigation
nav_dict = {"Main Menu": [pg_dashboard, pg_ai]}
if subject_pages:
    nav_dict["Subject Explorer"] = subject_pages
else:
    nav_dict["Subject Explorer"] = [st.Page(lambda: st.info("No folders found."), title="Empty", icon="❓")]

pg = st.navigation(nav_dict)
pg.run()
