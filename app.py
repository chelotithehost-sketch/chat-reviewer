import streamlit as st
import pandas as pd
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
    st.session_state.agents = {}

# --- ZIP PROCESSING & AUTO-DETECTION ---
def scan_zip_for_agents(uploaded_zip):
    detected_names = set()
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        for file_path in z.namelist():
            if file_path.endswith('.json'):
                with z.open(file_path) as f:
                    try:
                        data = json.load(f)
                        for msg in data.get("messages", []):
                            sender = msg.get("sender", {})
                            if sender.get("t") == "a": 
                                detected_names.add(sender.get("n"))
                    except: continue
    return [name for name in detected_names if name]

def get_agent_transcripts(uploaded_zip, target_name):
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
    full_text = "\n---\n".join(transcripts[:8]) 
    prompt = f"""
    You are a Quality Assurance Auditor. Analyze these customer support chats.
    Rate the agent on a scale of 1.0 to 5.0 based on:
    1. Timing (Response speed)
    2. Tone (Professionalism)
    3. Language & Grammar
    4. Empathy / Listening
    5. Endings (Closing the chat)
    6. Escalations (Handling difficult queries)
    Return ONLY a JSON object.
    Example: {{"Timing": 4.2, "Tone": 4.8, "Language & Grammar": 4.5, "Empathy / Listening": 4.0, "Endings": 4.0, "Escalations": 5.0}}
    Chats: {full_text}
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except: return None

# --- EXPORT LOGIC ---
def export_to_excel(agent, template_path="template.xlsx"):
    if not os.path.exists(template_path): return None
    wb = load_workbook(template_path)
    ws = wb.active
    # Mapping to your template (B24-B35)
    ws['B24'] = agent["csat_areas"]["Timing"]
    ws['B25'] = agent["csat_areas"]["Tone"]
    ws['B26'] = agent["csat_areas"]["Language & Grammar"]
    ws['B27'] = agent["csat_areas"]["Empathy / Listening"]
    ws['B28'] = agent["csat_areas"]["Endings"]
    ws['B29'] = agent["csat_areas"]["Escalations"]
    ws['B32'] = agent["kpis"]["Communication Skills"]
    ws['B33'] = agent["kpis"]["Productivity"]
    ws['B34'] = agent["kpis"]["Quality of Support"]
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

# --- SIDEBAR ---
st.sidebar.title("👥 Team Management")
zip_for_names = st.sidebar.file_uploader("Upload ZIP to find names", type="zip", key="namer")
if zip_for_names and st.sidebar.button("Scan ZIP for Agents"):
    found = scan_zip_for_agents(zip_for_names)
    for name in found:
        if name not in st.session_state.agents:
            st.session_state.agents[name] = get_initial_agent(name)
    st.sidebar.success(f"Detected: {', '.join(found)}")

manual_name = st.sidebar.text_input("Add Agent Manually")
if st.sidebar.button("➕ Add"):
    if manual_name: st.session_state.agents[manual_name] = get_initial_agent(manual_name)

agent_list = list(st.session_state.agents.keys())
if agent_list:
    selected_name = st.sidebar.selectbox("Select Agent", agent_list)
    if st.sidebar.button(f"🗑️ Remove {selected_name}"):
        del st.session_state.agents[selected_name]
        st.rerun()
    current_agent = st.session_state.agents[selected_name]
else:
    st.warning("Please add or scan for agents.")
    st.stop()

# --- MAIN DASHBOARD ---
st.title(f"Performance Review: {selected_name}")
tab1, tab2 = st.tabs(["🤖 AI Quality Audit", "📈 Results & Excel Export"])

with tab1:
    data_zip = st.file_uploader("Upload Chat ZIP", type="zip", key="data_loader")
    if data_zip and st.button(f"Analyze Chats for {selected_name}"):
        with st.spinner("Gemini is auditing conversations..."):
            texts = get_agent_transcripts(data_zip, selected_name)
            if texts:
                results = run_gemini_audit(texts)
                if results:
                    current_agent["csat_areas"].update(results)
                    st.success(f"Audit complete! {len(texts)} chats analyzed.")
                else: st.error("AI analysis failed.")
            else: st.warning("No chats found.")

with tab2:
    cols = st.columns(2)
    with cols[0]:
        st.subheader("CSAT Metrics (1-5)")
        for area, val in current_agent["csat_areas"].items():
            current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, float(val), 0.1)
    with cols[1]:
        st.subheader("KPIs (1-10)")
        for kpi, val in current_agent["kpis"].items():
            current_agent["kpis"][kpi] = st.slider(kpi, 0.0, 10.0, float(val), 0.5)

    if st.button("Generate Performance Excel"):
        report = export_to_excel(current_agent)
        if report:
            st.download_button("📥 Download Report", report, f"{selected_name}_Review.xlsx")
        else: st.error("template.xlsx not found in directory.")
