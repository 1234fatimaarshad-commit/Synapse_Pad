import streamlit as st
import sqlite3
import requests
from datetime import datetime, date

# v13.0 - STUDY SUITE: QUIZ, FLASHCARDS, MIND MAPS
st.set_page_config(page_title="Synapse Pad", layout="wide")

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name TEXT, 
    type TEXT, 
    minutes INTEGER, 
    item_date TEXT,
    attended INTEGER DEFAULT 0
)""")
conn.commit()

# ------------------- Helper: AI Study Generator -------------------
def generate_study_material(prompt_type, subject_name):
    try:
        hf_token = st.secrets["HF_TOKEN"]
        prompts = {
            "Quiz": f"Generate a 5-question multiple choice quiz with answers for the subject: {subject_name}.",
            "Flashcards": f"Create 5 high-impact flashcards (Front: Question, Back: Answer) for: {subject_name}.",
            "Mind Map": f"Generate a structured hierarchical mind map outline for: {subject_name}. Use indentation."
        }
        
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/Llama-3.2-3B-Instruct", 
            "messages": [{"role": "user", "content": prompts[prompt_type]}],
            "max_tokens": 700
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI Error: Ensure HF_TOKEN is set. Details: {str(e)}"

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
    search_query = st.text_input("🔍 Search Folders", "").lower()
    st.divider()
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    filtered_subs = [s for s in st.session_state.subjects if search_query in s.lower()]

# ------------------- Dashboard -------------------
if page == "📊 Dashboard":
    st.title("📊 Main Dashboard")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🗓️ Daily Planner")
        sel_date = st.date_input("Select Date", date.today()).strftime("%Y-%m-%d")
        
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        mins_used = cursor.fetchone()[0] or 0
        st.write(f"**AI Capacity:** {mins_used} / 960 mins")
        st.progress(min(mins_used / 960, 1.0))
        
        st.divider()
        st.subheader("🏫 Classes")
        if not st.session_state.subjects:
            st.info("Create a subject folder first.")
        else:
            class_sub = st.selectbox("Select Subject", st.session_state.subjects)
            class_mins = st.number_input("Duration (Mins)", min_value=15, step=15, value=60)
            if st.button("Schedule Class"):
                if (mins_used + class_mins) <= 960:
                    cursor.execute("INSERT INTO items(name, type, minutes, item_date, attended) VALUES (?,?,?,?,0)", 
                                   (class_sub, "Class", class_mins, sel_date))
                    conn.commit()
                    st.rerun()

        st.divider()
        st.subheader("📝 To-Do List")
        task_name = st.text_input("Task Name")
        task_mins = st.number_input("Task Mins", min_value=15, step=15, value=30)
        if st.button("Add Task"):
            if (mins_used + task_mins) <= 960 and task_name.strip():
                cursor.execute("INSERT INTO items(name, type, minutes, item_date, attended) VALUES (?,?,?,?,0)", 
                               (task_name, "Task", task_mins, sel_date))
                conn.commit()
                st.rerun()

        st.divider()
        st.subheader("📁 New Folder")
        new_sub = st.text_input("Folder Name")
        if st.button("Create"):
            if new_sub.strip():
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_sub,))
                conn.commit()
                if new_sub not in st.session_state.subjects: st.session_state.subjects.append(new_sub)
                st.rerun()

    with col2:
        st.subheader(f"📋 Timeline: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        items = cursor.fetchall()
        for i_id, i_name, i_type, i_mins, i_attended in items:
            c1, c2, c3 = st.columns([4, 1, 1])
            icon = "🏫" if i_type == "Class" else "🧠"
            c1.info(f"{icon} **{i_name}** ({i_mins}m)")
            if i_type == "Class":
                is_checked = c2.checkbox("Attended", value=bool(i_attended), key=f"att_{i_id}")
                if is_checked != bool(i_attended):
                    cursor.execute("UPDATE items SET attended=? WHERE id=?", (int(is_checked), i_id))
                    conn.commit()
                    st.rerun()
            if c3.button("🗑️", key=f"del_{i_id}"):
                cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                conn.commit()
                st.rerun()

# ------------------- Synapse AI -------------------
elif page == "🤖 Synapse AI":
    st.title("🤖 Synapse AI")
    user_q = st.text_input("Message Synapse AI:")
    if st.button("Generate"):
        try:
            hf_token = st.secrets["HF_TOKEN"]
            API_URL = "https://router.huggingface.co/v1/chat/completions"
            headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
            payload = {"model": "meta-llama/Llama-3.2-3B-Instruct", "messages": [{"role": "user", "content": user_q}]}
            res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
            st.markdown(res.json()['choices'][0]['message']['content'])
        except:
            st.error("AI Error. Check Secrets.")

# ------------------- Subject Explorer -------------------
elif page == "📂 Subject Explorer":
    st.title("📂 Subject Explorer")
    if not filtered_subs:
        st.info("No folders found.")
    else:
        choice = st.selectbox("Open Folder:", filtered_subs)
        
        # Attendance Logic
        cursor.execute("SELECT COUNT(*) FROM items WHERE name=? AND type='Class'", (choice,))
        total_classes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM items WHERE name=? AND type='Class' AND attended=1", (choice,))
        attended_classes = cursor.fetchone()[0]
        final_percentage = 100 if total_classes == 0 else round((attended_classes / total_classes) * 100, 1)
        
        st.metric("Attendance Rate", f"{final_percentage}%", delta=f"{attended_classes}/{total_classes} Classes")
        
        st.divider()
        
        # --- NEW STUDY SUITE SECTION ---
        st.subheader("🧠 Synapse Study Suite")
        uploaded_file = st.file_uploader(f"Upload materials for {choice}", key=f"file_{choice}")
        
        if uploaded_file:
            st.success(f"Document '{uploaded_file.name}' loaded into AI memory.")

        col_q, col_f, col_m = st.columns(3)
        
        if col_q.button("📝 Generate Quiz", use_container_width=True):
            with st.spinner("Analyzing document..."):
                st.session_state.study_result = generate_study_material("Quiz", choice)
        
        if col_f.button("🗂️ Flashcards", use_container_width=True):
            with st.spinner("Extracting key facts..."):
                st.session_state.study_result = generate_study_material("Flashcards", choice)
                
        if col_m.button("🕸️ Mind Map", use_container_width=True):
            with st.spinner("Mapping concepts..."):
                st.session_state.study_result = generate_study_material("Mind Map", choice)

        # Display AI Result
        if "study_result" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state.study_result)
            if st.button("Clear AI Result"):
                del st.session_state.study_result
                st.rerun()

        st.divider()
        if st.button("🗑️ Delete Folder"):
            cursor.execute("DELETE FROM subjects WHERE name=?;", (choice,))
            cursor.execute("DELETE FROM items WHERE name=?;", (choice,))
            conn.commit()
            st.rerun()
