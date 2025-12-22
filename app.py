import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openpyxl import load_workbook
import io
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Team Performance Review", layout="wide")

# --- INITIAL STATE & LOGIC ---
def get_initial_agent(name=""):
    """Creates a fresh agent dictionary based on the original JSX structure."""
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
        "chat_breakdown": {
            "negative": 0, "positive": 0, "neutral": 0, "avg_duration": "0:00"
        }
    }

if 'agents' not in st.session_state:
    # Start with a default agent
    st.session_state.agents = [get_initial_agent("Athira")]
    st.session_state.agents[0]["total_chats"] = 40

def calculate_score(agent):
    """Calculates a weighted percentage score (Average of CSAT % and KPI %)."""
    csat_score = sum(agent["csat_areas"].values())
    csat_max = len(agent["csat_areas"]) * 5
    kpi_score = sum(agent["kpis"].values())
    kpi_max = len(agent["kpis"]) * 10
    
    csat_perc = (csat_score / csat_max * 100) if csat_max > 0 else 0
    kpi_perc = (kpi_score / kpi_max * 100) if kpi_max > 0 else 0
    return round((csat_perc + kpi_perc) / 2, 1)

def get_grade(score):
    """Determines the letter grade based on the score."""
    if score >= 90: return "A", "green"
    if score >= 80: return "B", "blue"
    if score >= 70: return "C", "orange"
    if score >= 60: return "D", "red"
    return "F", "grey"

def export_to_excel(agent_data, template_path="template.xlsx"):
    """Maps app data directly to specific Excel cells from your screenshots."""
    if not os.path.exists(template_path):
        return None
    
    wb = load_workbook(template_path)
    ws = wb.active

    # Mapping to Column B based on your image (Rows 24-29 for CSAT, 32-34 for KPIs)
    ws['B24'] = agent_data['csat_areas']['Timing']
    ws['B25'] = agent_data['csat_areas']['Tone']
    ws['B26'] = agent_data['csat_areas']['Language & Grammar']
    ws['B27'] = agent_data['csat_areas']['Empathy / Listening']
    ws['B28'] = agent_data['csat_areas']['Endings']
    ws['B29'] = agent_data['csat_areas']['Escalations']

    ws['B32'] = agent_data['kpis']['Communication Skills']
    ws['B33'] = agent_data['kpis']['Productivity']
    ws['B34'] = agent_data['kpis']['Quality of Support']

    # Final Overall Score
    ws['B35'] = f"{calculate_score(agent_data)}%"

    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()

# --- SIDEBAR: AGENT MANAGEMENT ---
st.sidebar.title("Team Management")

# Add Agent
new_name = st.sidebar.text_input("New Agent Name")
if st.sidebar.button("➕ Add Agent", use_container_width=True):
    if new_name and new_name not in [a["name"] for a in st.session_state.agents]:
        st.session_state.agents.append(get_initial_agent(new_name))
        st.rerun()

st.sidebar.markdown("---")

# Select Agent
agent_names = [a["name"] for a in st.session_state.agents]
selected_name = st.sidebar.selectbox("Current Agent", agent_names)
agent_idx = agent_names.index(selected_name)
current_agent = st.session_state.agents[agent_idx]

# Remove Agent (Original Logic: Only if > 1 remains)
if len(st.session_state.agents) > 1:
    if st.sidebar.button(f"🗑️ Remove {selected_name}", type="secondary", use_container_width=True):
        st.session_state.agents.pop(agent_idx)
        st.rerun()

# --- MAIN DASHBOARD ---
score = calculate_score(current_agent)
grade, color = get_grade(score)

st.title(f"📊 {current_agent['name']}'s Performance")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Chats", current_agent["total_chats"])
col2.metric("Overall Score", f"{score}%")
col3.markdown(f"### Grade: :{color}[{grade}]")
col4.write(f"Period: {current_agent['period']}")

tab1, tab2, tab3 = st.tabs(["Edit Scores", "Batch Upload CSV", "Excel Export"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("CSAT Areas (1-5)")
        for area in current_agent["csat_areas"]:
            current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, current_agent["csat_areas"][area], 0.5)
    with c2:
        st.subheader("KPIs (1-10)")
        for kpi in current_agent["kpis"]:
            current_agent["kpis"][kpi] = st.slider(kpi, 0.0, 10.0, current_agent["kpis"][kpi], 0.5)

with tab2:
    st.info("Upload multiple CSVs from Tawk.to to merge chat counts for this agent.")
    uploaded_files = st.file_uploader("Select CSV Files", type="csv", accept_multiple_files=True)
    if uploaded_files:
        # Batch processing logic
        all_dfs = [pd.read_csv(f) for f in uploaded_files]
        combined = pd.concat(all_dfs)
        agent_col = next((c for c in combined.columns if c in ['Agent', 'Assignee']), None)
        if agent_col:
            count = len(combined[combined[agent_col] == current_agent["name"]])
            current_agent["total_chats"] = count
            st.success(f"Merged {len(uploaded_files)} files. Found {count} chats for {current_agent['name']}.")

with tab3:
    st.subheader("Download to Excel")
    if st.button("Generate Filled Report"):
        excel_data = export_to_excel(current_agent)
        if excel_data:
            st.download_button("📥 Download Excel File", excel_data, f"{current_agent['name']}_Review.xlsx")
        else:
            st.error("Missing 'template.xlsx' in GitHub folder!")
