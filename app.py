import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time

# ------------------- Page Config -------------------
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
        return "⚠️ Synapse AI is offline. Check HF_TOKEN in Secrets."

# ------------------- Session State -------------------
if "subjects" not in st.session_state:
    cursor.execute("SELECT name FROM subjects")
    st.session_state.subjects = [row[0] for row in cursor.fetchall()]

# ------------------- Sidebar -------------------
with st.sidebar:
    st.title("🚀 Synapse Pad Pro")
    search_query = st.text_input("🔍 Search Folders", "").lower()
    st.divider()
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    
    # Refresh subjects list
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
        res_sum = cursor.fetchone()[0]
        mins_used = res_sum if res_sum else 0
        
        st.write(f"**Capacity:** {mins_used}/960 mins")
        st.progress(min(mins_used / 960, 1.0))

        with st.expander("🏫 Add Class"):
            if not st.session_state.subjects:
                st.warning("Create a folder first!")
            else:
                c_sub = st.selectbox("Subject", st.session_state.subjects)
                c_min = st.number_input("Mins", 15, 300, 60, key="class_input")
                if st.button("Schedule Class"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                    conn.commit()
                    st.rerun()

        with st.expander("📝 Add Task"):
            t_name = st.text_input("Task Name")
            t_min = st.number_input("Mins", 15, 300, 30, key="task_input")
            if st.button("Add Task"):
                if t_name.strip():
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",t_min,sel_date))
                    conn.commit()
                    st.rerun()

        st.divider()
        st.subheader("📁 Folders")
        new_s = st.text_input("New Subject Name")
        if st.button("Create Folder"):
            if new_s.strip():
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
                conn.commit()
                st.rerun()

    with col2:
        st.subheader(f"📋 Timeline: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        day_items = cursor.fetchall()
        
        for i_id, i_name, i_type, i_mins, i_att in day_items:
            c1, c2, c3 = st.columns([4, 1, 1])
            icon = '🏫' if i_type=='Class' else '🧠'
            c1.info(f"{icon} **{i_name}** ({i_mins}m)")
            
            if i_type == "Class":
                is_done = c2.checkbox("Done", value=bool(i_att), key=f"att_check_{i_id}")
                if is_done != bool(i_att):
                    cursor.execute("UPDATE items SET attended=? WHERE id=?", (int(is_done), i_id))
                    conn.commit()
                    st.rerun()
            
            if c3.button("🗑️", key=f"del_item_{i_id}"):
                cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                conn.commit()
                st.rerun()

# ------------------- Synapse AI -------------------
elif page == "🤖 Synapse AI":
    st.title("🤖 Synapse Global Assistant")
    u_q = st.chat_input("How can Synapse help you today?")
    if u_q:
        with st.chat_message("user"):
            st.write(u_q)
        with st.chat_message("assistant"):
            st.write(ask_synapse(u_q))

# ------------------- Subject Explorer -------------------
elif page == "📂 Subject Explorer":
    if not filtered_subs:
        st.info("No folders found. Create one in the Dashboard.")
    else:
        choice = st.selectbox("Select Workspace:", filtered_subs)
        
        cursor.execute("SELECT COUNT(*) FROM items WHERE name=? AND type='Class'", (choice,))
        total_scheduled = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        res_att = cursor.fetchone()[0]
        actual_att = res_att if res_att else 0
        
        score = 100 if total_scheduled == 0 else round((actual_att/total_scheduled)*100, 1)
        
        st.title(f"📂 {choice} Workspace")
        st.metric("Attendance Score", f"{score}%", delta=f"{actual_att}/{total_scheduled} attended")
        
        tab1, tab2, tab3 = st.tabs(["📚 Materials", "🧠 AI Suite", "⏱️ Focus Timer"])
        
        with tab1:
            st.file_uploader("Upload Docs", key=f"file_uploader_{choice}")
            st.text_area("Subject Notes", height=200, placeholder="Type your lecture notes here...")

        with tab2:
            st.write("Analyze your subject using AI.")
            tool = st.radio("Tool", ["Summary", "Quiz", "Flashcards", "Mind Map"], horizontal=True)
            if st.button("Generate Study Content"):
                with st.spinner("Synapse is analyzing..."):
                    result = ask_synapse(f"Generate a {tool} for the subject {choice}")
                    st.markdown(result)

        with tab3:
            st.subheader("Pomodoro Focus Session")
            focus_mins = st.slider("Duration (Minutes)", 1, 60, 25)
            
            if st.button("🚀 Start Deep Work"):
                t_seconds = focus_mins * 60
                timer_display = st.empty()
                prog_bar = st.progress(0)
                
                for t in range(t_seconds, -1, -1):
                    m, s = divmod(t, 60)
                    timer_display.header(f"⏳ Focus Time: {m:02d}:{s:02d}")
                    prog_bar.progress(1.0 - (t / t_seconds))
                    time.sleep(1)
                
                st.success("Session Complete!")
                st.balloons()

        st.divider()
        if st.button("🗑️ Delete Folder"):
            cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
            cursor.execute("DELETE FROM items WHERE name=?", (choice,))
            conn.commit()
            st.rerun()
