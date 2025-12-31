import requests
import streamlit as st
import sqlite3
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
        for row in rows:
            if row[0]:
                st.session_state.subjects.append(row[0])
    except:
        st.session_state.subjects = []

# ------------------- Helper Functions -------------------
def difficulty_minutes(level):
    return {"Easy":25,"Medium":45,"Hard":75}.get(level,0)

def total_scheduled_minutes(tasks):
    return sum(task["minutes"] for task in tasks)

def attendance_allowed():
    return True  # Always allow marking for demo

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

def update_streak(tasks):
    if len(tasks)==0:
        return 0
    completed_all = all(task.get("completed",False) for task in tasks)
    return 1 if completed_all else -1

def add_subject(name):
    if not name.strip():
        return
    try:
        cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)",(name,))
        conn.commit()
        if name not in st.session_state.subjects:
            st.session_state.subjects.append(name)
    except:
        st.error("Failed to add subject.")

def add_task(name, difficulty, task_date):
    if not name.strip():
        return
    
    minutes = difficulty_minutes(difficulty)
    
    # AI Logic: Check total time for that day
    tasks_that_day = get_tasks_for_date(task_date)
    current_total = sum(t['minutes'] for t in tasks_that_day)
    
    if (current_total + minutes) > 480: # 480 mins = 8 hours
        st.error(f"⚠️ Overbooked! Adding this would exceed 8 hours. AI recommends rescheduling.")
        return False
    
    try:
        cursor.execute(
            "INSERT INTO tasks(name,difficulty,minutes,task_date) VALUES (?,?,?,?)",
            (name, difficulty, minutes, task_date)
        )
        conn.commit()
        return True
    except:
        st.error("Failed to add task.")
        return False

def get_tasks_for_date(task_date):
    try:
        cursor.execute("SELECT id,name,difficulty,minutes,completed FROM tasks WHERE task_date=?",(task_date,))
        rows = cursor.fetchall()
        tasks=[]
        for row in rows:
            tasks.append({
                "id":row[0],
                "name":row[1],
                "difficulty":row[2],
                "minutes":row[3],
                "completed":bool(row[4])
            })
        return tasks
    except:
        return []

def toggle_task_completion(task_id,completed):
    try:
        cursor.execute("UPDATE tasks SET completed=? WHERE id=?",(int(completed),task_id))
        conn.commit()
    except:
        st.error("Failed to update task.")

def generate_quiz_or_flashcard(subject):
    return f"Generated a quiz/flashcard for {subject}!"

def add_subject(name):
    if not name.strip():
        return
    try:
        cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (name,))
        conn.commit()
        if name not in st.session_state.subjects:
            st.session_state.subjects.append(name)
            st.rerun() 
    except Exception as e:
        st.error(f"Failed to add subject: {e}")

# ------------------- Sidebar -------------------
with st.sidebar:
    st.title("Synapse Pad")
    pages = ["Main Dashboard","Subject Explorer","Global AI"]
    st.session_state.page = st.radio("Navigate",pages)

# ------------------- Page Router -------------------
if st.session_state.page == "Main Dashboard":
    st.title("📊 Synapse Pad Dashboard")

    col1, col2, col3 = st.columns(3)

    # -------- Column 1: Tasks --------
    with col1:
        st.subheader("📅 Tasks / Calendar")
        selected_date = st.date_input("Select Date", date.today())
        date_str = selected_date.strftime("%Y-%m-%d")
        tasks = get_tasks_for_date(date_str)

        if not tasks:
            st.info("No tasks for this date.")
        else:
            for task in tasks:
                completed = st.checkbox(
                    f"{task['name']} ({task['difficulty']}, {task['minutes']} mins)",
                    value=task["completed"],
                    key=f"task_{task['id']}"
                )
                if completed != task["completed"]:
                    toggle_task_completion(task["id"], completed)

        streak_change = update_streak(tasks)
        st.metric("Today's Streak Change", streak_change)

    # -------- Column 2: Add Task --------
    with col2:
        st.subheader("🧠 AI Study Timer")
        task_name = st.text_input("Task Name")
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        task_date_input = st.date_input("Task Date", date.today())
        task_date_str = task_date_input.strftime("%Y-%m-%d")

        if st.button("Add Task"):
            add_task(task_name, difficulty, task_date_str)
            st.success(f"Task '{task_name}' added for {task_date_str}")

    # -------- Column 3: Subjects --------
    with col3:
        st.subheader("📚 Subjects")
        # Use a unique key for the text input
        new_subject_name = st.text_input("Enter Subject Name", key="subject_input_field")

        if st.button("Add Subject"):
            if len(st.session_state.subjects) < 100:
                add_subject(new_subject_name) # This CALLS the function at the top
            else:
                st.error("Limit of 100 subjects reached.")

        # Display the list
        st.write("---")
        for subj in st.session_state.subjects:
            att = get_attendance_percentage(subj)
            eff = efficiency_score(subj)
            st.info(f"**{subj}**\nAtt: {att}% | Eff: {eff}")

# Check if it's currently midnight (or past a certain cut-off)
current_hour = datetime.now().hour

if current_hour == 0: # 0 is 12 AM (Midnight)
    st.warning("🕒 Attendance is locked between 12:00 AM and 1:00 AM for processing.")
    attendance_disabled = True
else:
    attendance_disabled = False

if st.button(f"Mark Class Attended: {subj}", disabled=attendance_disabled):
    # Logic to +1 attendance in SQLite
    cursor.execute("UPDATE subjects SET attendance = attendance + 1 WHERE name=?", (subj,))
    conn.commit()
    st.success("Attendance Updated!")


elif st.session_state.page == "Global AI":
    st.title("🌍 Global AI Assistant")
    
    # Replace the text below with your actual token from Hugging Face
    HF_TOKEN = "paste_your_token_here" 
    
    user_input = st.text_input("Ask Synapse AI anything (e.g., 'Make a quiz for Biology'):")

    if st.button("Generate Response"):
        if HF_TOKEN == "paste_your_token_here":
            st.error("Please provide your Hugging Face Token first!")
        else:
            with st.spinner("AI is thinking..."):
                # This is the "Bridge" to the AI brain
                API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
                headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                
                response = requests.post(API_URL, headers=headers, json={"inputs": user_input})
                
                try:
                    # Show the AI's answer
                    result = response.json()
                    st.write(result[0]['generated_text'])
                except:
                    st.error("AI is busy or Token is wrong. Try again in a minute!")
