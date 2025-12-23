# 🚀 Quick Start Guide

## Setup (5 minutes)

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure API Key
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Get your Gemini API key from https://makersuite.google.com/app/apikey
3. Replace `your-gemini-api-key-here` with your actual key in `secrets.toml`

### Step 3: Launch the Application
```bash
streamlit run enhanced_ai_auditor.py
```

## First Audit (2 minutes)

### Step 1: Add an Agent
1. In the sidebar, type the agent's name (e.g., "John Doe")
2. Click "➕ Add Agent"

### Step 2: Upload Transcripts
1. Select the agent from the dropdown
2. Click "Upload tawk.to ZIP file"
3. Select your ZIP file containing chat transcripts

### Step 3: Run Analysis
1. Click "🚀 Run Comprehensive Audit"
2. Wait 30-60 seconds for AI analysis
3. View the results!

### Step 4: Download Report
1. Switch to "📈 Detailed Results & Export" tab
2. Click "📄 Generate & Download PDF Report"
3. Share with your team!

## 💡 Pro Tips

- **Exact Names**: Make sure agent names match exactly as they appear in chats
- **Sufficient Data**: Upload at least 10-20 chats for accurate results
- **Regular Reviews**: Run audits monthly to track improvement
- **Action Items**: Focus on "Areas for Development" in coaching sessions

## ⚠️ Common Issues

### "No chats found"
→ Check that the agent name matches exactly (case-sensitive)

### "API Error"
→ Verify your Gemini API key is correct in secrets.toml

### "File not found"
→ Make sure you're running the command from the project directory

## 📞 Need Help?

Refer to the full README.md for detailed documentation and troubleshooting.

---

**Happy Auditing! 🎉**
