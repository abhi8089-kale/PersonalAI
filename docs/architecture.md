# PersonalAI System Architecture & Engineering Specification

PersonalAI is an **Agentic AI Personal Assistant and Academic Mentor** built for Computer Science Engineering students and professionals. Unlike standard text-completion chatbots that only generate conversational prose, PersonalAI implements an autonomous reasoning-and-action loop (ReAct) with verified Python tool execution, persistent state in SQLite, and dynamic memory augmentation.

---

## 1. High-Level Architectural Diagram

```
+-----------------------------------------------------------------------------------+
|                                  USER INTERFACE                                   |
|                        Streamlit Multi-Page Web Dashboard                         |
|  [Dashboard] [Agent Chat] [My Tasks] [Goal Planner] [Study Helper] [Settings]    |
+------------------------------------------+----------------------------------------+
                                           | User Prompts / Actions
                                           v
+-----------------------------------------------------------------------------------+
|                                AGENT ORCHESTRATOR                                 |
|                                                                                   |
|  1. Context Builder: Injects persistent user memories & recent history           |
|  2. LLM Call: Passes registered OpenAI-compatible tool specifications             |
|  3. Model Decision: Evaluates if tools are required or if task is complete       |
|  4. Tool Execution: Validates arguments via Pydantic & executes Python handlers   |
|  5. Feedback Loop: Feeds observation results back to model (up to Max Iterations) |
|  6. Offline Dispatcher: Fallback engine when API key is unconfigured              |
+-------------------+-------------------------------------------+-------------------+
                    | Tool Calls                                | Structured Queries
                    v                                           v
+-------------------+-------------------+   +-------------------+-------------------+
|               TOOLS LAYER             |   |              SERVICES LAYER           |
|  - create_task                        |   |  - TaskService (CRUD, stats, sorting) |
|  - list_tasks                         |   |  - PlannerService (Curriculum breakdown)|
|  - mark_task_completed                |   |  - StudyService (Quizzes, grading)    |
|  - update_task                        |   |  - LLMService (OpenAI / Groq client)  |
|  - delete_task (requires confirm)     |   +-------------------+-------------------+
|  - recommend_next_task                |                       |
|  - save_goal_plan (requires confirm)  |                       |
|  - save_memory / recall_memory        |                       |
+-------------------+-------------------+                       |
                    | Parameterized SQL                         |
                    +--------------------+----------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                               PERSISTENT DATA LAYER                               |
|                     SQLite Database (WAL Mode, Thread-Safe)                       |
|                                                                                   |
|  TABLES:                                                                          |
|  - `tasks`: id, title, description, category, priority, status, deadline, goal_id  |
|  - `goals`: id, title, category, target_date, status, plan_data                   |
|  - `memories`: id, category, key, value, created_at, updated_at (UNIQUE key)       |
|  - `activity_logs`: id, action, details, timestamp                                |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Pillars

### A. The Agentic Reasoning-and-Acting (ReAct) Loop
When a user submits a natural-language request:
1. **Perception**: The user input is combined with system prompt instructions and explicitly stored user memories recalled from the `memories` table.
2. **Planning & Tool Selection**: The LLM analyzes the request and produces structured tool calls formatted per OpenAI function-calling specifications.
3. **Pydantic Validation**: Before any execution occurs, input arguments are validated through strong typing schemas (e.g. `CreateTaskArgs`, `DeleteTaskArgs`). Invalid values trigger error responses back to the model without corrupting the database.
4. **Deterministic Execution**: The Python tool handler runs the corresponding service function against SQLite using parameterized queries.
5. **Observation & Reflection**: The tool's output dictionary is formatted into a `tool` role message and returned to the model.
6. **Iterative Refinement**: The agent may choose to call another tool (e.g., listing tasks after creating one) or generate the final user-facing answer.
7. **Maximum Iteration Guard**: An explicit `max_iterations` counter (default: 5) ensures the agent never enters an infinite loop.

---

### B. Persistent State Management
- **ACID-Compliant SQLite**: All tasks, multi-day goals, user preferences, and audit logs are stored in a local SQLite file (`personal_ai.db`).
- **Connection Isolation**: Utilizes context managers (`with get_db() as conn:`) with auto-commit on success and auto-rollback on exception.
- **Write-Ahead Logging (WAL)**: Enabled via `PRAGMA journal_mode = WAL;` to handle multi-threaded reads and writes from Streamlit sessions without database locking.
- **Foreign Key Constraints**: Enforces referential integrity between goals and tasks (`ON DELETE SET NULL`).

---

### C. Persistent Memory Architecture
The agent maintains a dedicated key-value store categorized into:
- `preference`: User preferences (e.g., preferred coding language, explanation depth).
- `fact`: Static user details (e.g., target company, college name, graduation year).
- `context`: Active project context or constraints.
- `profile`: User's name, role, and domain.
- `study_note`: Technical insights and reminders saved from study sessions.

**Memory Injection Workflow**:
Before initiating an LLM turn, `get_memory_context_prompt()` queries all active records and injects them under a dedicated section in the system prompt. This ensures the agent personalizes recommendations without hallucinating unverified assumptions.

---

### D. Safety, Guardrails & Human-in-the-Loop Confirmation
- **No Arbitrary Code Execution**: The system explicitly forbids `eval()`, `exec()`, or arbitrary shell execution.
- **Destructive Operation Guards**:
  - `delete_task` requires `confirm=True`. If `False`, execution is blocked and the agent requests explicit user confirmation.
  - `save_goal_plan` requires `confirm=True`. The user is shown the proposed daily milestone preview and must explicitly confirm before tasks are inserted into the database.
- **SQL Injection Prevention**: 100% of database queries use parameterized SQL (`?` placeholders). No raw SQL string interpolation is ever permitted.
- **Zero API Key Leakage**: API keys are retrieved from environment variables and masked in the UI. Error handlers strip any matching key fragments before displaying messages.

---

### E. Offline Graceful Degradation
To enable seamless evaluation in exam, viva, or placement settings where internet access or paid API keys may be unavailable:
- The system includes a deterministic offline intent dispatcher (`_handle_offline_agent`).
- Core intents (creating tasks, listing tasks, calculating statistics, recommending next tasks, generating curricula) execute real Python tools and database queries with transparent notice banners.
- Tests run completely offline in under 4 seconds.
