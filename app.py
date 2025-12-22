import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openpyxl import load_workbook
import io
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Team Performance Review", layout="wide")

# --- INITIAL STATE ---
def get_initial_agent(name=""):
    return {
        "name": name,
        "period": "Oct 1, 2025 - Dec 22, 2025",
        "total_chats": 0,
        "csat_areas": {
            "Timing": 0.0,
            "Tone": 0.0,
            "Language & Grammar": 0.0,
            "Empathy / Listening": 0.0,
            "Endings": 0.0,
            "Escalations": 0.0
        },
        "kpis": {
            "Communication Skills": 0.0,
            "Productivity": 0.0,
            "Quality of Support": 0.0
        },
        "chat_breakdown": {
            "negative": 0,
            "positive": 0,
            "neutral": 0,
            "avg_duration": "0:00"
        }
    }

if 'agents' not in st.session_state:
    st.session_state.agents = [get_initial_agent("Athira")]
    st.session_state.agents[0]["total_chats"] = 40

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

def export_to_excel(agent_data, template_path="template.xlsx"):
    if not os.path.exists(template_path):
        return None
    
    wb = load_workbook(template_path)
    ws = wb.active

    # Mapping based on your provided screenshot
    # CSAT Areas (Row 24-29)
    ws['B24'] = agent_data['csat_areas']['Timing']
    ws['B25'] = agent_data['csat_areas']['Tone']
    ws['B26'] = agent_data['csat_areas']['Language & Grammar']
    ws['B27'] = agent_data['csat_areas']['Empathy / Listening']
    ws['B28'] = agent_data['csat_areas']['Endings']
    ws['B29'] = agent_data['csat_areas']['Escalations']

    # KPIs (Row 32-34)
    ws['B32'] = agent_data['kpis']['Communication Skills']
    ws['B33'] = agent_data['kpis']['Productivity']
    ws['B34'] = agent_data['kpis']['Quality of Support']

    # Final Score (Row 35)
    ws['B35'] = f"{calculate_score(agent_data)}%"

    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()

# --- UI LAYOUT ---
st.sidebar.title("Team Management")
new_agent = st.sidebar.text_input("Add New Agent")
if st.sidebar.button("Add"):
    if new_agent:
        st.session_state.agents.append(get_initial_agent(new_agent))

agent_names = [a["name"] for a in st.session_state.agents]
selected_name = st.sidebar.selectbox("Select Agent", agent_names)
agent_idx = agent_names.index(selected_name)
current_agent = st.session_state.agents[agent_idx]

st.title(f"🚀 Performance Review: {current_agent['name']}")

tab1, tab2, tab3 = st.tabs(["Metrics & Scoring", "Batch Upload CSV", "Excel Export"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("CSAT Areas (1-5)")
        for area in current_agent["csat_areas"]:
            current_agent["csat_areas"][area] = st.slider(area, 0.0, 5.0, current_agent["csat_areas"][area], 0.5)
    with col2:
        st.subheader("KPIs (1-10)")
        for kpi in current_agent["kpis"]:
            current_agent["kpis"][kpi] = st.slider(kpi, 0.0, 10.0, current_agent["kpis"][kpi], 0.5)

with tab2:
    st.info("Upload multiple CSVs to batch process chats for the same agent.")
    uploaded_files = st.file_uploader("Upload CSVs", type="csv", accept_multiple_files=True)
    if uploaded_files:
        combined_df = pd.concat([pd.read_csv(f) for f in uploaded_files])
        agent_col = next((c for c in combined_df.columns if c in ['Agent', 'Assignee']), None)
        if agent_col:
            stats = combined_df.groupby(agent_col).size()
            if current_agent["name"] in stats:
                current_agent["total_chats"] = int(stats[current_agent["name"]])
                st.success(f"Updated {current_agent['name']}'s total chats to {current_agent['total_chats']}")

with tab3:
    st.subheader("Generate Excel Report")
    if st.button("Generate Pre-filled Excel"):
        excel_file = export_to_excel(current_agent)
        if excel_file:
            st.download_button(
                label="📥 Download Excel Report",
                data=excel_file,
                file_name=f"{current_agent['name']}_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Error: 'template.xlsx' not found in repository. Please upload your template file.")
