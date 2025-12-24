# 📦 Bulk Upload Feature - Complete Guide

## ✅ What's New

The auditor now supports **bulk upload** - process multiple agents from a single upload!

---

## 🎯 How It Works

### Your Workflow (Nested ZIPs):
```
1. Create a folder with all agent ZIPs:
   📁 All_Agents/
   ├── 📦 Athira_chats.zip
   ├── 📦 Timothy_chats.zip
   ├── 📦 Ian_chats.zip
   └── 📦 Mavis_chats.zip

2. Zip the entire folder:
   📦 All_Agents.zip (contains the 4 ZIPs above)

3. Upload All_Agents.zip to the auditor

4. System processes all agents automatically!
```

### Alternative: Single ZIP with All Chats
```
📦 all_chats.zip
├── chat_001.json (Athira)
├── chat_002.json (Timothy)
├── chat_003.json (Athira)
├── chat_004.json (Ian)
└── ... (all JSON files)
```

---

## 🚀 Step-by-Step Usage

### **Method 1: Auto-Detect Agents** (Recommended)

**Step 1: Enable Bulk Mode**
```
☐ 📦 Enable Bulk Upload Mode  ← Check this box
```

**Step 2: Choose Auto-Detect**
```
Choose input method:
● Auto-Detect from ZIP  ← Select this
```

**Step 3: Upload Your ZIP**
```
Upload ZIP file: [Browse...]
→ Select your All_Agents.zip
```

**Step 4: Detect Agents**
```
[🔍 Detect Agents in ZIP]  ← Click this
```

**Result:**
```
✅ Found 4 agent(s)!
Detected agents:
- Athira
- Timothy
- Ian
- Mavis
```

**Step 5: Run Bulk Audit**
```
[🚀 Run Bulk Audit]  ← Click this
```

**Step 6: Download All Reports**
```
[📦 Generate All Excel Reports]
[📄 Generate All PDF Reports]
```

---

### **Method 2: Manual Entry**

**Step 1: Enable Bulk Mode**
```
☐ 📦 Enable Bulk Upload Mode  ← Check this
```

**Step 2: Choose Manual Entry**
```
Choose input method:
● Manual Entry  ← Select this
```

**Step 3: Enter Agent Names**
```
Enter agent names (one per line):
┌─────────────┐
│ Athira      │
│ Timothy     │
│ Ian         │
│ Mavis       │
└─────────────┘
```

**Step 4: Add All Agents**
```
[➕ Add All Agents]  ← Click this
```

**Step 5: Upload ZIP & Run**
```
Upload ZIP → Run Bulk Audit → Download Reports
```

---

## 📊 What You Get

### During Processing:
```
📊 Processing Results
Processing Athira (1/4)...
[████████░░░░░░░░░░░░] 40%
```

### After Completion:
```
📊 Results Summary
┌────────────┬───────┬───────┬──────────────┐
│ agent      │ score │ chats │ status       │
├────────────┼───────┼───────┼──────────────┤
│ Athira     │ 8.0   │ 38    │ ✅ Success   │
│ Timothy    │ 6.5   │ 42    │ ✅ Success   │
│ Ian        │ 7.2   │ 35    │ ✅ Success   │
│ Mavis      │ 9.1   │ 45    │ ✅ Success   │
└────────────┴───────┴───────┴──────────────┘

📥 Download All Reports
[📦 Generate All Excel Reports]  [📄 Generate All PDF Reports]
```

### Downloads:
```
📦 HostAfrica_Bulk_Reviews_20251224.zip
├── 📊 Athira_Performance_Review.xlsx
├── 📊 Timothy_Performance_Review.xlsx
├── 📊 Ian_Performance_Review.xlsx
└── 📊 Mavis_Performance_Review.xlsx

📦 HostAfrica_Bulk_Reviews_PDF_20251224.zip
├── 📄 Athira_Performance_Review.pdf
├── 📄 Timothy_Performance_Review.pdf
├── 📄 Ian_Performance_Review.pdf
└── 📄 Mavis_Performance_Review.pdf
```

---

## 🎯 Supported ZIP Structures

### ✅ Structure 1: Nested ZIPs (Your Method)
```
📦 All_Agents.zip
├── 📦 agent1.zip
│   ├── chat1.json
│   └── chat2.json
├── 📦 agent2.zip
│   ├── chat3.json
│   └── chat4.json
└── 📦 agent3.zip
    ├── chat5.json
    └── chat6.json
```

### ✅ Structure 2: Flat ZIP
```
📦 all_chats.zip
├── chat1.json (Athira)
├── chat2.json (Timothy)
├── chat3.json (Athira)
├── chat4.json (Ian)
└── chat5.json (Mavis)
```

### ✅ Structure 3: Mixed (Nested + Flat)
```
📦 mixed.zip
├── 📦 athira_chats.zip
│   └── chat1.json
├── chat2.json (Timothy - loose)
└── chat3.json (Ian - loose)
```

**All three structures work!** The system intelligently handles nested ZIPs and flat structures.

---

## 💡 Pro Tips

