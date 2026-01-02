import streamlit as st
import sqlite3
import requests
from datetime import datetime, date

# v12.0 - MEDIA UPLOAD + ATTENDANCE LOGIC
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
                else:
                    st.error("Capacity Exceeded!")

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
            st.error("Check Secrets!")

# ------------------- Subject Explorer -------------------
elif page == "📂 Subject Explorer":
    st.title("📂 Subject Explorer")
    if not filtered_subs:
        st.info("No folders found.")
    else:
        choice = st.selectbox("Open Folder:", filtered_subs)
        
        # --- TOP SECTION: ATTENDANCE MATH ---
        cursor.execute("SELECT COUNT(*) FROM items WHERE name=? AND type='Class'", (choice,))
        total_classes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM items WHERE name=? AND type='Class' AND attended=1", (choice,))
        attended_classes = cursor.fetchone()[0]
        
        final_percentage = 100 if total_classes == 0 else round((attended_classes / total_classes) * 100, 1)
        
        col_metrics, col_btn = st.columns([3, 1])
        with col_metrics:
            st.metric("Attendance Rate", f"{final_percentage}%", delta=f"{attended_classes}/{total_classes} Classes")
        with col_btn:
            if st.button("🗑️ Delete Folder", use_container_width=True):
                cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
                cursor.execute("DELETE FROM items WHERE name=?", (choice,))
                conn.commit()
                st.session_state.subjects.remove(choice)
                st.rerun()
        
        st.divider()
        
        # --- MEDIA OPTION (BACK AGAIN!) ---
        st.subheader(f"📁 {choice} Media & Notes")
        st.file_uploader("Upload Study Materials (PDF, PNG, etc.)", key=f"file_{choice}")
        
        st.info("Uploaded files will appear here for review during your presentation.")
