import streamlit as st
import pandas as pd
from openpyxl import load_workbook
import io
import os
import google.generativeai as genai
import json
import zipfile

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Agent Auditor - Deep Scan Mode", layout="wide")

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Changed from 'models/gemini-1.5-flash' to just 'gemini-1.5-flash'
    # The SDK handles the prefixing automatically.
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
    """Recursively finds JSONs in Year/Month/Day folders and extracts transcripts."""
    transcripts = []
    debug_log = []
    
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        all_files = z.namelist()
        
        for file_path in all_files:
            if file_path.endswith('.json'):
                if debug: debug_log.append(f"Found JSON: {file_path}")
                
                with z.open(file_path) as f:
                    try:
                        data = json.load(f)
                        chat_text = ""
                        belongs_to_agent = False
                        
                        # Extract messages from the 'messages' list
                        for msg in data.get("messages", []):
                            sender_data = msg.get("sender", {})
                            name = sender_data.get("n", "Visitor") #
                            message_body = msg.get("msg", "") #
                            
                            chat_text += f"{name}: {message_body}\n"
                            
                            if name == target_name:
                                belongs_to_agent = True
                        
                        if belongs_to_agent:
                            transcripts.append(chat_text)
                            if debug: debug_log.append(f"✅ Matched agent '{target_name}' in this file.")
                    except Exception as e:
                        if debug: debug_log.append(f"❌ Error reading {file_path}: {e}")
                        continue
                        
    return transcripts, debug_log

# --- AI AUDIT LOGIC ---
def run_gemini_audit(transcripts):
    """Sends transcripts to Gemini to determine 1-5 scores."""
    # Sampling 5 chats to stay safe within prompt limits
    full_text = "\n---\n".join(transcripts[:5]) 
    prompt = f"""
    You are a Quality Assurance Auditor. Analyze the following customer support chats.
    Rate the agent's performance on a scale of 1.0 to 5.0 for these metrics:
    1. Timing (Response speed & delay)
    2. Tone (Professionalism & friendliness)
    3. Language & Grammar (Accuracy)
    4. Empathy / Listening (Acknowledging concerns)
    5. Endings (Closing with help offered)
    6. Escalations (Handling transfers or difficult tech)

    Return ONLY a valid JSON object. Example:
    {{"Timing": 4.0, "Tone": 5.0, "Language & Grammar": 4.5, "Empathy / Listening": 4.0, "Endings": 4.0, "Escalations": 5.0}}

    Chats:
    {full_text}
    """
    try:
        # Ensuring we call generate_content correctly
        response = model.generate_content(prompt)
        
        # Clean potential markdown from AI response
        response_text = response.text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
            
        return json.loads(response_text.strip())
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return None

# --- EXPORT LOGIC ---
def export_to_excel(agent, template_path="template.xlsx"):
    if not os.path.exists(template_path): return None
    wb = load_workbook(template_path)
    ws = wb.active
    ws['B24'], ws['B25'], ws['B26'] = agent["csat_areas"]["Timing"], agent["csat_areas"]["Tone"], agent["csat_areas"]["Language & Grammar"]
    ws['B27'], ws['B28'], ws['B29'] = agent["csat_areas"]["Empathy / Listening"], agent["csat_areas"]["Endings"], agent["csat_areas"]["Escalations"]
    ws['B32'], ws['B33'], ws['B34'] = agent["kpis"]["Communication Skills"], agent["kpis"]["Productivity"], agent["kpis"]["Quality of Support"]
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

# --- SIDEBAR ---
st.sidebar.title("👥 Team Management")
debug_mode = st.sidebar.checkbox("🐞 Enable Debug Mode")

manual_name = st.sidebar.text_input("Add Agent Name")
if st.sidebar.button("➕ Add Agent"):
    if manual_name: st.session_state.agents[manual_name] = get_initial_agent(manual_name)

agent_list = list(st.session_state.agents.keys())
if agent_list:
    selected_name = st.sidebar.selectbox("Reviewing:", agent_list)
    current_agent = st.session_state.agents[selected_name]
else:
    st.warning("Please add an agent in the sidebar.")
    st.stop()

# --- MAIN UI ---
st.title(f"Performance Review: {selected_name}")
tab1, tab2 = st.tabs(["🤖 AI Quality Audit", "📈 Final Scores & Export"])

with tab1:
    st.info("Upload the tawk.to ZIP. The AI will recursively search all subfolders.")
    data_zip = st.file_uploader("Upload ZIP File", type="zip")
    
    if data_zip:
        if st.button(f"🔍 Audit {selected_name}"):
            with st.spinner(f"Scanning deep folders for {selected_name}..."):
                texts, logs = get_agent_transcripts(data_zip, selected_name, debug=debug_mode)
                
                if debug_mode:
                    with st.expander("🐞 View Debug Log"):
                        for line in logs: st.text(line)
                
                if texts:
                    results = run_gemini_audit(texts)
                    if results:
                        current_agent["csat_areas"].update(results)
                        current_agent["total_chats"] = len(texts)
                        st.success(f"Audit Complete! Analyzed {len(texts)} chats.")
                    else:
                        st.error("AI analysis failed to return a valid result.")
                else:
                    st.error(f"No chats found for '{selected_name}'.")

with tab2:
    st.subheader("Adjusted Scores")
    c1, c2 = st.columns(2)
    with c1:
        for area in current_agent["csat_areas"]:
            current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, float(current_agent["csat_areas"][area]), 0.1)
    with c2:
        for kpi in current_agent["kpis"]:
            current_agent["kpis"][kpi] = st.slider(kpi, 0.0, 10.0, float(current_agent["kpis"][kpi]), 0.5)

    if st.button("📥 Download Final Excel Report"):
        report = export_to_excel(current_agent)
        if report:
            st.download_button("Click to Download", report, f"{selected_name}_Review.xlsx")
        else:
            st.error("template.xlsx not found.")
