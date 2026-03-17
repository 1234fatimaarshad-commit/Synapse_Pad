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
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #0f172a !important; }
    section[data-testid="stSidebar"] * { color: #f8fafc !important; }

    /* MAIN SCREEN TEXT TO BLACK */
    [data-testid="stMain"] p, 
    [data-testid="stMain"] h1, 
    [data-testid="stMain"] h2, 
    [data-testid="stMain"] h3, 
    [data-testid="stMain"] label,
    [data-testid="stMain"] div,
    [data-testid="stMain"] span,
    [data-testid="stMain"] small { 
        color: #000000 !important; 
    }

    .stMetric { background: #ffffff !important; border: 2px solid #10b981 !important; border-radius: 10px !important; padding: 15px !important; }
    div[data-testid="stExpander"], .stTabs [data-baseweb="tab-panel"], [data-testid="stChatMessage"] {
        background: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; padding: 18px;
    }
    div.stButton > button { background-color: #10b981; color: white !important; font-weight: 600; border-radius: 6px; width: 100%; }
    input, textarea { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #94a3b8 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
conn = sqlite3.connect("synapse_final.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY, marks TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, minutes INTEGER, item_date TEXT, attended INTEGER DEFAULT 0)")
conn.commit()

# --- 3. AI ENGINE (UPDATED URL) ---
def ask_synapse(prompt):
    try:
        hf_token = "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"
        # Using the standard Inference API URL
        API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct"
        headers = {"Authorization": f"Bearer {hf_token}"}
        
        payload = {
            "inputs": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nYou are Synapse Pro AI assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
            "parameters": {"max_new_tokens": 500, "return_full_text": False}
        }
        
        res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        
        if res.status_code == 200:
            output = res.json()
            # Handle different return formats from HF
            if isinstance(output, list) and len(output) > 0:
                return output[0].get('generated_text', 'No response text.')
            return str(output)
        elif res.status_code == 503:
            return "⏳ AI is loading/starting up. Please try again in 30 seconds."
        else:
            return f"⚠️ Connection Error: {res.status_code}. Make sure your token is active."
            
    except Exception as e: 
        return f"⚠️ AI ERROR: {str(e)}"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("SYNAPSE PRO")
    search_query = st.text_input("🔍 SEARCH FOLDERS", "").lower()
    st.divider()
    page = st.radio("NAVIGATION", ["DASHBOARD", "SYNAPSE AI", "SUBJECT EXPLORER"])
    st.divider()
    if st.button("🚨 RESET ALL DATA"):
        cursor.execute("DELETE FROM items"); cursor.execute("DELETE FROM subjects")
        conn.commit(); st.rerun()

    cursor.execute("SELECT name FROM subjects")
    subjects_list = [row[0] for row in cursor.fetchall()]
    filtered_subs = [s for s in subjects_list if search_query in s.lower()]

# --- 5. DASHBOARD ---
if page == "DASHBOARD":
    st.title("System Dashboard")
    col1, col2 = st.columns([1.2, 2])
    with col1:
        sel_date = st.date_input("TARGET DATE", date.today()).strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(minutes) FROM items WHERE item_date=?", (sel_date,))
        m_used = cursor.fetchone()[0] or 0
        st.metric("NEURAL LOAD", f"{m_used}/960 MINS")
        st.progress(min(m_used / 960, 1.0))
        
        cursor.execute("SELECT type, SUM(minutes) FROM items WHERE item_date=? GROUP BY type", (sel_date,))
        chart_data = cursor.fetchall()
        if chart_data:
            df = pd.DataFrame(chart_data, columns=['Type', 'Minutes'])
            st.vega_lite_chart(df, {'mark': {'type': 'arc', 'innerRadius': 40}, 'encoding': {'theta': {'field': 'Minutes', 'type': 'quantitative'}, 'color': {'field': 'Type', 'type': 'nominal', 'scale': {'range': ['#10b981', '#0f172a']}}}}, use_container_width=True)
        
        with st.expander("ADD CLASS"):
            if subjects_list:
                c_sub = st.selectbox("SELECT SUBJECT", subjects_list)
                if st.button("SAVE"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",60,sel_date))
                    conn.commit(); st.rerun()
        
        new_s = st.text_input("CREATE NEW FOLDER")
        if st.button("INITIALIZE"):
            if new_s:
                cursor.execute("INSERT OR IGNORE INTO subjects(name, marks) VALUES (?,?)", (new_s, ""))
                conn.commit(); st.rerun()

    with col2:
        st.subheader(f"TIMELINE: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins, i_att in cursor.fetchall():
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.write(f"**[{i_type.upper()}]** {i_name}")
                if i_type == "Class":
                    if c2.checkbox("DONE", value=bool(i_att), key=f"c_{i_id}"):
                        cursor.execute("UPDATE items SET attended=1 WHERE id=?", (i_id,))
                        conn.commit(); st.rerun()
                if c3.button("DEL", key=f"d_{i_id}"):
                    cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                    conn.commit(); st.rerun()

# --- 6. SUBJECT EXPLORER ---
elif page == "SUBJECT EXPLORER":
    st.title("Workspace Explorer")
    display_list = filtered_subs if search_query else subjects_list
    
    if display_list:
        choice = st.selectbox("ACTIVE FOLDER", display_list)
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, res_att = cursor.fetchone()
        att_rate = 100 if total == 0 else round(((res_att or 0)/total)*100, 1)
        
        m1, m2 = st.columns(2)
        m1.metric("SYNC RATE", f"{att_rate}%")
        
        tab1, tab2 = st.tabs(["RESOURCES", "AI TOOLS"])
        with tab1:
            st.text_area("SESSION NOTES", height=200, key=f"notes_{choice}")
        with tab2:
            if st.button("GENERATE SUMMARY"):
                notes = st.session_state.get(f"notes_{choice}", "")
                with st.spinner("Brainstorming..."):
                    st.write(ask_synapse(f"Summarize these notes: {notes}"))

else:
    st.title("Synapse AI Core")
    u_q = st.chat_input("Command...")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"): st.write(ask_synapse(u_q))
