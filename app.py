import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time

# --- 1. CYBER UI CONFIGURATION ---
st.set_page_config(page_title="SYNAPSE PAD: PRO", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Glassmorphism and Neon Accents
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    div.stButton > button {
        border-radius: 10px; border: 1px solid #00f2ff;
        background-color: #161b22; color: #00f2ff;
        transition: 0.3s; font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #00f2ff; color: #000;
        box-shadow: 0 0 15px #00f2ff;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px; border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stAlert { border-radius: 15px; border: none; }
    div[data-testid="stExpander"] {
        border: 1px solid rgba(0, 242, 255, 0.2);
        border-radius: 15px; background: rgba(0, 0, 0, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & LOGIC ---
conn = sqlite3.connect("synapse_pro.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name TEXT, type TEXT, minutes INTEGER, 
    item_date TEXT, attended INTEGER DEFAULT 0
)""")
conn.commit()

def ask_synapse(prompt):
    try:
        hf_token = st.secrets["HF_TOKEN"]
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/Llama-3.2-3B-Instruct", 
            "messages": [{"role": "system", "content": "You are Synapse Pro, a futuristic academic AI."},
                         {"role": "user", "content": prompt}]
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return "⚠️ SYSTEM ERROR: AI CORE OFFLINE. CHECK SECRETS."

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("⚡ SYNAPSE PRO")
    st.caption("v16.0 | Cyber-Academic OS")
    st.divider()
    page = st.radio("SYSTEM ACCESS", ["📊 DASHBOARD", "🤖 SYNAPSE AI", "📂 EXPLORER"])
    
    cursor.execute("SELECT name FROM subjects")
    subjects_list = [row[0] for row in cursor.fetchall()]

# --- 4. DASHBOARD (ENERGY CENTER) ---
if page == "📊 DASHBOARD":
    st.title("📊 SYSTEM CONTROL")
    col1, col2 = st.columns([1.2, 2])
    
    with col1:
        st.subheader("🔋 ENERGY CORE")
        sel_date = st.date_input("TARGET DATE", date.today()).strftime("%Y-%m-%d")
        
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        m_used = cursor.fetchone()[0] or 0
        
        # Dynamic Progress Bar Color Logic
        bar_color = "#00f2ff" # Cyan
        if m_used > 480: bar_color = "#3d5afe" # Blue
        if m_used > 800: bar_color = "#ab47bc" # Purple
        
        st.write(f"**NEURAL LOAD:** {m_used} / 960 MINS")
        st.progress(min(m_used / 960, 1.0))
        
        with st.expander("➕ SCHEDULE PATHWAY"):
            if not subjects_list: st.warning("Initialize a Subject first.")
            else:
                c_sub = st.selectbox("Subject", subjects_list)
                c_min = st.number_input("Duration (min)", 15, 480, 60)
                if st.button("EXECUTE"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                    conn.commit()
                    st.toast(f"✅ {c_sub} Synced to Timeline!")
                    st.rerun()

        with st.expander("📝 ADD NEURAL TASK"):
            t_name = st.text_input("Task Label")
            if st.button("LOG TASK"):
                cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",30,sel_date))
                conn.commit()
                st.toast("🧠 Task Uploaded!")
                st.rerun()

        st.divider()
        new_s = st.text_input("INITIALIZE NEW SUBJECT")
        if st.button("CREATE FOLDER"):
            if new_s:
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
                conn.commit()
                st.balloons()
                st.rerun()

    with col2:
        st.subheader(f"📋 TIMELINE: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins, i_att in cursor.fetchall():
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                icon = "🏫" if i_type == "Class" else "🧠"
                status_color = "🟢" if i_att else "⚪"
                c1.info(f"{icon} **{i_name}** | {i_mins}m")
                
                if i_type == "Class":
                    if c2.checkbox("DONE", value=bool(i_att), key=f"c_{i_id}"):
                        cursor.execute("UPDATE items SET attended=1 WHERE id=?", (i_id,))
                        conn.commit()
                    else:
                        cursor.execute("UPDATE items SET attended=0 WHERE id=?", (i_id,))
                        conn.commit()
                
                if c3.button("🗑️", key=f"d_{i_id}"):
                    cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                    conn.commit()
                    st.rerun()

# --- 5. SYNAPSE AI (CHART INTERFACE) ---
elif page == "🤖 SYNAPSE AI":
    st.title("🤖 SYNAPSE NEURAL LINK")
    st.write("Current Model: `Meta-Llama-3.2` | Status: `Optimized`")
    u_q = st.chat_input("Input command or query...")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"):
            with st.spinner("Processing Neural Pathways..."):
                st.write(ask_synapse(u_q))

# --- 6. EXPLORER (GAMIFIED WORKSPACE) ---
elif page == "📂 EXPLORER":
    st.title("📂 NEURAL ARCHIVES")
    if not subjects_list: st.info("Archives Empty. Initialize subjects via Dashboard.")
    else:
        choice = st.selectbox("Select Workspace", subjects_list)
        
        # ATTENDANCE ACHIEVEMENT LOGIC
        cursor.execute("SELECT COUNT(*) FROM items WHERE name=? AND type='Class'", (choice,))
        total = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        res_a = cursor.fetchone()[0]
        att = res_a if res_a else 0
        score = 100 if total == 0 else round((att/total)*100, 1)

        c1, c2 = st.columns([2, 1])
        with c1:
            st.header(f"FOLDER: {choice}")
            if score == 100: st.success("🏆 RANK: PERFECTIONIST (100% Streak)")
            elif score >= 75: st.info("⭐ RANK: ELITE (Maintaining 75%+)")
            else: st.warning("⚠️ RANK: RECOVERY REQUIRED")
        
        with c2:
            st.metric("SYNC RATE", f"{score}%", help="Must stay above 75% for Academic Optimization.")

        tab1, tab2, tab3 = st.tabs(["📑 MATERIALS", "🧠 STUDY SUITE", "⚡ FOCUS MODE"])
        
        with tab1:
            st.file_uploader("Upload Knowledge Files", key=f"u_{choice}")
            st.text_area("Memory Log (Notes)", height=200)

        with tab2:
            st.write("Select a tool to generate knowledge structures:")
            tool = st.pills("Tools", ["Summary", "Quiz", "Flashcards", "Mind Map"])
            if st.button("RUN GENERATOR"):
                with st.status("Initializing Synapse AI..."):
                    st.write("Scanning materials...")
                    time.sleep(1)
                    st.write("Constructing neural map...")
                    result = ask_synapse(f"Generate a {tool} for {choice}")
                st.markdown(result)

        with tab3:
            st.subheader("DEEP WORK TIMER")
            mins = st.slider("Focus Minutes", 1, 60, 25)
            if st.button("INITIATE DEEP WORK"):
                st.toast("System locked for study session.")
                timer_place = st.empty()
                p_bar = st.progress(0)
                for t in range(mins * 60, -1, -1):
                    m, s = divmod(t, 60)
                    timer_place.header(f"⏳ {m:02d}:{s:02d}")
                    p_bar.progress(1.0 - (t / (mins * 60)))
                    time.sleep(1)
                st.snow()
                st.success("SESSION COMPLETE. COGNITIVE GAINS DETECTED.")

        st.divider()
        if st.button("🧨 PURGE FOLDER"):
            cursor.execute("DELETE FROM subjects WHERE name=?", (choice,))
            cursor.execute("DELETE FROM items WHERE name=?", (choice,))
            conn.commit()
            st.rerun()
