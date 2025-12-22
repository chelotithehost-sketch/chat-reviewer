import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openpyxl import load_workbook
import io
import os
import google.generativeai as genai
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Team Performance Review", layout="wide")

# --- GEMINI AI SETUP ---
# You will set this key in Streamlit Cloud Secrets or local environment
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- INITIAL STATE ---
def get_initial_agent(name=""):
    return {
        "name": name,
        "period": "Oct 1, 2025 - Dec 22, 2025",
        "total_chats": 0,
        "csat_areas": {
            "Timing": 0.0, "Tone": 0.0, "Language & Grammar": 0.0,
            "Empathy / Listening": 0.0, "Endings": 0.0, "Escalations": 0.0
        },
        "kpis": {
            "Communication Skills": 0.0, "Productivity": 0.0, "Quality of Support": 0.0
        },
        "chat_breakdown": {"negative": 0, "positive": 0, "neutral": 0}
    }

if 'agents' not in st.session_state:
    st.session_state.agents = [get_initial_agent("Athira")]

# --- LOGIC FUNCTIONS ---
def calculate_score(agent):
    csat_score = sum(agent["csat_areas"].values())
    csat_max = len(agent["csat_areas"]) * 5
    kpi_score = sum(agent["kpis"].values())
    kpi_max = len(agent["kpis"]) * 10
    csat_perc = (csat_score / csat_max * 100) if csat_max > 0 else 0
    kpi_perc = (kpi_score / kpi_max * 100) if kpi_max > 0 else 0
    return round((csat_perc + kpi_perc) / 2, 1)

def get_grade(score):
    if score >= 90: return "A", "green"
    if score >= 80: return "B", "blue"
    if score >= 70: return "C", "orange"
    return "F", "red"

def run_ai_audit(chat_data):
    """Sends chat transcripts to Gemini and parses the scores."""
    prompt = f"""
    Analyze these customer support chats. Rate the agent on a scale of 1.0 to 5.0 for:
    Timing, Tone, Language & Grammar, Empathy / Listening, Endings, Escalations.
    
    Return ONLY a valid JSON object. Example:
    {{"Timing": 4.5, "Tone": 4.0, "Language & Grammar": 5.0, "Empathy / Listening": 4.0, "Endings": 4.5, "Escalations": 5.0}}

    Chats:
    {chat_data}
    """
    try:
        response = model.generate_content(prompt)
        # Clean up response text in case Gemini adds markdown code blocks
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"AI Audit Failed: {e}")
        return None

def export_to_excel(agent_data, template_path="template.xlsx"):
    if not os.path.exists(template_path): return None
    wb = load_workbook(template_path)
    ws = wb.active
    # Cell Mapping
    ws['B24'], ws['B25'], ws['B26'] = agent_data['csat_areas']['Timing'], agent_data['csat_areas']['Tone'], agent_data['csat_areas']['Language & Grammar']
    ws['B27'], ws['B28'], ws['B29'] = agent_data['csat_areas']['Empathy / Listening'], agent_data['csat_areas']['Endings'], agent_data['csat_areas']['Escalations']
    ws['B32'], ws['B33'], ws['B34'] = agent_data['kpis']['Communication Skills'], agent_data['kpis']['Productivity'], agent_data['kpis']['Quality of Support']
    ws['B35'] = f"{calculate_score(agent_data)}%"
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

# --- SIDEBAR ---
st.sidebar.title("Team Management")
new_name = st.sidebar.text_input("New Agent Name")
if st.sidebar.button("➕ Add Agent", use_container_width=True):
    if new_name:
        st.session_state.agents.append(get_initial_agent(new_name))
        st.rerun()

agent_names = [a["name"] for a in st.session_state.agents]
selected_name = st.sidebar.selectbox("Current Agent", agent_names)
current_agent = next(a for a in st.session_state.agents if a["name"] == selected_name)

if len(st.session_state.agents) > 1:
    if st.sidebar.button(f"🗑️ Remove {selected_name}", type="secondary"):
        st.session_state.agents = [a for a in st.session_state.agents if a["name"] != selected_name]
        st.rerun()

# --- MAIN UI ---
score = calculate_score(current_agent)
grade, color = get_grade(score)
st.title(f"🚀 {current_agent['name']}'s Performance")

col1, col2, col3 = st.columns(3)
col1.metric("Total Chats", current_agent["total_chats"])
col2.metric("Overall Score", f"{score}%")
col3.markdown(f"### Grade: :{color}[{grade}]")

tab1, tab2, tab3 = st.tabs(["Manual Scoring", "AI Quality Audit (Batch CSV)", "Excel Export"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        for area in current_agent["csat_areas"]:
            current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, current_agent["csat_areas"][area], 0.5)
    with c2:
        for kpi in current_agent["kpis"]:
            current_agent["kpis"][kpi] = st.slider(kpi, 0.0, 10.0, current_agent["kpis"][kpi], 0.5)

with tab2:
    st.info("Upload CSVs to calculate volume and run AI analysis on transcripts.")
    files = st.file_uploader("Upload CSVs", type="csv", accept_multiple_files=True)
    if files:
        df = pd.concat([pd.read_csv(f) for f in files])
        agent_col = next((c for c in df.columns if c in ['Agent', 'Assignee']), None)
        text_col = next((c for c in df.columns if c in ['Messages', 'Transcript', 'Body', 'Text']), None)
        
        if agent_col:
            agent_chats = df[df[agent_col] == current_agent["name"]]
            current_agent["total_chats"] = len(agent_chats)
            st.success(f"Found {len(agent_chats)} chats for {current_agent['name']}.")
            
            if text_col and GEMINI_API_KEY:
                if st.button("🤖 Run AI Analysis on Transcripts"):
                    with st.spinner("Gemini is auditing chats..."):
                        # Sample first 5 chats to avoid token limits
                        sample_text = "\n---\n".join(agent_chats[text_col].astype(str).head(5))
                        results = run_ai_audit(sample_text)
                        if results:
                            for area, val in results.items():
                                if area in current_agent["csat_areas"]:
                                    current_agent["csat_areas"][area] = val
                            st.success("Scores updated based on AI feedback!")
                            st.rerun()
            elif not text_col:
                st.warning("No transcript column found for AI analysis.")

with tab3:
    if st.button("Generate Excel Report"):
        data = export_to_excel(current_agent)
        if data:
            st.download_button("📥 Download Report", data, f"{current_agent['name']}_Review.xlsx")
        else:
            st.error("template.xlsx not found.")
