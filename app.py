import streamlit as st
import pandas as pd
import io
import os
import google.generativeai as genai
import json
import zipfile

# --- CONFIGURATION ---
st.set_page_config(page_title="HostAfrica AI Auditor - Security Edition", layout="wide")

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # UPDATED: Use gemini-2.5-flash as requested
    model = genai.GenerativeModel('gemini-2.5-flash')

# --- DATA STRUCTURES ---
if 'agents' not in st.session_state:
    st.session_state.agents = {}

def get_initial_agent(name=""):
    return {
        "name": name,
        "audit_data": None,
        "total_chats": 0
    }

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
                        # Extracting transcript data based on tawk.to JSON structure
                        for msg in data.get("messages", []):
                            name = msg.get("sender", {}).get("n", "Visitor")
                            body = msg.get("msg", "")
                            chat_text += f"{name}: {body}\n"
                            if name == target_name: belongs_to_agent = True
                        if belongs_to_agent:
                            transcripts.append(chat_text)
                    except: continue
    return transcripts

# --- ENHANCED AI AUDIT LOGIC ---
def run_comprehensive_audit(transcripts):
    sample = "\n---\n".join(transcripts[:12])
    
    prompt = f"""
    You are a Senior Technical QA Auditor at HostAfrica. 
    Evaluate the agent ONLY. Ignore bots/automated messages.

    CRITICAL SCALING RULE:
    - All metrics MUST be between 0.0 and 5.0. 
    - overall_score MUST be between 0.0 and 10.0.

    EVALUATION FRAMEWORK:
    1. SECURITY & PIN VERIFICATION (Weight: 20%)
       - Verify if agent followed "Client Support PIN" protocols.
       - Check if agent asked for a PIN already provided (Redundancy).
    2. TECHNICAL CAPABILITY (Weight: 25%)
       - Accuracy for DNS, Email, SSL, WordPress.
       - Use of tools: Ping, Traceroute, WHOIS, cPanel.
    3. COMMUNICATION & EMPATHY (Weight: 15%)
    4. INVESTIGATIVE APPROACH (Weight: 20%)
    5. LIVECHAT OWNERSHIP (Weight: 20%)

    Return ONLY JSON:
    {{
        "overall_score": 0.0,
        "overall_assessment": "Summary text",
        "metrics": {{
            "security_pin_protocol": 0.0,
            "technical_capability": 0.0,
            "communication_clarity": 0.0,
            "investigative_approach": 0.0,
            "chat_ownership": 0.0
        }},
        "key_strengths": [],
        "key_development_areas": [],
        "pin_protocol_feedback": "Text",
        "technical_examples": [{{ "issue": "x", "agent_action": "y", "pin_handled_well": "Yes/No/Redundant", "improvement": "z" }}]
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
        st.error(f"AI Generation Error: {e}")
        return None

# --- UI DISPLAY ---
def display_results(audit_data):
    # Fix scaling in case AI hallucinated high numbers
    score = min(float(audit_data.get('overall_score', 0)), 10.0)
    st.markdown(f"## Overall Score: {score}/10")
    
    st.markdown("### 📋 Overall Assessment")
    st.info(audit_data.get("overall_assessment"))

    st.markdown("### 📊 Metrics (Out of 5.0)")
    m = audit_data.get("metrics", {})
    cols = st.columns(len(m))
    for i, (k, v) in enumerate(m.items()):
        # Ensure individual metrics don't exceed 5.0
        display_val = min(float(v), 5.0)
        cols[i].metric(k.replace("_", " ").title(), f"{display_val}/5.0")

    st.markdown("### 🔐 PIN Verification Analysis")
    st.warning(audit_data.get("pin_protocol_feedback"))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ✅ Strengths")
        for s in audit_data.get("key_strengths", []): st.success(s)
    with c2:
        st.markdown("### 🎯 Areas to Improve")
        for d in audit_data.get("key_development_areas", []): st.warning(d)

    st.markdown("### 🔧 Technical Examples")
    for ex in audit_data.get("technical_examples", []):
        with st.expander(f"Issue: {ex.get('issue', 'N/A')}"):
            st.write(f"**PIN Handled Well?** {ex.get('pin_handled_well')}")
            st.write(f"**Action:** {ex.get('agent_action')}")
            st.write(f"**Improvement:** {ex.get('improvement')}")

# --- APP FLOW ---
st.sidebar.title("HostAfrica Team")
m_name = st.sidebar.text_input("Agent Name")
if st.sidebar.button("➕ Add Agent"):
    if m_name and m_name not in st.session_state.agents:
        st.session_state.agents[m_name] = get_initial_agent(m_name)

agent_list = list(st.session_state.agents.keys())
if agent_list:
    sel_name = st.sidebar.selectbox("Select Agent:", agent_list)
    
    # AMMENDED: Restore Remove Agent option
    if st.sidebar.button(f"🗑️ Remove {sel_name}"):
        del st.session_state.agents[sel_name]
        st.rerun()

    agent = st.session_state.agents[sel_name]
    
    t1, t2 = st.tabs(["🤖 Audit Interface", "📈 Detailed Results"])
    
    with t1:
        st.subheader(f"Analyzing: {sel_name}")
        zip_file = st.file_uploader("Upload tawk.to ZIP", type="zip")
        
        if zip_file:
            # AMMENDED: Clear loading indication
            if st.button("Run Comprehensive Audit"):
                with st.spinner(f"AI is currently auditing {len(zip_file.name)} transcripts..."):
                    texts = get_agent_transcripts(zip_file, sel_name)
                    if texts:
                        res = run_comprehensive_audit(texts)
                        if res:
                            agent["audit_data"] = res
                            st.success("Analysis Complete! View the 'Detailed Results' tab.")
                    else:
                        st.error("No chats found for this agent in the uploaded file.")

    with t2:
        if agent["audit_data"]:
            display_results(agent["audit_data"])
        else:
            st.info("No audit data found. Please run an audit in the first tab.")
