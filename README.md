# PersonalAI — Intelligent Personal Assistant Agent
### *A Full-Stack Agentic AI Personal Assistant & Academic Mentor*
**Final-Year B.Tech Computer Science & Engineering Capstone Project**  
**Subject:** Agentic AI Development  

---

## 📋 Table of Contents
1. [Project Abstract](#1-project-abstract)
2. [Problem Statement](#2-problem-statement)
3. [Objectives of the Project](#3-objectives-of-the-project)
4. [Limitations of Existing Systems](#4-limitations-of-existing-systems)
5. [Proposed System & Agentic Architecture](#5-proposed-system--agentic-architecture)
6. [Key Features](#6-key-features)
7. [Technology Stack](#7-technology-stack)
8. [Project Structure](#8-project-structure)
9. [Installation & Setup Guide](#9-installation--setup-guide)
10. [Running the Application](#10-running-the-application)
11. [Running Automated Tests](#11-running-automated-tests)
12. [User Interface & Screenshots](#12-user-interface--screenshots)
13. [Agentic AI vs Traditional Chatbots](#13-agentic-ai-vs-traditional-chatbots)
14. [Viva Voce & Placement Interview Cheat Sheet](#14-viva-voce--placement-interview-cheat-sheet)
15. [Limitations & Future Enhancements](#15-limitations--future-enhancements)
16. [Academic References & Credits](#16-academic-references--credits)

---

## 1. Project Abstract
Modern productivity tools and conversational AI interfaces typically operate in silos: task managers lack intelligent contextual reasoning, while conversational chatbots lack agency and execution ability to manipulate real databases. **PersonalAI** bridges this gap by implementing an autonomous, full-stack **Agentic AI Personal Assistant**.

PersonalAI utilizes an iterative **ReAct (Reasoning + Acting)** execution loop. It interprets natural language user intents, creates structured multi-day milestone plans, validates execution arguments using Pydantic, calls registered Python tools, and persists state in a local SQLite database. It incorporates persistent memory for user preferences, an interactive placement interview and quiz helper, and an executive dashboard with proactive in-app deadline reminders.

---

## 2. Problem Statement
College students and software engineering professionals face critical challenges managing study routines, placement preparation, academic assignments, and deadlines:
1. **Tool Fragmentation:** Users must juggle disparate tools for task management, calendar tracking, interview study resources, and AI questioning.
2. **Lack of Autonomous Execution in AI:** Mainstream LLM interfaces (e.g., standard ChatGPT) can suggest study plans but cannot directly create, update, query, or track tasks in a persistent database.
3. **Absence of Grounded State & Memory:** Typical conversational interfaces do not remember user context across sessions or align recommendations with actual pending deadlines.

---

## 3. Objectives of the Project
- **Autonomous Tool Calling:** Implement a real ReAct loop where the AI selects and invokes registered Python tools to interact with persistent storage.
- **Goal Decomposition & Planning:** Enable users to state high-level goals (e.g., *"Help me prepare for my Java interview in 7 days"*) and automatically generate structured milestones.
- **Human-in-the-Loop Safety:** Enforce confirmation barriers before destructive operations (deleting tasks) or committing generated plans.
- **Persistent State & Memory Store:** Store tasks, goals, activity audits, and user preferences in an ACID-compliant SQLite database.
- **Offline Reliability:** Provide deterministic fallback dispatchers and comprehensive local tests so the application runs and evaluates reliably without a paid API key.
- **Comprehensive Academic Documentation:** Supply architecture specifications, viva questions, and a turn-by-turn demonstration script for examination evaluation.

---

## 4. Limitations of Existing Systems

| Feature | Traditional To-Do Apps (e.g. Todoist) | Standard AI Chatbots (e.g. ChatGPT Free) | **PersonalAI (Proposed System)** |
| :--- | :--- | :--- | :--- |
| **Natural Language Understanding** | Minimal / Keyword only | High | **High + Agentic Context** |
| **Tool Execution on Database** | No | No (pure text only) | **Yes (Real Python & SQLite Execution)** |
| **Goal Decomposition** | Manual entry required | Generates text only | **Decomposes & writes tasks to DB upon confirmation** |
| **Smart Recommendation** | Simple sort rules | No access to user DB | **Multi-tier urgency & deadline analysis** |
| **Persistent User Preferences** | Static profile fields | Session-only / Opaque | **Explicit, auditable SQLite key-value store** |
| **Offline Capability** | Yes (manual) | No | **Yes (Offline tool dispatcher + mock bank)** |

---

## 5. Proposed System & Agentic Architecture

PersonalAI replaces static prompt-response flows with a verified **Reasoning and Action cycle**:

```
[ User Prompt ]
      │
      ▼
[ Agent Orchestrator ] ◄── Injects ── [ Persistent Memory Context ]
      │
      ▼
[ LLM API Call with Tool Schemas ]
      │
      ├───────────────────────┬───────────────────────┐
      ▼                       ▼                       ▼
(Direct Answer)       (Tool Call Required)    (Iteration Limit Reached)
      │                       │                       │
      │                       ▼                       │
      │             [ Pydantic Validation ]           │
      │                       │                       │
      │                       ▼                       │
      │             [ Python Tool Handler ]           │
      │                       │                       │
      │                       ▼                       │
      │             [ SQLite Transaction ]            │
      │                       │                       │
      │                       ▼                       │
      │             [ Observation Result ]            │
      │                       │                       │
      │                       └───────────┐           │
      │                                   │           │
      ▼                                   ▼           ▼
[ User Interface ] ◄────────────── [ Re-feed into LLM ]
```

### What Makes This System "Agentic"?
1. **Planning:** Breaks down complex, ambiguous goals into discrete chronological milestones.
2. **Tool Selection:** Selects appropriate functions from an explicit registry of tools (`create_task`, `list_tasks`, `save_goal_plan`, etc.).
3. **Execution:** Translates LLM JSON arguments into typed Python objects and executes real database operations.
4. **Feedback:** Reads real database outputs back into the conversation context to confirm state changes.
5. **Controlled Completion:** Terminates autonomously once the goal is accomplished or `max_iterations` is reached.

---

## 6. Key Features

### 1. Autonomous Agentic Chat
- Natural language task creation, updates, and deletion.
- Real-time expandable **Agent Tool Execution Trace** showing tool name, arguments, and returned SQLite results for demonstration transparency.
- Honest offline mode with deterministic intent dispatch when no API key is set.

### 2. Smart Task Manager
- Full CRUD operations: Title, description, category (`Study`, `Interview`, `Assignment`, `Work`, `Personal`, `General`), priority (`Low`, `Medium`, `High`, `Urgent`), and deadlines.
- Interactive status toggling (Pending ➔ In Progress ➔ Completed).
- Multi-criteria filtering by category, priority, status, and search keywords.
- Human-in-the-loop deletion confirmation guard.

### 3. AI Goal Planner
- High-level curriculum and milestone generator (e.g. 7-Day Java Sprint, 14-Day Python Fundamentals, DSA Preparation).
- Generates titles, descriptions, estimated hours, and suggested sequential deadlines.
- Preview screen with explicit user confirmation before writing tasks to the database.

### 4. Executive Dashboard & In-App Reminders
- Top metric cards: Total, Pending, Completed, Overdue, Active Goals, and Completion Percentage.
- Proactive in-app overdue alerts in red.
- **Smart Agent Recommendation Engine**: Hierarchical algorithm highlighting the single next task to tackle (Overdue ➔ Due Today ➔ Urgent Pending).
- Quick task creation form and live SQLite activity audit log.

### 5. Placement Study & Interview Helper
- **Concept Explainer**: Explains technical concepts with analogies, internal mechanisms, and viva pitfalls.
- **Mock Interview Simulator**: Technical questions (Java, Python, DBMS, DSA) with interactive candidate answer scoring (1-10) and feedback.
- **Practice Quizzes**: Multiple-choice quizzes with instant grading and explanations.

### 6. Persistent Memory & Configuration
- Explicit key-value memory store for user preferences, target roles, and college context.
- System prompt injection for personalized agent interactions.
- Secure API key management supporting OpenAI, Groq, OpenRouter, and Ollama.

---

## 7. Technology Stack

- **Programming Language:** Python 3.11 / 3.14 compatible
- **Web Interface:** Streamlit
- **Persistent Storage:** SQLite3 (WAL journal mode, foreign key support)
- **Data Validation:** Pydantic v2
- **LLM Interface:** OpenAI Python Client (`openai>=1.30.0`) supporting OpenAI-compatible endpoints
- **Environment Management:** python-dotenv
- **Automated Testing:** pytest 8+

---

## 8. Project Structure

```
PersonalAI/
├── app.py                      # Main Streamlit application entrypoint
├── requirements.txt            # Python dependencies
├── .env.example                # Configuration template
├── .gitignore                  # Git ignore rules
├── README.md                   # Academic project documentation
├── database/                   # Database persistence layer
│   ├── __init__.py
│   ├── db.py                   # SQLite connection, context managers, logging
│   └── schema.sql              # Relational schema DDL
├── agent/                      # Core agentic layer
│   ├── __init__.py
│   ├── orchestrator.py         # ReAct agent loop & offline dispatcher
│   ├── prompts.py              # System prompts & tool guidelines
│   ├── tools.py                # Tool registry, schemas & Python handlers
│   └── memory.py               # Persistent key-value memory manager
├── services/                   # Business logic services
│   ├── __init__.py
│   ├── task_service.py         # Task CRUD, filters, metrics & recommendations
│   ├── planner_service.py      # Goal planning & curriculum decomposition
│   ├── study_service.py        # Concept explanations, mock interview & quizzes
│   └── llm_service.py          # OpenAI client wrapper & key validation
├── ui/                         # Streamlit user interface components
│   ├── __init__.py
│   ├── dashboard.py            # Executive dashboard view
│   ├── assistant.py            # AI agent conversational chat view
│   ├── tasks.py                # Task management table view
│   ├── planner.py              # Goal planner view
│   ├── study_helper.py         # Study and interview helper view
│   └── settings.py             # Memory & API settings view
├── tests/                      # Automated test suite (35 test cases)
│   ├── __init__.py
│   ├── conftest.py             # Isolated temporary SQLite fixture
│   ├── test_database.py        # Database init & logging tests
│   ├── test_tasks.py           # Task CRUD & recommendation tests
│   ├── test_agent_tools.py     # Tool schema validation & execution tests
│   ├── test_agent_orchestrator.py # ReAct loop, iterations & offline tests
│   ├── test_online_ai.py       # Online AI connection, error sanitization & tool tests
│   └── test_services.py        # Planner & study helper tests
└── docs/                       # Project documentation
    ├── architecture.md         # Detailed architectural specification
    ├── demo_script.md          # Turn-by-turn presentation script
    └── viva_questions.md       # Comprehensive viva questions & answers
```

---

## 9. Installation & Setup Guide

### Step 1: Clone or Open the Workspace
```bash
cd "D:\Ai personal assi"
```

### Step 2: Create and Activate Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```bash
python -m pip install -r requirements.txt
```

## 9. Enabling Online AI Mode (Step-by-Step)

By default, when no `.env` file or API key is detected, PersonalAI runs in **Offline Mode (`🟠 Offline Mode Active`)**. To enable genuine **Online AI Mode (`🟢 Online AI Active`)**, follow one of the recipes below.

### Step 1: Create your `.env` File
In PowerShell, copy the provided template:
```powershell
copy .env.example .env
```

### Step 2: Choose Your AI Provider

#### Option A: Groq (Recommended — Ultra-Fast & Free Tier Available)
1. Get a free API key at [console.groq.com/keys](https://console.groq.com/keys).
2. Edit `.env`:
   ```ini
   OPENAI_API_KEY=gsk_your_groq_api_key_here
   OPENAI_MODEL=llama-3.3-70b-versatile
   OPENAI_BASE_URL=https://api.groq.com/openai/v1
   ```

#### Option B: Official OpenAI
1. Get an API key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Edit `.env`:
   ```ini
   OPENAI_API_KEY=sk-proj-your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_BASE_URL=
   ```

#### Option C: Google Gemini (Generous Free Tier via OpenAI Endpoint)
1. Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Edit `.env`:
   ```ini
   OPENAI_API_KEY=AIzaSy_your_gemini_api_key_here
   OPENAI_MODEL=gemini-2.5-flash
   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   ```

#### Option D: Ollama (100% Local, Free, No API Key or Internet Required)
1. Install from [ollama.com](https://ollama.com) and run: `ollama run llama3.1`
2. Edit `.env`:
   ```ini
   OPENAI_API_KEY=ollama
   OPENAI_MODEL=llama3.1
   OPENAI_BASE_URL=http://localhost:11434/v1
   ```

*(Alternatively, you can configure and switch providers directly inside the app under **⚙️ Memory & Settings** using the Quick Provider Presets dropdown!)*

### Step 3: Test Connection in the UI
1. Launch the application:
   ```powershell
   python -m streamlit run app.py
   ```
2. In the sidebar, navigate to **⚙️ Memory & Settings**.
3. Click the **🔌 Test AI Connection** button.
4. When verified, the status indicator will immediately turn **`🟢 Online AI Active`** and display the provider name, model, and response latency.

---

## 10. Running Automated Tests

The project includes an automated test suite with **38 unit and integration tests** verifying database operations, tool calling, Pydantic argument validation, online AI connection verification, error sanitization, iteration limits, environment variable precedence, and memory injection:

```bash
python -m pytest tests -v
```

Expected output:
```
============================= test session starts =============================
collected 28 items

tests/test_agent_orchestrator.py::test_offline_agent_dispatch_create_task PASSED [  3%]
tests/test_agent_orchestrator.py::test_offline_agent_recommend_next_task PASSED [  7%]
tests/test_agent_orchestrator.py::test_offline_agent_goal_planning PASSED [ 10%]
tests/test_agent_orchestrator.py::test_agent_iteration_limit_safety PASSED [ 14%]
tests/test_agent_orchestrator.py::test_memory_prompt_injection PASSED    [ 17%]
tests/test_agent_tools.py::test_tool_create_task PASSED                  [ 21%]
tests/test_agent_tools.py::test_tool_list_tasks PASSED                   [ 25%]
tests/test_agent_tools.py::test_tool_mark_task_completed PASSED          [ 28%]
tests/test_agent_tools.py::test_tool_delete_task_safety_confirmation PASSED [ 32%]
tests/test_agent_tools.py::test_tool_memory_operations PASSED            [ 35%]
tests/test_agent_tools.py::test_tool_save_goal_plan PASSED               [ 39%]
tests/test_agent_tools.py::test_unknown_tool_rejection PASSED            [ 42%]
tests/test_database.py::test_database_initialization PASSED              [ 46%]
tests/test_database.py::test_activity_logging PASSED                     [ 50%]
tests/test_database.py::test_database_reset PASSED                       [ 53%]
tests/test_services.py::test_planner_curriculum_generation PASSED        [ 57%]
tests/test_services.py::test_save_confirmed_plan_atomic_persistence PASSED [ 60%]
tests/test_services.py::test_study_service_concept_explainer PASSED      [ 64%]
tests/test_services.py::test_study_service_quiz_and_interview_questions PASSED [ 67%]
tests/test_services.py::test_study_service_answer_evaluation PASSED      [ 71%]
tests/test_services.py::test_llm_service_configuration PASSED            [ 75%]
tests/test_tasks.py::test_create_and_retrieve_task PASSED                [ 78%]
tests/test_tasks.py::test_invalid_task_inputs PASSED                     [ 82%]
tests/test_tasks.py::test_update_and_completion_flow PASSED              [ 85%]
tests/test_tasks.py::test_task_deletion PASSED                           [ 89%]
tests/test_tasks.py::test_list_tasks_and_filters PASSED                  [ 92%]
tests/test_tasks.py::test_dashboard_metrics_calculation PASSED           [ 96%]
tests/test_tasks.py::test_smart_task_recommendation PASSED               [100%]

============================= 28 passed in 3.15s ==============================
```

---

## 12. User Interface & Screenshots

### 1. Executive Dashboard
*Displays real-time metrics, urgent overdue warnings, the smart recommendation card, upcoming deadlines, active goal progress bars, and recent database audit logs.*

```
+-----------------------------------------------------------------------------------------+
|  📊 PersonalAI Executive Dashboard                      Current Date: Sunday, Oct 25    |
+-------------------+-------------------+-------------------+-------------------+---------+
| Total Tasks: 12   | Pending: 8        | Completed: 4(33%) | Overdue: 1 (⚠️)   | Goals: 2|
+-------------------+-------------------+-------------------+-------------------+---------+
| 🎯 Smart Agent Recommendation:                                                          |
| Focus on this next: [#4] Day 2: Strings, Memory Management & GC [Urgent]                |
| [✅ Mark Done]                                                                          |
+-------------------------------------------+---------------------------------------------+
| ⚡ Quick Create Task                       | ⏰ Upcoming Deadlines (Next 7 Days)          |
| [ Title: Review Cache Architecture     ]  | - Day 3 Collections (Due: 2026-10-27) [Done]|
| [ Category: Study v ] [ Priority: High v ] | - Submit Lab File (Due: 2026-10-28)   [Done]|
| [ Deadline: 2026-10-26 ] [ ➕ Add Task  ] |                                             |
+-------------------------------------------+---------------------------------------------+
```

### 2. Agentic Chat & Tool Execution Trace
*Demonstrates multi-step reasoning, real tool calls, and returned SQLite results.*

```
+-----------------------------------------------------------------------------------------+
| 🤖 AI Assistant Chat                                                                    |
| [Suggested: 📅 7-Day Java Prep] [🎯 What should I do next?] [📋 Show pending tasks]    |
+-----------------------------------------------------------------------------------------+
| User: What should I focus on next?                                                      |
|                                                                                         |
| Assistant: Based on your task deadlines and priority levels, you should focus on:       |
| **#4 Day 2: Strings, Memory Management & GC** (Priority: Urgent, Due: 2026-10-26).       |
|                                                                                         |
| 🛠️ Agent Tool Execution Trace (1 tool called, 1 iteration)                       [v]     |
|   Step 1: Called `recommend_next_task`                                                  |
|   Arguments: {}                                                                         |
|   Result: {"success": true, "task": {"id": 4, "title": "Day 2: Strings...", ...}}      |
+-----------------------------------------------------------------------------------------+
| [Ask PersonalAI to plan a goal or manage tasks...                                      ]|
+-----------------------------------------------------------------------------------------+
```

---

## 13. Agentic AI vs Traditional Chatbots

| Dimension | Traditional Chatbot | PersonalAI Agentic System |
| :--- | :--- | :--- |
| **Operational Loop** | Prompt ➔ Text Generation | ReAct Loop: Plan ➔ Tool Selection ➔ Python Execution ➔ Observation ➔ Synthesis |
| **Data Grounding** | Training data or RAG text | Live SQLite Database state with ACID transactions |
| **Action Capability** | None (cannot alter data) | Full (Creates tasks, completes milestones, logs audits) |
| **Safety Guardrails** | Prompt filters only | Schema-level validation (Pydantic), Parameterized SQL, Human confirmation barriers |
| **Loop Control** | Single pass | Bounded multi-turn loop with strict iteration ceiling |

---

## 14. Viva Voce & Placement Interview Cheat Sheet

1. **How does tool calling work?**  
   The LLM is provided with JSON function schemas (`AGENT_TOOLS`). When prompted, it emits a `tool_calls` payload with function name and arguments. Our Python orchestrator validates arguments with Pydantic and executes the native Python method.
2. **How is SQL injection prevented?**  
   All database queries in `database/db.py` and `services/task_service.py` use parameterized queries with `?` placeholders. No string concatenation is used in SQL.
3. **How does the system ensure safety during destructive actions?**  
   `delete_task` and `save_goal_plan` enforce a human-in-the-loop confirmation requirement (`confirm=True`). If unconfirmed, execution is prevented and preview data is returned.
4. **How does persistent memory work?**  
   Explicit memories are stored in SQLite (`memories` table) and dynamically formatted into the system prompt via `get_memory_context_prompt()` before each agent turn.
5. **How does the app operate offline?**  
   If `OPENAI_API_KEY` is not present, the orchestrator routes user requests to a deterministic intent dispatcher that triggers real SQLite tools, keeping 100% of features functional and testable without network access.

*(For the complete list of 10 in-depth questions and answers, see [`docs/viva_questions.md`](docs/viva_questions.md)).*

---

## 15. Limitations & Future Enhancements

### Current Limitations:
- Notifications are in-app only (no SMS or background mobile push daemons).
- Single-user profile per local SQLite database instance.

### Planned Enhancements:
- Multi-user authentication via JWT and session tokens.
- Asynchronous Celery/APScheduler worker for external email reminders.
- Bi-directional synchronization with Google Calendar and Outlook APIs.
- Embedded local quantized LLM inference (e.g. via Ollama or Llama.cpp).

---

## 16. Academic References & Credits
- **Yao et al. (2022)**: *ReAct: Synergizing Reasoning and Acting in Language Models*, ICLR 2023.
- **OpenAI**: *Function Calling and Structured Outputs Specification*.
- **Streamlit Documentation**: *State Management and Component Architecture*.
- **SQLite Consortium**: *Write-Ahead Logging (WAL) and Concurrency*.

---
*Created as a Final Year Computer Science & Engineering Capstone Project.*
