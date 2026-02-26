# 🎯 Microsoft Certification Coach — Multi-Agent AI System

A **5-agent sequential orchestration** system that helps students prepare for Microsoft certification exams. Built following the [Microsoft Agent Framework Sequential Orchestration pattern](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential?pivots=programming-language-python) and powered by **MS Learn MCP Tools**.

---

## 🏗️ Architecture

```
Student Input
     │
     ▼
┌─────────────────────┐
│  Agent 1            │  Parses exam domains & subtopics
│  Syllabus Parser    │
└────────┬────────────┘
         │ full conversation history ↓
┌────────▼────────────┐
│  Agent 2            │  🔗 Calls MS Learn MCP Server
│  Learning Path      │     microsoft_docs_search()
│  Curator            │     per domain → real module URLs
└────────┬────────────┘
         │ full conversation history ↓
┌────────▼────────────┐
│  Agent 3            │  Week-by-week plan + milestones
│  Study Plan         │
│  Generator          │
└────────┬────────────┘
         │ full conversation history ↓
┌────────▼────────────┐
│  Agent 4            │  Reminders, nudges, habits
│  Engagement Coach   │
└────────┬────────────┘
         │
    ┌────▼─────────────────┐
    │  🛑 Human-in-the-Loop │  Student confirms readiness
    │     Checkpoint        │
    └────┬─────────────────┘
         │
┌────────▼────────────┐
│  Agent 5            │  10-question MCQ exam
│  Assessment Agent   │
└────────┬────────────┘
         │
    ┌────▼─────────────────┐
    │  Conditional Branch   │
    │  Pass ≥70% → Cert     │
    │  Fail < 70% → Loop ↩  │
    └──────────────────────┘
```

**Orchestration mix:**
- **Sequential** (`SequentialBuilder` pattern): Agents 1–4, each sees full conversation history
- **Human checkpoint**: Explicit readiness gate before assessment
- **Conditional branching**: Pass → exam booking; Fail → loop back with weak-area context

---

## 📁 Project Structure

```
cert_coach/
├── app.py                          # Streamlit UI (5-phase flow)
├── requirements.txt
├── .env.example
├── agents/
│   ├── syllabus_agent.py           # Agent 1 — exam domain parser
│   ├── curator_agent.py            # Agent 2 — MS Learn path curator
│   ├── planner_agent.py            # Agent 3 — study plan generator
│   ├── engagement_agent.py         # Agent 4 — engagement coach
│   └── assessment_agent.py         # Agent 5 — MCQ assessor + recommender
├── mcp_tools/
│   └── mslearn_mcp.py              # MS Learn MCP server wrappers
└── orchestration/
    └── workflow.py                 # Sequential pipeline engine
```

---

## 🚀 Setup & Run

### 1. Install dependencies

```bash
cd cert_coach
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
# Edit .env with your Azure OpenAI credentials
```

**.env contents:**
```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### 3. Run the app

```bash
streamlit run app.py
```

---

## 🔗 Microsoft Learn MCP Integration

The curator agent calls the **MS Learn MCP Server** (`https://learn.microsoft.com/api/mcp`) using the `microsoft_docs_search` tool to find real learning module URLs per exam domain. The MCP wrapper includes graceful fallback to curated mocks if the endpoint is unreachable, so the pipeline always runs.

**Tools used:**
| Tool | Purpose |
|------|---------|
| `microsoft_docs_search` | Search MS Learn for modules by domain keyword |
| `microsoft_docs_fetch` | Fetch full article text for deep reading |
| `microsoft_code_sample_search` | Find code samples for technical exams |

---

## 🎓 Supported Exams

| Code | Name |
|------|------|
| AZ-900 | Microsoft Azure Fundamentals |
| AI-900 | Microsoft Azure AI Fundamentals |
| DP-900 | Microsoft Azure Data Fundamentals |
| SC-900 | Microsoft Security, Compliance, and Identity Fundamentals |
| AZ-104 | Microsoft Azure Administrator |
| AZ-204 | Developing Solutions for Microsoft Azure |
| AZ-305 | Designing Microsoft Azure Infrastructure Solutions |
| AZ-400 | Designing and Implementing Microsoft DevOps Solutions |
| AI-102 | Designing and Implementing a Microsoft Azure AI Solution |
| DP-203 | Microsoft Azure Data Engineer Associate |
| MS-900 | Microsoft 365 Fundamentals |
| PL-900 | Microsoft Power Platform Fundamentals |
| Custom | Any exam you type manually |

---

## 🧩 Key Design Decisions

### Sequential Orchestration (Agent Framework pattern)
Each agent receives the **full conversation history** from all previous agents — identical semantics to `SequentialBuilder(participants=[...]).build()` in the official docs. The `_run_agent()` function in `workflow.py` maintains a shared `conversation: list[dict]` that grows through the pipeline.

### MCP Tool Integration
MCP calls happen **before** the LLM call in Agent 2. Results are injected as structured context in the user message, allowing the curator LLM to produce real `learn.microsoft.com` URLs.

### Human-in-the-Loop
Implemented as a Streamlit **phase gate** (`st.session_state["phase"]`). The pipeline halts at phase 2 until the student clicks "I'm Ready", then transitions to the assessment agent. This mirrors the `HumanInTheLoop` executor pattern described in the Agent Framework docs.

### Conditional Branching (Pass/Fail)
Post-assessment, `run_recommendation_agent()` scores the answers and sets `verdict = "PASS" | "FAIL"`. The UI routes accordingly — fail path pre-fills weak-area context into the next iteration's goals field, so the loop-back is contextually aware.

---

## 📖 References

- [Agent Framework — Sequential Orchestration](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential?pivots=programming-language-python)
- [Microsoft Learn MCP Server](https://learn.microsoft.com/api/mcp)
- [Microsoft Certification Overview](https://learn.microsoft.com/en-us/certifications/)
- [Exam Registration (Pearson VUE)](https://examregistration.microsoft.com/)
