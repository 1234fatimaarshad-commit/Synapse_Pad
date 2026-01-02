import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time

# v15.0 - REAL-TIME FOCUS TIMER + COMPLETE STUDY ENGINE
st.set_page_config(page_title="Synapse Pad Pro", layout="wide")

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name TEXT, type TEXT, minutes INTEGER, 
    item_date TEXT, attended INTEGER DEFAULT 0
)""")
conn.commit()

# ------------------- Advanced AI Engine -------------------
def ask_synapse(prompt):
    try:
        hf_token = st.secrets["HF_TOKEN"]
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/Llama-3.2-3B-Instruct", 
            "messages": [{"role": "system", "content": "You are Synapse, an academic AI. Be concise."},
                         {"role": "user", "content": prompt}],
            "max_tokens": 800
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        return res.json()['choices'][0]['message']['content']
    except:
        return "⚠️ Synapse AI is offline. Check HF_TOKEN."

# ------------------- Sidebar -------------------
with st.sidebar:
    st.title("🚀 Synapse Pad Pro")
    search_query = st.text_input("🔍 Search Folders", "").lower()
    st.divider()
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    
    cursor.execute("SELECT name FROM subjects")
    st.session_state.subjects = [row[0] for row in cursor.fetchall()]
    filtered_subs = [s for s in st.session_state.subjects if search_query in s.lower()]

# ------------------- Dashboard -------------------
if page == "📊 Dashboard":
    st.title("📊 Control Center")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📅 Schedule")
        sel_date = st.date_input("Date", date.today()).strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        mins_used = cursor.fetchone()[0] or 0
        st.write(f"**Capacity:** {mins_used}/960 mins")
        st.progress(min(mins_used / 960, 1.0))

        with st.expander("🏫 Add Class"):
            c_sub = st.selectbox("Subject", st.session_state.subjects)
            c_min = st.number_input("Mins", 15, 300, 60)
            if st.button("Schedule Class"):
                cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                conn.commit() ; st.rerun()

        with st.expander("📝 Add Task"):
            t_name = st.text_input("Task Name")
            t_min = st.number_input("Mins", 15, 300, 30)
            if st.button("Add Task"):
                cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",t_min,sel_date))
                conn.commit() ; st.rerun()

        st.divider()
        new_s = st.text_input("New Subject Folder")
        if st.button("Create Folder"):
            cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
            conn.commit() ; st.rerun()

    with col2:
        st.subheader(f"📋 Timeline: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins, i_att in cursor.fetchall():
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.info(f"{'🏫' if i_type=='Class' else '🧠'} **{i_name}** ({i_mins}m)")
            if i_type == "Class":
                if c2.checkbox("Done", value=bool(i_att), key=f"at_{i_id}"):
                    cursor.execute("UPDATE items SET attended=1 WHERE id=?", (i_id,))
                else:
                    cursor.execute("UPDATE items SET attended=0 WHERE id=?", (i_id,))
                conn.commit()
            if c3.button("🗑️", key=f"d_{i_id}"):
                cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                conn.commit() ; st.rerun()

# ------------------- Synapse AI -------------------
elif page == "🤖 Synapse AI":
    st.title("🤖 Synapse Global Assistant")
    u_q = st.chat_input("How can Synapse help you today?")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"): st.write(ask_synapse(u_q))

# ------------------- Subject Explorer -------------------
elif page == "📂 Subject Explorer":
    if not filtered_subs: st.info("Create a folder first.")
    else:
        choice = st.selectbox("Select Workspace:", filtered_subs)
        
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, att = cursor.fetchone()
        att = att or 0
        score = 100 if total == 0 else round((att/total)*100, 1)
        
        st.title(f"📂 {choice} Workspace")
        st.metric("Attendance Score", f"{score}%")
        
        tab1, tab2, tab3 = st.tabs(["📚 Materials", "🧠 AI Suite", "⏱️ Focus Timer"])
        
        with tab1:
            st.file_uploader("Upload Docs", key=f"f_{choice}")
            st.text_area("Subject Notes", height=200)

        with tab2:
            tool = st.radio("Tool", ["Summary", "Quiz", "Flashcards", "Mind Map"], horizontal=True)
            if st.button("Generate"):
                res = ask_synapse(f"Generate a {tool} for the subject {choice}")
                st.markdown(res)

        with tab3:
            st.subheader("Pomodoro Timer")
            focus_mins = st.slider("Set Focus Duration (Minutes)", 1, 60, 25)
            
            if st.button("🚀 Start Deep Work"):
                t_seconds = focus_mins * 60
                timer_place = st.empty()
                prog_bar = st.progress(0)
                
                # REAL-TIME COUNTDOWN LOGIC
                for t in range(t_seconds, -1, -1):
                    mins, secs = divmod(t, 60)
                    timer_place.header(f"⏳ Time Remaining: {mins:02d}:{secs:02d}")
                    prog_bar.progress(1.0 - (t / t_seconds))
                    time.sleep(1) # REAL SECOND WAIT
                    
                st.success("Session Complete! Take a 5-minute break.")
                st.balloons()

        st.divider()
        if st.button("🗑️ Delete Folder"):
            cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
            conn.commit() ; st.rerun()import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time

# v14.0 - ADVANCED STUDY ENGINE: INTERACTIVE WORKSPACE
st.set_page_config(page_title="Synapse Pad Pro", layout="wide")

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect("synapse_pad.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name TEXT, type TEXT, minutes INTEGER, 
    item_date TEXT, attended INTEGER DEFAULT 0
)""")
conn.commit()

