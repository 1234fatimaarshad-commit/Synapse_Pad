import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time

# --- 1. UI CONFIGURATION (FIXED VISIBILITY) ---
st.set_page_config(page_title="SYNAPSE PAD: PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* 1. Clear Dark Background */
    .stApp {
        background-color: #050505;
        color: #ffffff;
    }
    
    /* 2. High Contrast Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0e1117 !important;
        border-right: 1px solid #00f2ff;
    }

    /* 3. Sharp Glass Cards (No Blur for Readability) */
    .stMetric, div[data-testid="stExpander"], .stAlert, .stTabs [data-baseweb="tab-panel"] {
        background: #161b22 !important;
        border: 1px solid #00f2ff !important;
        border-radius: 12px !important;
        padding: 20px;
        margin-bottom: 15px;
        color: #ffffff !important;
    }

    /* 4. Chat Message Visibility Fix */
    [data-testid="stChatMessage"] {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        margin-bottom: 10px;
    }

    /* 5. Neon Button Fix */
    div.stButton > button {
        border-radius: 10px;
        border: 2px solid #00f2ff;
        background-color: #000000;
        color: #00f2ff;
        font-weight: bold;
        height: 3em;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #00f2ff !important;
        color: #000000 !important;
        box-shadow: 0 0 15px #00f2ff;
    }

    /* 6. Input Text Visibility */
    input, textarea, [data-baseweb="select"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #00f2ff !important;
    }

    /* 7. Heading Glow */
    h1, h2, h3 {
        color: #00f2ff !important;
        text-shadow: none !important;
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

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚡ SYNAPSE PRO")
    page = st.radio("MENU", ["📊 DASHBOARD", "🤖 SYNAPSE AI", "📂 EXPLORER"])
    cursor.execute("SELECT name FROM subjects")
    subjects_list = [row[0] for row in cursor.fetchall()]

# --- 5. DASHBOARD ---
if page == "📊 DASHBOARD":
    st.title("📊 DASHBOARD")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        sel_date = st.date_input("SELECT DATE", date.today()).strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        m_used = cursor.fetchone()[0] or 0
        st.metric("NEURAL LOAD", f"{m_used}/960 MINS")
        st.progress(min(m_used / 960, 1.0))
        
        with st.expander("ADD CLASS"):
            if subjects_list:
                c_sub = st.selectbox("SUBJECT", subjects_list)
                c_min = st.number_input("MINS", 15, 480, 60)
                if st.button("ADD CLASS"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                    conn.commit()
                    st.rerun()
            else: st.info("Create a folder first.")

        new_s = st.text_input("NEW FOLDER NAME")
        if st.button("CREATE FOLDER"):
            if new_s:
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
                conn.commit()
                st.rerun()

    with col2:
        st.subheader("TIMELINE")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins, i_att in cursor.fetchall():
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.write(f"**{i_name}** ({i_mins}m)")
                if i_type == "Class":
                    if c2.checkbox("DONE", value=bool(i_att), key=f"c_{i_id}"):
                        cursor.execute("UPDATE items SET attended=1 WHERE id=?", (i_id,))
                        conn.commit()
                        st.rerun()
                if c3.button("🗑️", key=f"d_{i_id}"):
                    cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                    conn.commit()
                    st.rerun()

# --- 6. SYNAPSE AI ---
elif page == "🤖 SYNAPSE AI":
    st.title("🤖 AI ASSISTANT")
    u_q = st.chat_input("Ask Synapse...")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"):
            response = ask_synapse(u_q)
            st.write(response)

# --- 7. EXPLORER ---
elif page == "📂 EXPLORER":
    st.title("📂 ARCHIVES")
    if subjects_list:
        choice = st.selectbox("CHOOSE FOLDER", subjects_list)
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, att = cursor.fetchone()
        att = att or 0
        score = 100 if total == 0 else round((att/total)*100, 1)
        
        st.metric("ATTENDANCE", f"{score}%")
        
        tab1, tab2, tab3 = st.tabs(["MATERIALS", "AI STUDY", "TIMER"])
        with tab1:
            st.file_uploader("UPLOAD", key=f"u_{choice}")
            st.text_area("NOTES", key=f"n_{choice}")
        with tab2:
            tool = st.radio("PROTOCOL", ["Summary", "Quiz", "Flashcards"], horizontal=True)
            if st.button("RUN"):
                res = ask_synapse(f"Generate {tool} for {choice}")
                st.write(res)
        with tab3:
            mins = st.slider("MINUTES", 1, 60, 25)
            if st.button("START"):
                t_secs = mins * 60
                t_disp = st.empty()
                for t in range(t_secs, -1, -1):
                    m, s = divmod(t, 60)
                    t_disp.header(f"{m:02d}:{s:02d}")
                    time.sleep(1)
                st.balloons()
    else: st.info("No folders found.")
