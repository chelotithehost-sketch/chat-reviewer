import streamlit as st
import pandas as pd
import io
import os
import google.generativeai as genai
import json
import zipfile
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

# --- CONFIGURATION ---
st.set_page_config(
    page_title="HostAfrica AI Auditor - Enhanced Security Edition", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM STYLES ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .strength-item {
        background-color: #d4edda;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 0.3rem;
        border-left: 3px solid #28a745;
    }
    .improvement-item {
        background-color: #fff3cd;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 0.3rem;
        border-left: 3px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-exp')

# --- DATA STRUCTURES ---
if 'agents' not in st.session_state:
    st.session_state.agents = {}

def get_initial_agent(name=""):
    return {
        "name": name,
        "audit_data": None,
        "total_chats": 0,
        "audit_timestamp": None,
        "raw_transcripts": []
    }

# --- RECURSIVE ZIP PROCESSING ---
def get_agent_transcripts(uploaded_zip, target_name):
    """Extract transcripts for a specific agent from ZIP file"""
    transcripts = []
    chat_metadata = []
    
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        for file_path in z.namelist():
            if file_path.endswith('.json'):
                with z.open(file_path) as f:
                    try:
                        data = json.load(f)
                        chat_text = ""
                        belongs_to_agent = False
                        message_count = 0
                        
                        # Extract metadata
                        chat_id = data.get("id", "unknown")
                        started_at = data.get("started", "")
                        
                        # Extracting transcript data based on tawk.to JSON structure
                        for msg in data.get("messages", []):
                            name = msg.get("sender", {}).get("n", "Visitor")
                            body = msg.get("msg", "")
                            timestamp = msg.get("t", "")
                            
                            chat_text += f"[{timestamp}] {name}: {body}\n"
                            message_count += 1
                            
                            if name == target_name:
                                belongs_to_agent = True
                        
                        if belongs_to_agent and message_count > 3:  # Only include substantial chats
                            transcripts.append(chat_text)
                            chat_metadata.append({
                                "chat_id": chat_id,
                                "started_at": started_at,
                                "message_count": message_count
                            })
                    except Exception as e:
                        st.warning(f"Could not process file {file_path}: {str(e)}")
                        continue
    
    return transcripts, chat_metadata

# --- ENHANCED AI AUDIT LOGIC ---
def run_comprehensive_audit(transcripts, agent_name):
    """Run comprehensive AI-powered audit with detailed analysis"""
    
    # Use up to 50 transcripts for comprehensive analysis
    sample_size = min(50, len(transcripts))
    sample = "\n\n========== NEW CHAT SESSION ==========\n\n".join(transcripts[:sample_size])
    
    prompt = f"""
You are a Senior Technical QA Auditor at HostAfrica with 10+ years of experience evaluating technical support quality.
You are conducting a comprehensive performance review of agent: {agent_name}

CRITICAL INSTRUCTIONS:
1. Analyze ONLY the agent's performance, NOT bots or automated messages
2. Focus on REAL examples from the actual chat transcripts provided
3. All scores must use the correct scale as specified
4. Provide actionable, specific feedback based on actual chat evidence

SCORING SCALES:
- Individual metrics: 0.0 to 5.0 (where 5.0 is exceptional)
- Overall score: 0.0 to 10.0 (composite of all metrics)

EVALUATION FRAMEWORK (Weighted):

1. SECURITY & PIN VERIFICATION PROTOCOL (Weight: 20%)
   - Did agent request PIN when required (before accessing account details)?
   - Did agent avoid redundant PIN requests (not asking for already-provided PIN)?
   - Did agent follow proper security procedures consistently?
   - Rate: 0.0-5.0

2. TECHNICAL CAPABILITY & ACCURACY (Weight: 25%)
   - Accuracy in diagnosing DNS, Email, SSL, WordPress, hosting issues
   - Proper use of diagnostic tools (Ping, Traceroute, WHOIS, cPanel)
   - Correctness of technical solutions provided
   - Rate: 0.0-5.0

3. COMMUNICATION & PROFESSIONALISM (Weight: 15%)
   - Clarity and professionalism in communication
   - Empathy and patience with customers
   - Grammar, spelling, and tone appropriateness
   - Rate: 0.0-5.0

4. INVESTIGATIVE & PROBLEM-SOLVING APPROACH (Weight: 20%)
   - Systematic troubleshooting methodology
   - Asking relevant diagnostic questions
   - Root cause analysis capability
   - Thoroughness in investigation
   - Rate: 0.0-5.0

5. CHAT OWNERSHIP & RESOLUTION (Weight: 20%)
   - Taking full ownership of issues
   - Following through to resolution
   - Proactive communication and updates
   - Proper escalation when needed
   - Rate: 0.0-5.0

OUTPUT REQUIREMENTS:
Provide exactly 20 detailed technical examples from the actual transcripts. Each example must:
- Reference a REAL issue from the chats
- Show the ACTUAL agent action/response
- Include specific improvement recommendations
- Indicate PIN handling quality (Yes/No/Redundant/N/A)

Return ONLY valid JSON in this exact structure:
{{
    "overall_score": 0.0,
    "overall_assessment": "Comprehensive 3-4 paragraph summary of agent's performance, highlighting key patterns observed across all interactions",
    "metrics": {{
        "security_pin_protocol": 0.0,
        "technical_capability": 0.0,
        "communication_professionalism": 0.0,
        "investigative_approach": 0.0,
        "chat_ownership_resolution": 0.0
    }},
    "key_strengths": [
        "Specific strength with example",
        "Specific strength with example",
        "Specific strength with example",
        "Specific strength with example",
        "Specific strength with example"
    ],
    "key_development_areas": [
        "Specific area for improvement with actionable advice",
        "Specific area for improvement with actionable advice",
        "Specific area for improvement with actionable advice",
        "Specific area for improvement with actionable advice",
        "Specific area for improvement with actionable advice"
    ],
    "pin_protocol_feedback": "Detailed analysis of PIN verification practices: when PIN was requested, any redundant requests, security protocol adherence, specific examples of good/poor PIN handling",
    "technical_examples": [
        {{
            "example_number": 1,
            "issue_type": "DNS/Email/SSL/WordPress/etc",
            "customer_issue": "Specific customer complaint or issue",
            "agent_action": "Detailed description of what agent did",
            "pin_handled_well": "Yes/No/Redundant/N/A",
            "outcome": "What happened as a result",
            "assessment": "Was this handled well or poorly?",
            "improvement": "Specific actionable improvement suggestion",
            "severity": "Minor/Moderate/Major/Critical"
        }},
        ... (continue for all 20 examples)
    ],
    "performance_trends": {{
        "response_time_assessment": "Analysis of agent's response speed",
        "consistency": "How consistent is the agent's performance",
        "technical_depth": "Assessment of technical knowledge depth",
        "customer_satisfaction_indicators": "Signs of customer satisfaction or frustration"
    }},
    "recommended_training": [
        "Specific training recommendation based on identified gaps",
        "Specific training recommendation based on identified gaps",
        "Specific training recommendation based on identified gaps"
    ],
    "standout_moments": [
        "Exceptional handling example",
        "Exceptional handling example"
    ],
    "critical_incidents": [
        "Any critical errors or serious issues"
    ]
}}

CHAT TRANSCRIPTS TO ANALYZE:
{sample}

Remember: Base ALL examples and assessments on the ACTUAL transcripts provided above. Be specific, fair, and constructive.
"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # Clean up JSON response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        # Parse JSON
        audit_result = json.loads(text.strip())
        
        # Validate and cap scores
        audit_result['overall_score'] = min(float(audit_result.get('overall_score', 0)), 10.0)
        for key in audit_result.get('metrics', {}):
            audit_result['metrics'][key] = min(float(audit_result['metrics'][key]), 5.0)
        
        return audit_result
        
    except json.JSONDecodeError as e:
        st.error(f"JSON Parsing Error: {e}")
        st.error(f"Raw response: {text[:500]}")
        return None
    except Exception as e:
        st.error(f"AI Generation Error: {e}")
        return None

# --- PDF REPORT GENERATION ---
def generate_pdf_report(agent_data, agent_name, output_path):
    """Generate a comprehensive PDF performance review report"""
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=10,
        spaceBefore=10
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    
    # Build story
    story = []
    
    # Title
    story.append(Paragraph("PERFORMANCE REVIEW REPORT", title_style))
    story.append(Paragraph(f"<b>Agent:</b> {agent_name}", styles['Normal']))
    story.append(Paragraph(f"<b>Review Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"<b>Chats Analyzed:</b> {agent_data.get('total_chats', 0)}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Overall Score
    overall_score = agent_data.get('audit_data', {}).get('overall_score', 0)
    story.append(Paragraph("OVERALL PERFORMANCE SCORE", heading1_style))
    
    # Score table
    score_data = [[f"{overall_score}/10.0"]]
    score_table = Table(score_data, colWidths=[2*inch])
    score_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 24),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f4f8')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f77b4')),
        ('PADDING', (0, 0), (-1, -1), 20),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1f77b4'))
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Overall Assessment
    story.append(Paragraph("OVERALL ASSESSMENT", heading1_style))
    assessment = agent_data.get('audit_data', {}).get('overall_assessment', 'No assessment available')
    story.append(Paragraph(assessment, body_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Metrics
    story.append(Paragraph("PERFORMANCE METRICS", heading1_style))
    metrics = agent_data.get('audit_data', {}).get('metrics', {})
    
    metrics_data = [['Metric', 'Score (out of 5.0)']]
    for key, value in metrics.items():
        metric_name = key.replace('_', ' ').title()
        metrics_data.append([metric_name, f"{value}/5.0"])
    
    metrics_table = Table(metrics_data, colWidths=[4*inch, 1.5*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Page Break
    story.append(PageBreak())
    
    # Strengths
    story.append(Paragraph("KEY STRENGTHS", heading1_style))
    strengths = agent_data.get('audit_data', {}).get('key_strengths', [])
    for i, strength in enumerate(strengths, 1):
        story.append(Paragraph(f"<b>{i}.</b> {strength}", body_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Development Areas
    story.append(Paragraph("AREAS FOR DEVELOPMENT", heading1_style))
    dev_areas = agent_data.get('audit_data', {}).get('key_development_areas', [])
    for i, area in enumerate(dev_areas, 1):
        story.append(Paragraph(f"<b>{i}.</b> {area}", body_style))
    story.append(Spacer(1, 0.2*inch))
    
    # PIN Protocol Feedback
    story.append(Paragraph("SECURITY & PIN PROTOCOL ANALYSIS", heading1_style))
    pin_feedback = agent_data.get('audit_data', {}).get('pin_protocol_feedback', 'No feedback available')
    story.append(Paragraph(pin_feedback, body_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Page Break
    story.append(PageBreak())
    
    # Technical Examples
    story.append(Paragraph("DETAILED TECHNICAL EXAMPLES", heading1_style))
    examples = agent_data.get('audit_data', {}).get('technical_examples', [])
    
    for i, example in enumerate(examples, 1):
        story.append(Paragraph(f"<b>Example {i}: {example.get('issue_type', 'N/A')}</b>", heading2_style))
        
        example_data = [
            ['Customer Issue:', example.get('customer_issue', 'N/A')],
            ['Agent Action:', example.get('agent_action', 'N/A')],
            ['PIN Handled Well:', example.get('pin_handled_well', 'N/A')],
            ['Outcome:', example.get('outcome', 'N/A')],
            ['Assessment:', example.get('assessment', 'N/A')],
            ['Improvement:', example.get('improvement', 'N/A')],
            ['Severity:', example.get('severity', 'N/A')]
        ]
        
        example_table = Table(example_data, colWidths=[1.5*inch, 5*inch])
        example_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        
        story.append(example_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Page break every 4 examples
        if i % 4 == 0 and i < len(examples):
            story.append(PageBreak())
    
    # Performance Trends (if available)
    trends = agent_data.get('audit_data', {}).get('performance_trends', {})
    if trends:
        story.append(PageBreak())
        story.append(Paragraph("PERFORMANCE TRENDS", heading1_style))
        for key, value in trends.items():
            trend_name = key.replace('_', ' ').title()
            story.append(Paragraph(f"<b>{trend_name}:</b> {value}", body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Recommended Training
    training = agent_data.get('audit_data', {}).get('recommended_training', [])
    if training:
        story.append(Paragraph("RECOMMENDED TRAINING", heading1_style))
        for i, recommendation in enumerate(training, 1):
            story.append(Paragraph(f"<b>{i}.</b> {recommendation}", body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Standout Moments
    standout = agent_data.get('audit_data', {}).get('standout_moments', [])
    if standout:
        story.append(Paragraph("STANDOUT MOMENTS", heading1_style))
        for i, moment in enumerate(standout, 1):
            story.append(Paragraph(f"<b>{i}.</b> {moment}", body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Critical Incidents
    critical = agent_data.get('audit_data', {}).get('critical_incidents', [])
    if critical:
        story.append(Paragraph("CRITICAL INCIDENTS", heading1_style))
        for i, incident in enumerate(critical, 1):
            story.append(Paragraph(f"<b>{i}.</b> {incident}", body_style))
    
    # Build PDF
    doc.build(story)
    return output_path

# --- UI DISPLAY ---
def display_results(audit_data):
    """Display audit results in the Streamlit UI"""
    
    # Overall Score
    score = min(float(audit_data.get('overall_score', 0)), 10.0)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style='text-align: center; padding: 2rem; background-color: #e8f4f8; border-radius: 10px; border: 3px solid #1f77b4;'>
            <h1 style='color: #1f77b4; margin: 0;'>{score}/10.0</h1>
            <p style='font-size: 1.2rem; color: #666; margin: 0.5rem 0 0 0;'>Overall Performance Score</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Overall Assessment
    st.markdown("### 📋 Overall Assessment")
    st.info(audit_data.get("overall_assessment", "No assessment available"))
    
    # Metrics
    st.markdown("### 📊 Performance Metrics (Out of 5.0)")
    metrics = audit_data.get("metrics", {})
    cols = st.columns(len(metrics))
    
    for i, (key, value) in enumerate(metrics.items()):
        display_val = min(float(value), 5.0)
        metric_name = key.replace("_", " ").title()
        
        # Color coding based on score
        if display_val >= 4.0:
            color = "🟢"
        elif display_val >= 3.0:
            color = "🟡"
        else:
            color = "🔴"
        
        cols[i].metric(f"{color} {metric_name}", f"{display_val}/5.0")
    
    st.markdown("---")
    
    # PIN Protocol Feedback
    st.markdown("### 🔐 Security & PIN Verification Analysis")
    st.warning(audit_data.get("pin_protocol_feedback", "No feedback available"))
    
    # Strengths and Development Areas
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ Key Strengths")
        strengths = audit_data.get("key_strengths", [])
        if strengths:
            for strength in strengths:
                st.markdown(f"""
                <div class='strength-item'>
                    <strong>✓</strong> {strength}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No strengths identified")
    
    with col2:
        st.markdown("### 🎯 Areas for Development")
        dev_areas = audit_data.get("key_development_areas", [])
        if dev_areas:
            for area in dev_areas:
                st.markdown(f"""
                <div class='improvement-item'>
                    <strong>→</strong> {area}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No development areas identified")
    
    st.markdown("---")
    
    # Technical Examples
    st.markdown("### 🔧 Detailed Technical Examples")
    examples = audit_data.get("technical_examples", [])
    
    if examples:
        # Group by severity
        severity_filter = st.selectbox(
            "Filter by Severity:",
            ["All", "Critical", "Major", "Moderate", "Minor"]
        )
        
        filtered_examples = examples if severity_filter == "All" else [
            ex for ex in examples if ex.get('severity', '') == severity_filter
        ]
        
        for i, example in enumerate(filtered_examples, 1):
            severity = example.get('severity', 'N/A')
            severity_emoji = {
                'Critical': '🔴',
                'Major': '🟠',
                'Moderate': '🟡',
                'Minor': '🟢'
            }.get(severity, '⚪')
            
            with st.expander(f"{severity_emoji} Example {i}: {example.get('issue_type', 'N/A')} - {example.get('customer_issue', 'N/A')[:50]}..."):
                st.markdown(f"**Customer Issue:** {example.get('customer_issue', 'N/A')}")
                st.markdown(f"**Agent Action:** {example.get('agent_action', 'N/A')}")
                st.markdown(f"**PIN Handled Well:** {example.get('pin_handled_well', 'N/A')}")
                st.markdown(f"**Outcome:** {example.get('outcome', 'N/A')}")
                st.markdown(f"**Assessment:** {example.get('assessment', 'N/A')}")
                st.markdown(f"**Improvement Recommendation:** {example.get('improvement', 'N/A')}")
                st.markdown(f"**Severity:** {severity}")
    else:
        st.info("No technical examples available")
    
    # Performance Trends
    trends = audit_data.get("performance_trends", {})
    if trends:
        st.markdown("---")
        st.markdown("### 📈 Performance Trends")
        for key, value in trends.items():
            trend_name = key.replace('_', ' ').title()
            st.markdown(f"**{trend_name}:** {value}")
    
    # Recommended Training
    training = audit_data.get("recommended_training", [])
    if training:
        st.markdown("---")
        st.markdown("### 🎓 Recommended Training")
        for i, recommendation in enumerate(training, 1):
            st.markdown(f"{i}. {recommendation}")
    
    # Standout Moments
    standout = audit_data.get("standout_moments", [])
    if standout:
        st.markdown("---")
        st.markdown("### ⭐ Standout Moments")
        for moment in standout:
            st.success(moment)
    
    # Critical Incidents
    critical = audit_data.get("critical_incidents", [])
    if critical:
        st.markdown("---")
        st.markdown("### ⚠️ Critical Incidents")
        for incident in critical:
            st.error(incident)

# --- MAIN APP FLOW ---
def main():
    # Header
    st.markdown("<h1 class='main-header'>🤖 HostAfrica AI Auditor - Enhanced Edition</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Comprehensive Performance Analysis with AI-Powered Insights</p>", unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("🏢 Agent Management")
    st.sidebar.markdown("---")
    
    # Add new agent
    st.sidebar.subheader("Add New Agent")
    new_agent_name = st.sidebar.text_input("Agent Name", key="new_agent_input")
    
    if st.sidebar.button("➕ Add Agent", use_container_width=True):
        if new_agent_name:
            if new_agent_name not in st.session_state.agents:
                st.session_state.agents[new_agent_name] = get_initial_agent(new_agent_name)
                st.sidebar.success(f"Added {new_agent_name}")
                st.rerun()
            else:
                st.sidebar.warning("Agent already exists")
        else:
            st.sidebar.error("Please enter an agent name")
    
    st.sidebar.markdown("---")
    
    # Agent list
    agent_list = list(st.session_state.agents.keys())
    
    if not agent_list:
        st.info("👈 Please add an agent using the sidebar to begin")
        return
    
    # Select agent
    st.sidebar.subheader("Select Agent")
    selected_agent = st.sidebar.selectbox(
        "Choose an agent:",
        agent_list,
        key="agent_selector"
    )
    
    # Remove agent button
    if st.sidebar.button(f"🗑️ Remove {selected_agent}", use_container_width=True):
        del st.session_state.agents[selected_agent]
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"**Total Agents:** {len(agent_list)}")
    
    # Main content area
    agent = st.session_state.agents[selected_agent]
    
    # Tabs
    tab1, tab2 = st.tabs(["🤖 Audit Interface", "📈 Detailed Results & Export"])
    
    with tab1:
        st.subheader(f"Analyzing: {selected_agent}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            zip_file = st.file_uploader(
                "Upload tawk.to ZIP file containing chat transcripts",
                type="zip",
                help="Upload the exported ZIP file from tawk.to"
            )
        
        with col2:
            if agent.get("audit_timestamp"):
                st.metric("Last Audit", agent["audit_timestamp"].strftime("%Y-%m-%d %H:%M"))
            if agent.get("total_chats"):
                st.metric("Chats Analyzed", agent["total_chats"])
        
        if zip_file:
            st.success(f"✅ File uploaded: {zip_file.name}")
            
            if st.button("🚀 Run Comprehensive Audit", use_container_width=True, type="primary"):
                with st.spinner(f"🔍 AI is analyzing transcripts for {selected_agent}..."):
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Extract transcripts
                    status_text.text("📂 Extracting transcripts from ZIP file...")
                    progress_bar.progress(20)
                    transcripts, metadata = get_agent_transcripts(zip_file, selected_agent)
                    
                    if not transcripts:
                        st.error(f"❌ No chats found for agent '{selected_agent}' in the uploaded file.")
                        st.info("Please verify that the agent name matches exactly as it appears in the chat transcripts.")
                        return
                    
                    # Update progress
                    status_text.text(f"✅ Found {len(transcripts)} chats for {selected_agent}")
                    progress_bar.progress(40)
                    
                    # Run AI audit
                    status_text.text("🤖 Running AI-powered comprehensive analysis...")
                    progress_bar.progress(60)
                    
                    audit_result = run_comprehensive_audit(transcripts, selected_agent)
                    
                    if audit_result:
                        # Update agent data
                        agent["audit_data"] = audit_result
                        agent["total_chats"] = len(transcripts)
                        agent["audit_timestamp"] = datetime.now()
                        agent["raw_transcripts"] = transcripts[:10]  # Store first 10 for reference
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Analysis complete!")
                        
                        st.success(f"🎉 Successfully analyzed {len(transcripts)} chats!")
                        st.balloons()
                        
                        # Show quick summary
                        st.markdown("### Quick Summary")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Overall Score", f"{audit_result.get('overall_score', 0)}/10")
                        col2.metric("Strengths", len(audit_result.get('key_strengths', [])))
                        col3.metric("Dev Areas", len(audit_result.get('key_development_areas', [])))
                        
                        st.info("👉 Switch to the 'Detailed Results & Export' tab to view the full report and download PDF")
                    else:
                        st.error("❌ Analysis failed. Please try again or check the error messages above.")
        else:
            st.info("📤 Please upload a ZIP file containing tawk.to chat transcripts to begin analysis")
    
    with tab2:
        if agent.get("audit_data"):
            # Display results
            display_results(agent["audit_data"])
            
            st.markdown("---")
            
            # Export section
            st.markdown("### 📥 Export Report")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Download PDF
                if st.button("📄 Generate & Download PDF Report", use_container_width=True, type="primary"):
                    with st.spinner("Generating PDF report..."):
                        # Generate PDF
                        pdf_path = f"/tmp/performance_review_{selected_agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        generate_pdf_report(agent, selected_agent, pdf_path)
                        
                        # Read PDF
                        with open(pdf_path, "rb") as f:
                            pdf_data = f.read()
                        
                        # Download button
                        st.download_button(
                            label="⬇️ Download PDF Report",
                            data=pdf_data,
                            file_name=f"HostAfrica_Performance_Review_{selected_agent}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                        st.success("✅ PDF report generated successfully!")
            
            with col2:
                # Download JSON
                json_data = json.dumps(agent["audit_data"], indent=2)
                st.download_button(
                    label="📊 Download JSON Data",
                    data=json_data,
                    file_name=f"audit_data_{selected_agent}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )
        else:
            st.info("ℹ️ No audit data available. Please run an audit in the 'Audit Interface' tab first.")

if __name__ == "__main__":
    main()
