import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time

# --- 1. CYBER UI & DARK MODE CONFIGURATION ---
st.set_page_config(page_title="SYNAPSE PAD: PRO", layout="wide", initial_sidebar_state="expanded")

# Advanced CSS for Deep Space Background, Glassmorphism, and Neon Glow
st.markdown("""
    <style>
    /* Force Deep Space Background */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #050505 100%);
        color: #e6edf3;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(10, 10, 15, 0.95) !important;
        border-right: 1px solid #00f2ff;
    }

    /* Glassmorphism Cards */
    .stMetric, .stChatMessage, div[data-testid="stExpander"], .stAlert, .stTabs [data-baseweb="tab-panel"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(0, 242, 255, 0.2) !important;
        border-radius: 15px !important;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        padding: 20px;
        margin-bottom: 10px;
    }

    /* Neon Button Glow */
    div.stButton > button {
        border-radius: 12px;
        border: 1px solid #00f2ff;
        background-color: transparent;
        color: #00f2ff;
        text-transform: uppercase;
        font-weight: bold;
        letter-spacing: 1.5px;
        transition: all 0.3s ease-in-out;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #00f2ff !important;
        color: #000 !important;
        box-shadow: 0 0 25px #00f2ff;
        transform: scale(1.02);
    }

    /* Input Fields styling */
    input, textarea, [data-baseweb="select"] {
        background-color: #0d1117 !important;
        border: 1px solid rgba(0, 242, 255, 0.3) !important;
        color: #00f2ff !important;
        border-radius: 8px !important;
    }

    /* Headings */
    h1, h2, h3 {
        color: #ffffff;
        text-shadow: 0 0 15px rgba(0, 242, 255, 0.6);
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Progress Bar Neon Glow */
    div[data-testid="stProgress"] > div > div > div > div {
        background-image: linear-gradient(to right, #00f2ff, #ab47bc) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE INITIALIZATION ---
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

# --- 3. AI CORE ENGINE ---
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
        return "⚠️ SYSTEM ERROR: NEURAL LINK FAILED. CHECK HF_TOKEN."

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚡ SYNAPSE PRO")
    st.caption("OS v16.5 | CYBER-WORKSPACE")
    st.divider()
    page = st.radio("SYSTEM ACCESS", ["📊 DASHBOARD", "🤖 SYNAPSE AI", "📂 EXPLORER"])
    
    cursor.execute("SELECT name FROM subjects")
    subjects_list = [row[0] for row in cursor.fetchall()]

# --- 5. DASHBOARD (TIMELINE & PLANNING) ---
if page == "📊 DASHBOARD":
    st.title("📊 SYSTEM CONTROL")
    col1, col2 = st.columns([1.2, 2])
    
    with col1:
        st.subheader("🔋 ENERGY CORE")
        sel_date = st.date_input("TARGET DATE", date.today()).strftime("%Y-%m-%d")
        
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        m_used = cursor.fetchone()[0] or 0
        
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
                    st.toast(f"✅ {c_sub} Synced!")
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
                c1.info(f"{icon} **{i_name}** | {i_mins}m")
                
                if i_type == "Class":
                    if c2.checkbox("DONE", value=bool(i_att), key=f"c_{i_id}"):
                        cursor
