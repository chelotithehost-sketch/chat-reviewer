import streamlit as st
import pandas as pd
from openpyxl import load_workbook
import io
import os
import google.generativeai as genai
import json
import zipfile

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Agent Auditor - Comprehensive Mode", layout="wide")

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

# --- DATA STRUCTURES ---
def get_initial_agent(name=""):
    return {
        "name": name,
        "total_chats": 0,
        "overall_score": 0.0,
        "summary": "",
        "improvements": "",
        "csat_areas": {
            "Timing": 0.0, "Tone": 0.0, "Language & Grammar": 0.0,
            "Empathy / Listening": 0.0, "Endings": 0.0, "Escalations": 0.0
        }
    }

if 'agents' not in st.session_state:
    st.session_state.agents = {}

# --- RECURSIVE ZIP PROCESSING ---
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
                            name = msg.get("sender", {}).get("n", "Visitor")
                            body = msg.get("msg", "")
                            chat_text += f"{name}: {body}\n"
                            if name == target_name: belongs_to_agent = True
                        if belongs_to_agent:
                            transcripts.append(chat_text)
                    except: continue
    return transcripts

# --- AI AUDIT LOGIC ---
def run_comprehensive_audit(transcripts):
    # Sample up to 10 chats to provide deep context to the AI
    sample = "\n---\n".join(transcripts[:10])
    
    prompt = f"""
    You are a Senior QA Auditor. Analyze these customer support chats.
    
    TASK 1: Provide an Overall Score out of 10.
    TASK 2: Rate the agent (1.0 to 5.0) for: Timing, Tone, Language & Grammar, Empathy, Endings, Escalations.
    TASK 3: Generate a "Summary of 20 Chat Examples" based on the patterns found in these transcripts. 
    TASK 4: Suggest specific areas for improvement.

    Return ONLY a JSON object with this structure:
    {{
        "overall_score": 8.5,
        "metrics": {{"Timing": 4.0, "Tone": 4.5, "Language & Grammar": 5.0, "Empathy / Listening": 4.0, "Endings": 4.0, "Escalations": 4.0}},
        "summary_of_20": "1. [Brief Summary] - Improvement: [Suggestion]\\n2. [Brief Summary]...",
        "improvement_suggestions": "Point 1... Point 2..."
    }}

    Chats:
    {sample}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text: text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- UI ---
st.sidebar.title("Team Management")
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
tab1, tab2 = st.tabs(["🤖 AI Audit", "📈 Results & Insights"])

with tab1:
    data_zip = st.file_uploader("Upload Chat ZIP", type="zip")
    if data_zip and st.button("Run Comprehensive Audit"):
        with st.spinner("AI is analyzing chats and generating 20 examples..."):
            texts = get_agent_transcripts(data_zip, selected_name)
            if texts:
                results = run_comprehensive_audit(texts)
                if results:
                    current_agent["csat_areas"].update(results["metrics"])
                    current_agent["overall_score"] = results["overall_score"]
                    current_agent["summary"] = results["summary_of_20"]
                    current_agent["improvements"] = results["improvement_suggestions"]
                    current_agent["total_chats"] = len(texts)
                    st.success("Analysis Complete!")
            else: st.error("No chats found for this agent.")

with tab2:
    st.header(f"Overall Rating: {current_agent['overall_score']}/10")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Performance Metrics")
        for area, val in current_agent["csat_areas"].items():
            current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, float(val))
    
    with col2:
        st.subheader("Key Improvements")
        st.write(current_agent["improvements"])

    st.divider()
    st.subheader("Summary of 20 Chat Examples & Specific Suggestions")
    st.info(current_agent["summary"])
