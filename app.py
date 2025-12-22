import streamlit as st
import pandas as pd
from openpyxl import load_workbook
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
    model = genai.GenerativeModel('gemini-2.5-flash') # Using the latest flash model

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
                        # Extract full chat history to see what the bot/client said before the agent joined
                        for msg in data.get("messages", []):
                            name = msg.get("sender", {}).get("n", "Visitor")
                            body = msg.get("msg", "")
                            chat_text += f"{name}: {body}\n"
                            if name == target_name: belongs_to_agent = True
                        if belongs_to_agent:
                            transcripts.append(chat_text)
                    except: continue
    return transcripts

# --- ENHANCED AI AUDIT LOGIC WITH PIN PROTOCOLS ---
def run_comprehensive_audit(transcripts):
    sample = "\n---\n".join(transcripts[:12])
    
    prompt = f"""
    You are a Senior Technical QA Auditor at HostAfrica. 
    Audit the agent's performance with a specific focus on Technical Skills and Security Protocols.

    CRITICAL EVALUATION FRAMEWORK:
    
    1. SECURITY & PIN VERIFICATION (Weight: 20%)
       - Verify if the agent followed "Client Support PIN" protocols.
       - PENALTY: Did the agent ask for a PIN that the client ALREADY provided to the bot/pre-chat form? (Redundancy friction).
       - PENALTY: Did the agent fail to ask for a PIN before performing account-specific actions? (Security risk).
    
    2. TECHNICAL CAPABILITY (Weight: 25%)
       - Accuracy for DNS, Email (IMAP/SMTP), SSL, WordPress.
       - Proper use of diagnostic tools (Ping, Traceroute, WHOIS, cPanel).
    
    3. COMMUNICATION & EMPATHY (Weight: 15%)
       - Ability to explain complex concepts simply.
       - Tone appropriateness.
    
    4. INVESTIGATIVE APPROACH (Weight: 20%)
       - Proactive server-side diagnostics before requesting client action.
       - Verifying root causes vs making assumptions.
    
    5. LIVECHAT OWNERSHIP (Weight: 20%)
       - Accountability and follow-through.
       - Providing updates during troubleshooting.

    EVALUATION REQUIREMENTS:
    ✓ Focus ONLY on the human agent.
    ✓ Identify specific examples where the agent correctly handled PIN verification vs where they were redundant.
    
    Return ONLY a JSON object:
    {{
        "overall_score": 0.0,
        "overall_assessment": "Summary of strengths/weaknesses",
        "metrics": {{
            "security_pin_protocol": 0.0,
            "technical_capability": 0.0,
            "communication_clarity": 0.0,
            "investigative_approach": 0.0,
            "chat_ownership": 0.0
        }},
        "key_strengths": ["Example of good skill"],
        "key_development_areas": ["Example of weakness and fix"],
        "pin_protocol_feedback": "Specific evaluation of how they handled Support PINs",
        "technical_examples": [{{ "issue": "x", "agent_action": "y", "pin_handled_well": "Yes/No/Redundant", "improvement": "a" }}],
        "training_recommendations": ["Area 1", "Area 2"]
    }}

    Analyze these interactions:
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
    st.markdown(f"## Overall Score: {audit_data['overall_score']}/10")
    
    st.markdown("### 📋 Overall Assessment")
    st.info(audit_data.get("overall_assessment"))

    st.markdown("### 📊 Metrics")
    m = audit_data.get("metrics", {})
    cols = st.columns(len(m))
    for i, (k, v) in enumerate(m.items()):
        cols[i].metric(k.replace("_", " ").title(), f"{v}/5.0")

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
        with st.expander(f"Issue: {ex['issue']}"):
            st.write(f"**PIN Handled Well?** {ex.get('pin_handled_well')}")
            st.write(f"**Action:** {ex['agent_action']}")
            st.write(f"**Suggested Improvement:** {ex['improvement']}")

# --- APP FLOW ---
st.sidebar.title("HostAfrica Team")
m_name = st.sidebar.text_input("Agent Name")
if st.sidebar.button("Add Agent"):
    if m_name: st.session_state.agents[m_name] = get_initial_agent(m_name)

agent_list = list(st.session_state.agents.keys())
if agent_list:
    sel_name = st.sidebar.selectbox("Reviewing:", agent_list)
    agent = st.session_state.agents[sel_name]
    
    t1, t2 = st.tabs(["Audit", "Results"])
    with t1:
        zip_file = st.file_uploader("Upload ZIP", type="zip")
        if zip_file and st.button("Run Security & Tech Audit"):
            texts = get_agent_transcripts(zip_file, sel_name)
            if texts:
                res = run_comprehensive_audit(texts)
                if res:
                    agent["audit_data"] = res
                    st.success("Audit Done!")
    with t2:
        if agent["audit_data"]: display_results(agent["audit_data"])
