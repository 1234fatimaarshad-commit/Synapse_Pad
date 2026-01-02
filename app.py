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
    .stApp { background-color: #f8fafc; color: #1e293b; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #0f172a !important; }
    section[data-testid="stSidebar"] * { color: #f8fafc !important; }
    .stMetric { background: #ffffff !important; border: 2px solid #10b981 !important; border-radius: 10px !important; padding: 15px !important; }
    div[data-testid="stExpander"], .stTabs [data-baseweb="tab-panel"], [data-testid="stChatMessage"] {
        background: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; padding: 18px;
    }
    div.stButton > button { background-color: #10b981; color: white !important; font-weight: 600; border-radius: 6px; width: 100%; }
    input, textarea { background-color: #ffffff !important; color: #1e293b !important; border: 1px solid #94a3b8 !important; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
conn = sqlite3.connect("synapse_final.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY, marks TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, minutes INTEGER, item_date TEXT, attended INTEGER DEFAULT 0)")
conn.commit()

# --- 3. AI ENGINE ---
def ask_synapse(prompt):
    try:
        hf_token = st.secrets["HF_TOKEN"]
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        payload = {"model": "meta-llama/Llama-3.2-3B-Instruct", "messages": [{"role": "system", "content": "You are Synapse Pro AI."}, {"role": "user", "content": prompt}]}
        res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except: return "⚠️ AI OFFLINE."

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
                if st.button("SAVE CLASS"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",60,sel_date))
                    conn.commit(); st.rerun()
        
        with st.expander("ADD TASK"):
            t_name = st.text_input("TASK LABEL")
            if st.button("SAVE TASK"):
                cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",30,sel_date))
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
                        cursor.execute("UPDATE items SET attended=1 WHERE id=?"); conn.commit(); st.rerun()
                if c3.button("DEL", key=f"d_{i_id}"):
                    cursor.execute("DELETE FROM items WHERE id=?"); conn.commit(); st.rerun()

# --- 6. SUBJECT EXPLORER (STABLE FEATURES) ---
elif page == "SUBJECT EXPLORER":
    st.title("Workspace Explorer")
    display_list = filtered_subs if search_query else subjects_list
    
    if display_list:
        choice = st.selectbox("ACTIVE FOLDER", display_list)
        
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, res_att = cursor.fetchone()
        att_rate = 100 if total == 0 else round(((res_att or 0)/total)*100, 1)
        
        cursor.execute("SELECT marks FROM subjects WHERE name=?", (choice,))
        saved_marks = cursor.fetchone()[0] or ""
        mark_list = [float(x) for x in saved_marks.split(',') if x.strip()]
        avg_mark = round(sum(mark_list)/len(mark_list), 1) if mark_list else 0.0
        eff_score = round((att_rate + avg_mark) / 2, 1) if mark_list else att_rate

        # Efficiency Score Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("SYNC RATE", f"{att_rate}%")
        m2.metric("ACADEMIC AVG", f"{avg_mark}%")
        m3.metric("EFFICIENCY SCORE", f"{eff_score}%")
        
        tab1, tab2, tab3 = st.tabs(["MATERIALS & GRADES", "AI STUDY TOOLS", "TIMER"])
        
        with tab1:
            st.subheader("Grade Management")
            grade_input = st.text_input("Enter Marks (Ex: 85, 90, 78)", value=saved_marks)
            if st.button("UPDATE SUBJECT GRADES"):
                cursor.execute("UPDATE subjects SET marks=? WHERE name=?", (grade_input, choice))
                conn.commit(); st.success("Synced!"); time.sleep(0.5); st.rerun()
            
            st.divider()
            uploaded_file = st.file_uploader("UPLOAD MEDIA", key=f"u_{choice}")
            notes = st.text_area("SESSION NOTES", height=200, key=f"notes_{choice}")

        with tab2:
            st.subheader("Neural Analysis")
            tool = st.radio("PROTOCOL", ["Doc-to-Text", "Summary", "Quiz", "Flashcards"], horizontal=True)
            if st.button("EXECUTE ANALYSIS"):
                user_context = st.session_state.get(f"notes_{choice}", "")
                file_name = uploaded_file.name if uploaded_file else "No File"
                prompt = f"Subject: {choice}. File: {file_name}. Notes: {user_context}. Task: {tool}."
                with st.spinner("Analyzing..."): st.write(ask_synapse(prompt))

        with tab3:
            mins = st.slider("FOCUS SESSION", 1, 60, 25)
            if st.button("START TIMER"):
                t_secs = mins * 60
                t_disp = st.empty(); p_bar = st.progress(0)
                for t in range(t_secs, -1, -1):
                    m, s = divmod(t, 60)
                    t_disp.header(f"REMAINING: {m:02d}:{s:02d}")
                    p_bar.progress(1.0 - (t/t_secs))
                    time.sleep(1)
                st.session_state['timer_done'] = True
                st.rerun()

    # Global Balloon Trigger
    if st.session_state.get('timer_done'):
        st.balloons()
        st.success("Session Complete! Great work.")
        st.session_state['timer_done'] = False

else:
    st.title("Synapse AI Core")
    u_q = st.chat_input("Command...")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"): st.write(ask_synapse(u_q))
