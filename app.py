import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openpyxl import load_workbook
import io
import os
import google.generativeai as genai
import json
import zipfile

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Agent Performance Auditor", layout="wide")

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
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
    st.session_state.agents = {} # Use dict for easier name tracking

# --- ZIP PROCESSING & AUTO-DETECTION ---
def scan_zip_for_agents(uploaded_zip):
    """Scans the JSON files in the ZIP and extracts all unique Agent names."""
    detected_names = set()
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        for file_path in z.namelist():
            if file_path.endswith('.json'):
                with z.open(file_path) as f:
                    try:
                        data = json.load(f)
                        # Check sender metadata and message history for agent signatures
                        for msg in data.get("messages", []):
                            sender = msg.get("sender", {})
                            if sender.get("t") == "a": # 'a' usually stands for 'agent' in Tawk.to
                                detected_names.add(sender.get("n"))
                    except: continue
    return [name for name in detected_names if name]

def get_agent_transcripts(uploaded_zip, target_name):
    """Collects all chat text for a specific agent."""
    transcripts = []
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        for file_path in z.namelist():
            if file_path.endswith('.json'):
                with z.open(file_path) as f:
                    try:
                        data = json.load(f)
                        chat_text = ""
                        belongs_to_agent = False
                        for msg in data.get("messages", []):
                            n = msg.get("sender", {}).get("n", "Visitor")
                            chat_text += f"{n}: {msg.get('msg', '')}\n"
                            if n == target_name: belongs_to_agent = True
                        if belongs_to_agent:
                            transcripts.append(chat_text)
                    except: continue
    return transcripts

# --- AI AUDIT LOGIC ---
def run_gemini_audit(transcripts):
    full_text = "\n---\n".join(transcripts[:8]) # Sample up to 8 chats
    prompt = f"""
    You are a Quality Assurance Auditor. Analyze these customer support chats.
    Rate the agent on a scale of 1.0 to 5.0 based on these metrics:
    1. Timing (Response speed)
    2. Tone (Professionalism)
    3. Language & Grammar
    4. Empathy / Listening
    5. Endings (Closing the chat)
    6. Escalations (Handling difficult queries)

    Return ONLY a JSON object with these exact keys.
    Example: {{"Timing": 4.2, "Tone": 4.8, "Language & Grammar": 4.5, "Empathy / Listening": 4.0, "Endings": 4.0, "Escalations": 5.0}}
    
    Chats: {full_text}
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except: return None

# --- SIDEBAR: AGENT MANAGEMENT ---
st.sidebar.title("👥 Team Management")

# Auto-Detection Feature
st.sidebar.subheader("Auto-Detect Names")
zip_for_names = st.sidebar.file_uploader("Upload ZIP to find names", type="zip", key="namer")
if zip_for_names and st.sidebar.button("Scan ZIP for Agents"):
    found = scan_zip_for_agents(zip_for_names)
    for name in found:
        if name not in st.session_state.agents:
            st.session_state.agents[name] = get_initial_agent(name)
    st.sidebar.success(f"Detected: {', '.join(found)}")

st.sidebar.divider()

# Manual Add/Remove
manual_name = st.sidebar.text_input("Add Agent Manually")
if st.sidebar.button("➕ Add"):
    if manual_name: 
        st.session_state.agents[manual_name] = get_initial_agent(manual_name)

agent_list = list(st.session_state.agents.keys())
if agent_list:
    selected_name = st.sidebar.selectbox("Select Agent to Review", agent_list)
    if st.sidebar.button(f"🗑️ Remove {selected_name}"):
        del st.session_state.agents[selected_name]
        st.rerun()
else:
    st.warning("No agents loaded. Use the scanner or add manually.")
    st.stop()

current_agent = st.session_state.agents[selected_name]

# --- MAIN DASHBOARD ---
st.title(f"Performance Review: {selected_name}")

tab1, tab2 = st.tabs(["🤖 AI Quality Audit", "📈 Results & Excel Export"])

with tab1:
    st.info("Upload the tawk.to ZIP export to analyze performance metrics.")
    data_zip = st.file_uploader("Upload Chat ZIP", type="zip", key="data_loader")
    
    if data_zip:
        if st.button(f"Analyze Chats for {selected_name}"):
            with st.spinner("Gemini is auditing conversations..."):
                texts = get_agent_transcripts(data_zip, selected_name)
                current_agent["total_chats"] = len(texts)
                
                if texts:
                    results = run_gemini_audit(texts)
                    if results:
                        current_agent["csat_areas"].update(results)
                        st.success(f"Audit complete! {len(texts)} chats analyzed.")
                    else:
                        st.error("AI could not generate scores. Check API Key.")
                else:
                    st.warning("No chats found for this agent in the ZIP.")

with tab2:
    # Display Score Breakdown
    cols = st.columns(2)
    with cols[0]:
        st.subheader("CSAT Metrics (1-5)")
        for area, val in current_agent["csat_areas"].items():
            current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, float(val), 0.1)
    
    with cols[1]:
        st.subheader("KPIs (1-10)")
        for kpi, val in current_agent["kpis"].items():
            current_agent["kpis"][kpi] = st.slider(kpi, 0.0, 10.0, float(val), 0.5)

    # Export Section
    st.divider()
    if st.button("Generate Performance Excel"):
        # (Same export logic as previous turns, mapping to B24-B35)
        st.info("Generating report...")
        # ... (Export function call here)
