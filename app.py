import streamlit as st
import pandas as pd
from openpyxl import load_workbook
import io
import os
import google.generativeai as genai
import json
import zipfile

# --- CONFIGURATION ---
st.set_page_config(page_title="Tawk.to ZIP Performance Review", layout="wide")

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- PROCESSING LOGIC ---
def process_zip(uploaded_zip, target_agent):
    """Recursively finds and reads all JSON files inside a tawk.to ZIP export."""
    all_chats = []
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        # Loop through every file in the ZIP, regardless of folder depth
        for file_path in z.namelist():
            if file_path.endswith('.json'):
                with z.open(file_path) as f:
                    try:
                        data = json.load(f)
                        # Tawk.to JSON structure check
                        # We filter for the specific agent name in the messages or metadata
                        is_agent_chat = False
                        
                        # Check metadata for agent name
                        if "sender" in data and data["sender"].get("n") == target_agent:
                            is_agent_chat = True
                        
                        # Check messages if metadata doesn't confirm
                        if not is_agent_chat:
                            for msg in data.get("messages", []):
                                if msg.get("sender", {}).get("n") == target_agent:
                                    is_agent_chat = True
                                    break
                        
                        if is_agent_chat:
                            # Extract the message text for AI analysis
                            transcript = ""
                            for m in data.get("messages", []):
                                name = m.get("sender", {}).get("n", "Visitor")
                                text = m.get("msg", "")
                                transcript += f"{name}: {text}\n"
                            
                            all_chats.append({
                                "id": data.get("id"),
                                "transcript": transcript,
                                "date": data.get("createdOn")
                            })
                    except Exception as e:
                        continue
    return all_chats

def run_ai_audit(transcripts):
    """Sends combined chat transcripts to Gemini for scoring."""
    prompt = f"""
    Analyze these customer support chats. Rate the agent (1.0 to 5.0) for:
    Timing, Tone, Language & Grammar, Empathy / Listening, Endings, Escalations.
    Return ONLY a JSON object.
    
    Chats:
    {transcripts}
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except:
        return None

# --- INITIAL STATE & UI ---
if 'agents' not in st.session_state:
    st.session_state.agents = [{"name": "Athira", "total_chats": 0, "csat_areas": {k: 0.0 for k in ["Timing", "Tone", "Language & Grammar", "Empathy / Listening", "Endings", "Escalations"]}, "kpis": {k: 0.0 for k in ["Communication Skills", "Productivity", "Quality of Support"]}}]

# Sidebar management (Add/Remove)
st.sidebar.title("Team Management")
selected_name = st.sidebar.selectbox("Agent", [a["name"] for a in st.session_state.agents])
current_agent = next(a for a in st.session_state.agents if a["name"] == selected_name)

# --- MAIN TABS ---
tab1, tab2 = st.tabs(["AI Audit (Upload ZIP)", "Manual Adjustment & Export"])

with tab1:
    st.header(f"Analyze ZIP Export for {current_agent['name']}")
    uploaded_file = st.file_uploader("Upload tawk.to ZIP Folder", type="zip")
    
    if uploaded_file:
        with st.spinner("Scanning ZIP folders (Year/Month/Day)..."):
            chats = process_zip(uploaded_file, current_agent["name"])
            current_agent["total_chats"] = len(chats)
            
            if chats:
                st.success(f"Found {len(chats)} chats for {current_agent['name']}!")
                if st.button("🤖 Run Gemini AI Audit"):
                    # Combine transcripts (first 5 for speed/token limits)
                    combined_text = "\n---\n".join([c['transcript'] for c in chats[:5]])
                    results = run_ai_audit(combined_text)
                    if results:
                        current_agent["csat_areas"].update(results)
                        st.success("Scores updated!")
            else:
                st.warning(f"No chats found for agent '{current_agent['name']}' in this ZIP.")

with tab2:
    # (Sliders and Excel export logic same as previous version)
    st.write("Review and download results here...")
