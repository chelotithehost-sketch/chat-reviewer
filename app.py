import streamlit as st
import pandas as pd
from openpyxl import load_workbook
import io
import os
import google.generativeai as genai
import json
import zipfile

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Agent Auditor - Final Fix", layout="wide")

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # FIX: We use just the model name. The SDK handles the 'models/' prefix internally.
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- DATA STRUCTURES ---
def get_initial_agent(name=""):
    return {
        "name": name,
        "total_chats": 0,
        "csat_areas": {
            "Timing": 0.0, "Tone": 0.0, "Language & Grammar": 0.0,
            "Empathy / Listening": 0.0, "Endings": 0.0, "Escalations": 0.0
        },
        "kpis": {
            "Communication Skills": 0.0, "Productivity": 0.0, "Quality of Support": 0.0
        }
    }

if 'agents' not in st.session_state:
    st.session_state.agents = {}

# --- RECURSIVE ZIP PROCESSING ---
def get_agent_transcripts(uploaded_zip, target_name, debug=False):
    transcripts = []
    debug_log = []
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        for file_path in z.namelist():
            if file_path.endswith('.json'):
                if debug: debug_log.append(f"Found JSON: {file_path}")
                with z.open(file_path) as f:
                    try:
                        data = json.load(f)
                        chat_text = ""
                        belongs_to_agent = False
                        # Extract messages based on your specific JSON format
                        for msg in data.get("messages", []):
                            name = msg.get("sender", {}).get("n", "Visitor")
                            body = msg.get("msg", "")
                            chat_text += f"{name}: {body}\n"
                            if name == target_name: belongs_to_agent = True
                        if belongs_to_agent:
                            transcripts.append(chat_text)
                            if debug: debug_log.append(f"✅ Matched agent '{target_name}'")
                    except: continue
    return transcripts, debug_log

# --- AI AUDIT LOGIC ---
def run_gemini_audit(transcripts):
    # Take a sample of 5 chats to stay within token limits
    sample = "\n---\n".join(transcripts[:5])
    prompt = f"""
    You are a QA Auditor. Rate this agent (1.0 to 5.0) for:
    Timing, Tone, Language & Grammar, Empathy / Listening, Endings, Escalations.
    Return ONLY a JSON object like this:
    {{"Timing": 4.0, "Tone": 4.5, "Language & Grammar": 5.0, "Empathy / Listening": 3.5, "Endings": 4.0, "Escalations": 4.0}}
    Chats:
    {sample}
    """
    try:
        response = model.generate_content(prompt)
        # Clean potential markdown wrapping
        text = response.text
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text: text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- UI LOGIC ---
st.sidebar.title("Team Management")
debug_mode = st.sidebar.checkbox("🐞 Enable Debug Mode")
manual_name = st.sidebar.text_input("Add Agent Name")
if st.sidebar.button("➕ Add"):
    if manual_name: st.session_state.agents[manual_name] = get_initial_agent(manual_name)

agent_list = list(st.session_state.agents.keys())
if not agent_list:
    st.warning("Add an agent to start.")
    st.stop()

selected_name = st.sidebar.selectbox("Agent:", agent_list)
current_agent = st.session_state.agents[selected_name]

st.title(f"Review: {selected_name}")
tab1, tab2 = st.tabs(["🤖 AI Audit", "📈 Results"])

with tab1:
    data_zip = st.file_uploader("Upload Chat ZIP", type="zip")
    if data_zip and st.button("Run Audit"):
        with st.spinner("AI is analyzing..."):
            texts, logs = get_agent_transcripts(data_zip, selected_name, debug=debug_mode)
            if debug_mode:
                with st.expander("Logs"):
                    for l in logs: st.text(l)
            if texts:
                results = run_gemini_audit(texts)
                if results:
                    current_agent["csat_areas"].update(results)
                    st.success("Audit successful!")
            else: st.error("No chats found.")

with tab2:
    for area, val in current_agent["csat_areas"].items():
        current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, float(val))
    # Add Export logic as before...