### 1. **Organize by Period**
```
📁 Q4_2024_Reviews/
├── 📦 October_Chats.zip
├── 📦 November_Chats.zip
└── 📦 December_Chats.zip

→ Zip as Q4_2024_Reviews.zip
→ Upload and process all months at once
```

### 2. **Filter by Team**
```
📁 Support_Team_A/
├── 📦 Athira.zip
├── 📦 Timothy.zip
└── 📦 Ian.zip

📁 Support_Team_B/
├── 📦 Mavis.zip
├── 📦 John.zip
└── 📦 Sarah.zip

→ Process each team separately
```

### 3. **Name Your ZIPs Clearly**
```
✅ Good:
- Athira_December_2024.zip
- Support_Team_Q4.zip
- All_Agents_2024.zip

❌ Avoid:
- export.zip
- data.zip
- file.zip
```

---

## ⚙️ Technical Details

### Auto-Detection Logic:
```python
1. Scans all JSON files in ZIP
2. Extracts sender names from messages
3. Filters out "Visitor" and "Bot" names
4. Returns unique agent names
5. Auto-creates agents in system
```

### Processing:
```python
1. Sequential processing (one agent at a time)
2. Progress tracking for each agent
3. Error handling (continues on failure)
4. Results summary with status
```

### File Handling:
```python
- Supports nested ZIPs (your method)
- Supports flat ZIP structures
- Handles mixed structures
- Skips corrupted files
- Continues on errors
```

---

## 🔍 Troubleshooting

### "No agents detected"
**Cause:** JSON files might not have agent messages
**Solution:** 
- Check that JSON files contain actual chats
- Verify agent names appear in messages
- Try manual entry mode

### "No chats found for agent X"
**Cause:** Agent name mismatch
**Solution:**
- Check exact spelling of agent name
- Names are case-sensitive
- Check for extra spaces

### "Some agents failed"
**Cause:** Various (corrupted files, API limits)
**Solution:**
- Check results summary for specific errors
- Re-run failed agents individually
- Check Gemini API quota

---

## 📊 Performance

### Processing Speed:
```
1 agent   = ~1-2 minutes
5 agents  = ~5-10 minutes
10 agents = ~10-20 minutes
20 agents = ~20-40 minutes
```

### Recommendations:
- **1-5 agents**: Use bulk mode
- **5-10 agents**: Take a coffee break ☕
- **10+ agents**: Run overnight or in batches

### API Limits:
```
Gemini 2.5-flash-lite:
- 10 RPM (requests per minute)
- 20 RPD (requests per day)

→ Max 20 agents per day (free tier)
```

---

## 🎯 Comparison: Single vs Bulk

### Single Mode (Original):
```
Time for 5 agents:
1. Upload ZIP for Agent 1 → Audit → Download
2. Upload ZIP for Agent 2 → Audit → Download
3. Upload ZIP for Agent 3 → Audit → Download
4. Upload ZIP for Agent 4 → Audit → Download
5. Upload ZIP for Agent 5 → Audit → Download

Total: ~15 minutes + 5 uploads
```

### Bulk Mode (New):
```
Time for 5 agents:
1. Upload ONE ZIP with all agents
2. Click "Run Bulk Audit"
3. Download all reports as ZIP

Total: ~5-10 minutes + 1 upload ✅
```

**Bulk mode is 2-3x faster!** 🚀

---

## 📝 Example Workflow

### Monthly Team Review:
```
Day 1: Export all chats from tawk.to
→ One ZIP per agent OR one big ZIP

Day 2: Organize ZIPs
→ Put all agent ZIPs in one folder
→ Zip the folder

Day 3: Process with auditor
→ Enable bulk mode
→ Upload master ZIP
→ Auto-detect agents
→ Run bulk audit
→ Download all reports

Day 4-5: Review results
→ Open Excel/PDF reports
→ Schedule 1-on-1 meetings
→ Discuss findings
```

---

## 🎉 Benefits

### ✅ Time Savings
- Upload once vs multiple uploads
- Batch processing vs one-by-one
- Single download vs multiple

### ✅ Less Work
- Auto-detect agents (no manual entry)
- Batch download (all reports in one ZIP)
- Progress tracking (see status in real-time)

### ✅ Better Organization
- All reports timestamped
- Organized in single ZIP
- Easy to archive

### ✅ Error Resilience
- Continues on failure
- Shows which agents failed
- Re-run only failed ones

---

## 🚀 Quick Start

**Fastest way to bulk process:**

1. ☑️ Enable Bulk Upload Mode
2. 📤 Upload your ZIP (nested or flat)
3. 🔍 Click "Detect Agents in ZIP"
4. 🚀 Click "Run Bulk Audit"
5. 📥 Download All Reports

**That's it! 5 clicks to process unlimited agents.** 🎯

---

## 💬 Need Help?

**Common Questions:**

Q: Can I process 50 agents at once?
A: Yes, but limited by API quota (20/day free tier)

Q: Does it work with my ZIP structure?
A: Yes! Nested, flat, or mixed - all work

Q: Can I cancel mid-processing?
A: No, but you can refresh the page

Q: What if some agents fail?
A: Check results table, re-run failed ones individually

Q: Can I process different time periods?
A: Yes, just organize your ZIPs accordingly

---

**Enjoy your streamlined bulk processing! 📦✨**
