import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time
import pandas as pd

# --- 1. UI CONFIGURATION ---
st.set_page_config(page_title="SYNAPSE PAD: PRO", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ffffff; }
    div[data-testid="stChatMessage"] p, .stMarkdown p, .stMarkdown li {
        color: #ffffff !important; font-size: 1.1rem !important;
    }
    .stMetric, div[data-testid="stExpander"], .stTabs [data-baseweb="tab-panel"] {
        background: #161b22 !important;
        border: 2px solid #00f2ff !important;
        border-radius: 15px !important;
        color: #ffffff !important;
    }
    div.stButton > button {
        border: 2px solid #00f2ff; background-color: #000000;
        color: #00f2ff; font-weight: bold; width: 100%; border-radius: 10px;
    }
    div.stButton > button:hover {
        background-color: #00f2ff !important; color: #000000 !important;
        box-shadow: 0 0 15px #00f2ff;
    }
    input, textarea {
        background-color: #000000 !important; color: #ffffff !important;
        border: 1px solid #00f2ff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
conn = sqlite3.connect("synapse_final.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name TEXT, type TEXT, minutes INTEGER, 
    item_date TEXT, attended INTEGER DEFAULT 0
)""")
conn.commit()

# --- 3. AI ENGINE ---
def ask_synapse(prompt):
    try:
        hf_token = st.secrets["HF_TOKEN"]
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/Llama-3.2-3B-Instruct", 
            "messages": [{"role": "system", "content": "You are Synapse Pro AI."},
                         {"role": "user", "content": prompt}]
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return "⚠️ CONNECTION ERROR: Check HF_TOKEN."

# --- 4. SIDEBAR (WITH EMERGENCY RESET) ---
with st.sidebar:
    st.title("⚡ SYNAPSE PRO")
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    
    st.divider()
    with st.expander("🛠️ SYSTEM SETTINGS"):
        if st.button("🚨 EMERGENCY DATA RESET"):
            cursor.execute("DELETE FROM items")
            cursor.execute("DELETE FROM subjects")
            conn.commit()
            st.warning("All data purged.")
            st.rerun()
    
    cursor.execute("SELECT name FROM subjects")
    subjects_list = [row[0] for row in cursor.fetchall()]

# --- 5. DASHBOARD (WITH PIE CHART) ---
if page == "📊 Dashboard":
    st.title("📊 Main Dashboard")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        sel_date = st.date_input("Select Date", date.today()).strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        m_used = cursor.fetchone()[0] or 0
        st.metric("Capacity Used", f"{m_used}/960 mins")
        st.progress(min(m_used / 960, 1.0))

        # PIE CHART
        cursor.execute("SELECT type, SUM(minutes) FROM items WHERE item_date=? GROUP BY type", (sel_date,))
        chart_data = cursor.fetchall()
        if chart_data:
            df = pd.DataFrame(chart_data, columns=['Type', 'Minutes'])
            st.write("🕒 **Neural Distribution**")
            st.vega_lite_chart(df, {
                'mark': {'type': 'arc', 'innerRadius': 40},
                'encoding': {
                    'theta': {'field': 'Minutes', 'type': 'quantitative'},
                    'color': {'field': 'Type', 'type': 'nominal', 'scale': {'range': ['#00f2ff', '#ab47bc']}},
                }
            }, use_container_width=True)
        
        with st.expander("🏫 Schedule Class"):
            if subjects_list:
                c_sub = st.selectbox("Choose Subject", subjects_list)
                c_min = st.number_input("Minutes", 15, 480, 60)
                if st.button("Add to Schedule"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                    conn.commit(); st.rerun()
            else: st.warning("Create a folder first.")

        with st.expander("📝 Add Task"):
            t_name = st.text_input("Task Description")
            t_min = st.number_input("Task Minutes", 15, 300, 30)
            if st.button("Log Task"):
                if t_name:
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",t_min,sel_date))
                    conn.commit(); st.rerun()

        st.divider()
        new_s = st.text_input("Create New Subject Folder")
        if st.button("Create Folder"):
            if new_s:
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
                conn.commit(); st.rerun()

    with col2:
        st.subheader(f"Timeline for {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins, i_att in cursor.fetchall():
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                icon = "🏫" if i_type == "Class" else "🧠"
                c1.write(f"{icon} **{i_name}** ({i_mins}m)")
                if i_type == "Class":
                    if c2.checkbox("Done", value=bool(i_att), key=f"c_{i_id}"):
                        cursor.execute("UPDATE items SET attended=1 WHERE id=?", (i_id,))
                        conn.commit(); st.rerun()
                if c3.button("🗑️", key=f"d_{i_id}"):
                    cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                    conn.commit(); st.rerun()

# --- 6. SYNAPSE AI ---
elif page == "🤖 Synapse AI":
    st.title("🤖 Synapse AI Assistant")
    u_q = st.chat_input("Ask anything...")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"):
            st.markdown(f"**{ask_synapse(u_q)}**")

# --- 7. SUBJECT EXPLORER (WITH EXPORT) ---
elif page == "📂 Subject Explorer":
    st.title("📂 Subject Explorer")
    if subjects_list:
        choice = st.selectbox("Open Subject Folder", subjects_list)
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, res_att = cursor.fetchone()
        att = res_att or 0
        score = 100 if total == 0 else round((att/total)*100, 1)
        st.metric("Attendance Score", f"{score}%")
        
        tab1, tab2, tab3 = st.tabs(["📚 Materials", "🧠 AI Study Tools", "⏱️ Focus Timer"])
        with tab1:
            st.file_uploader("Upload Documents", key=f"u_{choice}")
            notes_content = st.text_area("Notes", key=f"n_{choice}")
            
            # EXPORT FEATURE
            if notes_content:
                st.download_button(
                    label="💾 EXPORT NOTES TO TXT",
                    data=notes_content,
                    file_name=f"{choice}_Notes.txt",
                    mime="text/plain"
                )

        with tab2:
            tool = st.radio("Generate Study Aid", ["Summary", "Quiz", "Flashcards"], horizontal=True)
            if st.button("Generate Action"):
                with st.spinner("AI Generating..."):
                    st.markdown(ask_synapse(f"Generate {tool} for {choice}"))
        with tab3:
            mins = st.slider("Session Minutes", 1, 60, 25)
            if st.button("Start Timer"):
                t_secs = mins * 60
                t_disp = st.empty()
                p_bar = st.progress(0)
                for t in range(t_secs, -1, -1):
                    m, s = divmod(t, 60)
                    t_disp.header(f"⏳ {m:02d}:{s:02d}")
                    p_bar.progress(1.0 - (t / t_secs))
                    time.sleep(1)
                st.balloons()
    else: st.info("No folders found.")