# ------------------- Advanced AI Engine -------------------
def ask_synapse(prompt):
    try:
        hf_token = st.secrets["HF_TOKEN"]
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/Llama-3.2-3B-Instruct", 
            "messages": [{"role": "system", "content": "You are Synapse, an advanced academic AI."},
                         {"role": "user", "content": prompt}],
            "max_tokens": 800
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        return res.json()['choices'][0]['message']['content']
    except:
        return "⚠️ Synapse AI is momentarily offline. Check your HF_TOKEN."

# ------------------- Sidebar -------------------
with st.sidebar:
    st.title("🚀 Synapse Pad Pro")
    search_query = st.text_input("🔍 Search Folders", "").lower()
    st.divider()
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    
    if "subjects" not in st.session_state:
        cursor.execute("SELECT name FROM subjects")
        st.session_state.subjects = [row[0] for row in cursor.fetchall()]
    
    filtered_subs = [s for s in st.session_state.subjects if search_query in s.lower()]

# ------------------- Dashboard -------------------
if page == "📊 Dashboard":
    st.title("📊 Control Center")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📅 Schedule")
        sel_date = st.date_input("Date", date.today()).strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        mins_used = cursor.fetchone()[0] or 0
        st.progress(min(mins_used / 960, 1.0))
        st.caption(f"{mins_used}/960 mins utilized (16hr Cap)")

        with st.expander("🏫 Add Class"):
            c_sub = st.selectbox("Subject", st.session_state.subjects)
            c_min = st.number_input("Mins", 15, 300, 60, key="c_m")
            if st.button("Schedule"):
                cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                conn.commit() ; st.rerun()

        with st.expander("📝 Add Task"):
            t_name = st.text_input("Task")
            t_min = st.number_input("Mins", 15, 300, 30, key="t_m")
            if st.button("Add"):
                cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",t_min,sel_date))
                conn.commit() ; st.rerun()

        st.divider()
        new_s = st.text_input("New Subject Folder")
        if st.button("Create Folder"):
            cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
            conn.commit() ; st.session_state.subjects.append(new_s) ; st.rerun()

    with col2:
        st.subheader(f"📋 Timeline: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins, i_att in cursor.fetchall():
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.info(f"{'🏫' if i_type=='Class' else '🧠'} **{i_name}** ({i_mins}m)")
            if i_type == "Class":
                if c2.checkbox("Done", value=bool(i_att), key=f"at_{i_id}"):
                    cursor.execute("UPDATE items SET attended=1 WHERE id=?", (i_id,))
                else:
                    cursor.execute("UPDATE items SET attended=0 WHERE id=?", (i_id,))
                conn.commit()
            if c3.button("🗑️", key=f"d_{i_id}"):
                cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                conn.commit() ; st.rerun()

# ------------------- Synapse AI -------------------
elif page == "🤖 Synapse AI":
    st.title("🤖 Synapse Global Assistant")
    u_q = st.chat_input("How can Synapse help you today?")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"): st.write(ask_synapse(u_q))

# ------------------- Advanced Subject Explorer -------------------
elif page == "📂 Subject Explorer":
    if not filtered_subs: st.info("Create a folder first.")
    else:
        choice = st.selectbox("Select Workspace:", filtered_subs)
        
        # Performance Header
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, att = cursor.fetchone()
        att = att or 0
        score = 100 if total == 0 else round((att/total)*100, 1)
        
        c1, c2 = st.columns([3, 1])
        c1.title(f"📂 {choice} Workspace")
        c2.metric("Attendance", f"{score}%")
        
        tab1, tab2, tab3 = st.tabs(["📚 Study Materials", "🧠 AI Study Suite", "⏱️ Focus Mode"])
        
        with tab1:
            st.subheader("File Repository")
            st.file_uploader("Upload PDFs or Lecture Slides", key=f"f_{choice}")
            st.text_area("Quick Notes", placeholder="Jot down key points from today's lecture...")

        with tab2:
            st.subheader("Synapse Generative Tools")
            tool = st.segmented_control("Select AI Tool", ["Summary", "Quiz", "Flashcards", "Mind Map"])
            if st.button("Run AI Analysis", type="primary"):
                prompt_map = {
                    "Summary": f"Summarize the core concepts of {choice} in bullet points.",
                    "Quiz": f"Create a 5-question tough quiz for {choice}.",
                    "Flashcards": f"Generate 5 active recall flashcards for {choice}.",
                    "Mind Map": f"Provide a nested markdown list representing a mind map for {choice}."
                }
                if tool:
                    result = ask_synapse(prompt_map[tool])
                    st.markdown(f"### {tool} Results")
                    st.write(result)
                else: st.warning("Please select a tool.")

        with tab3:
            st.subheader("Deep Work Timer")
            t_col1, t_col2 = st.columns(2)
            mins = t_col1.number_input("Study Session (Mins)", 1, 120, 25)
            if t_col2.button("Start Focus Session"):
                st.toast(f"Focusing on {choice} for {mins} minutes!")
                # Progress bar simulation
                p_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01) # Faster for demo purposes
                    p_bar.progress(i + 1)
                st.balloons()
                st.success("Session Complete!")

        st.divider()
        if st.button("🗑️ Permanently Delete Folder"):
            cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
            cursor.execute("DELETE FROM items WHERE name=?", (choice,))
            conn.commit() ; st.rerun()
