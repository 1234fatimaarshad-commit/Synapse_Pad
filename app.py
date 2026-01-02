import streamlit as st
import sqlite3
import requests
from datetime import datetime, date
import time
import pandas as pd

# --- 1. UI CONFIGURATION (EYE-FRIENDLY MODERN BLUE) ---
st.set_page_config(page_title="SYNAPSE PAD: PRO", layout="wide")

st.markdown("""
    <style>
    /* 1. Deep Midnight Blue Background (Easier on eyes than Black) */
    .stApp {
        background-color: #1a1c24;
        color: #ffffff;
    }
    
    /* 2. Sidebar - Darker Slate */
    section[data-testid="stSidebar"] {
        background-color: #111217 !important;
        border-right: 2px solid #4facfe;
    }

    /* 3. Containers - Cloud Grey/Blue (High Visibility) */
    .stMetric, div[data-testid="stExpander"], .stTabs [data-baseweb="tab-panel"], [data-testid="stChatMessage"] {
        background: #f0f2f6 !important;
        border: 1px solid #4facfe !important;
        border-radius: 12px !important;
        color: #1a1c24 !important; /* Dark text for light boxes */
        padding: 15px;
    }

    /* 4. Ensure Markdown text inside containers is visible (Dark on Light) */
    .stMetric div, .stExpander div, .stTabs p, [data-testid="stChatMessage"] p {
        color: #1a1c24 !important;
    }

    /* 5. Sapphire Buttons */
    div.stButton > button {
        background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
        color: white !important;
        border: none;
        font-weight: bold;
        border-radius: 8px;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.5);
        transform: translateY(-2px);
    }

    /* 6. Input Fields - Bright and Sharp */
    input, textarea {
        background-color: #ffffff !important;
        color: #1a1c24 !important;
        border: 2px solid #4facfe !important;
    }
    
    /* 7. Titles */
    h1, h2, h3 {
        color: #4facfe !important;
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
    st.title("💎 SYNAPSE PRO")
    page = st.radio("Navigate", ["📊 Dashboard", "🤖 Synapse AI", "📂 Subject Explorer"])
    
    st.divider()
    with st.expander("🛠️ SYSTEM SETTINGS"):
        if st.button("🚨 EMERGENCY DATA RESET"):
            cursor.execute("DELETE FROM items"); cursor.execute("DELETE FROM subjects")
            conn.commit(); st.warning("All data purged."); st.rerun()
    
    cursor.execute("SELECT name FROM subjects")
    subjects_list = [row[0] for row in cursor.fetchall()]

# --- 5. DASHBOARD ---
if page == "📊 Dashboard":
    st.title("📊 Control Dashboard")
    col1, col2 = st.columns([1.2, 2])
    
    with col1:
        sel_date = st.date_input("Target Date", date.today()).strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        m_used = cursor.fetchone()[0] or 0
        st.metric("Daily Capacity", f"{m_used}/960 mins")
        st.progress(min(m_used / 960, 1.0))

        # PIE CHART (Now in Sapphire tones)
        cursor.execute("SELECT type, SUM(minutes) FROM items WHERE item_date=? GROUP BY type", (sel_date,))
        chart_data = cursor.fetchall()
        if chart_data:
            df = pd.DataFrame(chart_data, columns=['Type', 'Minutes'])
            st.vega_lite_chart(df, {
                'mark': {'type': 'arc', 'innerRadius': 40},
                'encoding': {
                    'theta': {'field': 'Minutes', 'type': 'quantitative'},
                    'color': {'field': 'Type', 'type': 'nominal', 'scale': {'range': ['#4facfe', '#00f2fe']}},
                }
            }, use_container_width=True)
        
        with st.expander("🏫 Schedule Class"):
            if subjects_list:
                c_sub = st.selectbox("Choose Subject", subjects_list)
                c_min = st.number_input("Minutes", 15, 480, 60)
                if st.button("Add to Schedule"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                    conn.commit(); st.rerun()

        with st.expander("📝 Add Task"):
            t_name = st.text_input("Task Description")
            t_min = st.number_input("Task Minutes", 15, 300, 30)
            if st.button("Log Task"):
                if t_name:
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",t_min,sel_date))
                    conn.commit(); st.rerun()

        st.divider()
        new_s = st.text_input("Create Subject Folder")
        if st.button("Initialize Folder"):
            if new_s:
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
                conn.commit(); st.rerun()

    with col2:
        st.subheader(f"Timeline: {sel_date}")
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
    st.title("🤖 AI Research Assistant")
    u_q = st.chat_input("Ask a question...")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"):
            st.write(ask_synapse(u_q))

# --- 7. SUBJECT EXPLORER ---
elif page == "📂 Subject Explorer":
    st.title("📂 Workspace Explorer")
    if subjects_list:
        choice = st.selectbox("Active Folder", subjects_list)
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, res_att = cursor.fetchone()
        att = res_att or 0
        score = 100 if total == 0 else round((att/total)*100, 1)
        st.metric("Attendance Score", f"{score}%")
        
        tab1, tab2, tab3 = st.tabs(["📚 Materials", "🧠 AI Study Tools", "⏱️ Focus Timer"])
        with tab1:
            st.file_uploader("Upload Docs", key=f"u_{choice}")
            notes = st.text_area("Subject Notes", key=f"n_{choice}")
            if notes:
                st.download_button("💾 Export Notes (.txt)", notes, f"{choice}.txt")

        with tab2:
            tool = st.radio("Study Protocol", ["Summary", "Quiz", "Flashcards"], horizontal=True)
            if st.button("Generate"):
                with st.spinner("AI processing..."):
                    st.write(ask_synapse(f"Generate {tool} for {choice}"))
        with tab3:
            mins = st.slider("Focus Minutes", 1, 60, 25)
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
    else: st.info("Create a folder in the Dashboard first.")
