import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time

# 1. PAGE SETUP
st.set_page_config(page_title="Synapse Pad Pro", layout="wide")

# 2. DATABASE CONNECTION
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

# 3. AI ENGINE FUNCTION
def ask_synapse(prompt):
    try:
        hf_token = st.secrets["HF_TOKEN"]
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/Llama-3.2-3B-Instruct", 
            "messages": [
                {"role": "system", "content": "You are Synapse, an academic AI."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 800
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        return res.json()['choices'][0]['message']['content']
    except:
        return "⚠️ AI Error. Please check your HF_TOKEN in Streamlit Secrets."

# 4. SIDEBAR NAVIGATION
with st.sidebar:
    st.title("🚀 Synapse Pad Pro")
    search_query = st.text_input("🔍 Search Folders", "").lower()
    st.divider()
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    
    # Load subjects for sidebar
    cursor.execute("SELECT name FROM subjects")
    subjects_list = [row[0] for row in cursor.fetchall()]
    filtered_subs = [s for s in subjects_list if search_query in s.lower()]

# 5. DASHBOARD PAGE
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
            if not subjects_list:
                st.warning("Create a folder first!")
            else:
                c_sub = st.selectbox("Subject", subjects_list)
                c_min = st.number_input("Mins", 15, 300, 60)
                if st.button("Schedule Class"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                    conn.commit()
                    st.rerun()

        with st.expander("📝 Add Task"):
            t_name = st.text_input("Task Name")
            t_min = st.number_input("Mins", 15, 300, 30)
            if st.button("Add Task"):
                if t_name.strip():
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",t_min,sel_date))
                    conn.commit()
                    st.rerun()

        st.divider()
        st.subheader("📁 New Folder")
        new_s = st.text_input("Folder Name")
        if st.button("Create"):
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
                is_done = c2.checkbox("Done", value=bool(i_att), key=f"att_{i_id}")
                if is_done != bool(i_att):
                    cursor.execute("UPDATE items SET attended=? WHERE id=?", (int(is_done), i_id))
                    conn.commit()
                    st.rerun()
            
            if c3.button("🗑️", key=f"del_{i_id}"):
                cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                conn.commit()
                st.rerun()

# 6. SYNAPSE AI PAGE
elif page == "🤖 Synapse AI":
    st.title("🤖 Synapse Assistant")
    u_q = st.chat_input("Ask me anything...")
    if u_q:
        with st.chat_message("user"):
            st.write(u_q)
        with st.chat_message("assistant"):
            st.write(ask_synapse(u_q))

# 7. SUBJECT EXPLORER PAGE
elif page == "📂 Subject Explorer":
    if not filtered_subs:
        st.info("No folders match your search.")
    else:
        choice = st.selectbox("Select Workspace:", filtered_subs)
        
        # Attendance Score Calculation
        cursor.execute("SELECT COUNT(*) FROM items WHERE name=? AND type='Class'", (choice,))
        total_s = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        res_a = cursor.fetchone()[0]
        actual_a = res_a if res_a else 0
        score = 100 if total_s == 0 else round((actual_a/total_s)*100, 1)
        
        st.title(f"📂 {choice} Workspace")
        st.metric("Attendance Rate", f"{score}%")
        
        tab1, tab2, tab3 = st.tabs(["📚 Materials", "🧠 AI Study Suite", "⏱️ Focus Timer"])
        
        with tab1:
            st.file_uploader("Upload materials", key=f"upload_{choice}")
            st.text_area("Notes", placeholder="Add notes for this subject...")

        with tab2:
            tool = st.radio("Tool", ["Summary", "Quiz", "Flashcards", "Mind Map"], horizontal=True)
            if st.button("Generate"):
                with st.spinner("Synapse is thinking..."):
                    result = ask_synapse(f"Provide a {tool} for {choice}")
                    st.markdown(result)

        with tab3:
            st.subheader("Pomodoro Session")
            f_mins = st.slider("Minutes", 1, 60, 25)
            if st.button("Start Timer"):
                t_secs = f_mins * 60
                timer_spot = st.empty()
                p_bar = st.progress(0)
                for t in range(t_secs, -1, -1):
                    m, s = divmod(t, 60)
                    timer_spot.header(f"⏳ {m:02d}:{s:02d}")
                    p_bar.progress(1.0 - (t / t_secs))
                    time.sleep(1)
                st.balloons()
                st.success("Work Complete!")

        st.divider()
        if st.button("🗑️ Delete Folder"):
            cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
            cursor.execute("DELETE FROM items WHERE name=?", (choice,))
            conn.commit()
            st.rerun()
