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
    .stMetric, div[data-testid="stExpander"], .stTabs [data-baseweb="tab-panel"], [data-testid="stChatMessage"] {
        background: #ffffff !important; border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important; color: #1e293b !important; padding: 18px;
    }
    div.stButton > button {
        background-color: #10b981; color: white !important; font-weight: 600; border-radius: 6px; width: 100%;
    }
    div.stButton > button:hover { background-color: #059669 !important; }
    input, textarea { background-color: #ffffff !important; color: #1e293b !important; border: 1px solid #94a3b8 !important; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
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
            "messages": [{"role": "system", "content": "You are Synapse Pro AI. You analyze provided student notes and document metadata to create study aids."},
                         {"role": "user", "content": prompt}]
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return "SYSTEM NOTIFICATION: AI connection failed. Check HF_TOKEN in Secrets."

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("SYNAPSE PRO")
    search_query = st.text_input("SEARCH FOLDERS", "").lower()
    st.divider()
    page = st.radio("NAVIGATION", ["DASHBOARD", "SYNAPSE AI", "SUBJECT EXPLORER"])
    
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
        st.metric("NEURAL CAPACITY", f"{m_used}/960 MINS")
        st.progress(min(m_used / 960, 1.0))

        cursor.execute("SELECT type, SUM(minutes) FROM items WHERE item_date=? GROUP BY type", (sel_date,))
        chart_data = cursor.fetchall()
        if chart_data:
            df = pd.DataFrame(chart_data, columns=['Type', 'Minutes'])
            st.vega_lite_chart(df, {
                'mark': {'type': 'arc', 'innerRadius': 45},
                'encoding': {
                    'theta': {'field': 'Minutes', 'type': 'quantitative'},
                    'color': {'field': 'Type', 'type': 'nominal', 'scale': {'range': ['#10b981', '#0f172a']}},
                }
            }, use_container_width=True)
        
        with st.expander("SCHEDULE CLASS"):
            if subjects_list:
                c_sub = st.selectbox("SELECT SUBJECT", subjects_list)
                c_min = st.number_input("MINUTES", 15, 480, 60)
                if st.button("ADD CLASS"):
                    cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(c_sub,"Class",c_min,sel_date))
                    conn.commit(); st.rerun()

        with st.expander("LOG NEW TASK"):
            t_name = st.text_input("TASK DESCRIPTION")
            t_min = st.number_input("TASK MINS", 15, 300, 30)
            if st.button("SAVE TASK"):
                cursor.execute("INSERT INTO items(name,type,minutes,item_date) VALUES (?,?,?,?)",(t_name,"Task",t_min,sel_date))
                conn.commit(); st.rerun()

        st.divider()
        new_s = st.text_input("NEW FOLDER NAME")
        if st.button("CREATE SUBJECT"):
            if new_s:
                cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (new_s,))
                conn.commit(); st.rerun()

    with col2:
        st.subheader(f"TIMELINE: {sel_date}")
        cursor.execute("SELECT id, name, type, minutes, attended FROM items WHERE item_date=?", (sel_date,))
        for i_id, i_name, i_type, i_mins, i_att in cursor.fetchall():
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                prefix = "[CLASS]" if i_type == "Class" else "[TASK]"
                c1.write(f"**{prefix} {i_name}** ({i_mins}m)")
                if i_type == "Class":
                    if c2.checkbox("DONE", value=bool(i_att), key=f"c_{i_id}"):
                        cursor.execute("UPDATE items SET attended=1 WHERE id=?", (i_id,))
                        conn.commit(); st.rerun()
                if c3.button("DELETE", key=f"d_{i_id}"):
                    cursor.execute("DELETE FROM items WHERE id=?", (i_id,))
                    conn.commit(); st.rerun()

# --- 6. SYNAPSE AI ---
elif page == "SYNAPSE AI":
    st.title("Synapse AI Core")
    u_q = st.chat_input("Ask a general academic question...")
    if u_q:
        with st.chat_message("user"): st.write(u_q)
        with st.chat_message("assistant"): st.write(ask_synapse(u_q))

# --- 7. SUBJECT EXPLORER (COMPLETE ANALYSIS ENABLED) ---
elif page == "SUBJECT EXPLORER":
    st.title("Subject Archives")
    display_list = filtered_subs if search_query else subjects_list
    
    if display_list:
        choice = st.selectbox("ACTIVE WORKSPACE", display_list)
        cursor.execute("SELECT COUNT(*), SUM(attended) FROM items WHERE name=? AND type='Class'", (choice,))
        total, res_att = cursor.fetchone()
        att = res_att or 0
        score = 100 if total == 0 else round((att/total)*100, 1)
        st.metric("ATTENDANCE RATE", f"{score}%")
        
        tab1, tab2, tab3 = st.tabs(["MATERIALS", "AI STUDY TOOLS", "FOCUS TIMER"])
        
        with tab1:
            st.write(f"Upload media and log notes for **{choice}**")
            # Document Context
            uploaded_file = st.file_uploader("UPLOAD DOCUMENTS (PDF/TXT)", key=f"u_{choice}")
            # Note Context
            notes = st.text_area("SESSION NOTES", height=300, key=f"notes_{choice}")
            if notes:
                st.download_button("DOWNLOAD NOTES (.TXT)", notes, f"{choice}_notes.txt")

        with tab2:
            st.subheader("Complete Analysis Engine")
            
            # Checking if data exists
            has_notes = st.session_state.get(f"notes_{choice}")
            has_file = uploaded_file is not None
            
            if not has_notes and not has_file:
                st.warning("⚠️ No data found. Please upload a document or type notes in the 'MATERIALS' tab first.")
            else:
                tool = st.radio("SELECT PROTOCOL", ["Summary", "Quiz", "Flashcards"], horizontal=True)
                
                if st.button("RUN COMPLETE ANALYSIS"):
                    # Building the Contextual Prompt
                    file_info = f"Document: {uploaded_file.name}" if has_file else "No document uploaded"
                    note_info = f"Student Notes: {has_notes}" if has_notes else "No notes typed"
                    
                    full_prompt = f"""
                    Analyze all available media for the subject {choice}.
                    Context:
                    - {file_info}
                    - {note_info}
                    
                    Task: Generate a professional {tool} based on this combined knowledge.
                    """
                    
                    with st.spinner("Analyzing all subject media..."):
                        result = ask_synapse(full_prompt)
                        st.markdown("### Generated Result")
                        st.write(result)

        with tab3:
            mins = st.slider("FOCUS DURATION (MINS)", 1, 60, 25)
            if st.button("START SESSION"):
                t_secs = mins * 60
                t_disp = st.empty()
                p_bar = st.progress(0)
                for t in range(t_secs, -1, -1):
                    m, s = divmod(t, 60)
                    t_disp.header(f"TIMER: {m:02d}:{s:02d}")
                    p_bar.progress(1.0 - (t / t_secs))
                    time.sleep(1)
                st.snow()
    else: st.info("No folders detected.")
