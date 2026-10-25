"""
Planner Service for PersonalAI.
Handles goal decomposition into daily milestones, structured plan generation,
and safe atomic persistence of confirmed plans into SQLite.
"""

import json
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional
from database.db import get_db, log_activity
from services.task_service import create_task

# Built-in curriculum templates for high-yield offline planning (college CSE interview / viva topics)
CURRICULUM_TEMPLATES = {
    "java": [
        ("Core Java Basics & OOP Principles", "Classes, Objects, Inheritance, Polymorphism, Abstraction, Encapsulation, JVM vs JRE vs JDK.", "High", 3.0),
        ("Strings, Memory Management & GC", "String pool, immutability, StringBuilder/StringBuffer, Stack vs Heap, Garbage Collection algorithms.", "High", 2.5),
        ("Java Collections Framework - Part 1", "List, ArrayList vs LinkedList, Set, HashSet vs TreeSet, hashing & equals/hashCode contract.", "Urgent", 3.5),
        ("Java Collections Framework - Part 2 & Generics", "Map, HashMap internal working (buckets & treeify), ConcurrentHashMap, Generics fundamentals.", "Urgent", 3.5),
        ("Exception Handling & File I/O", "Checked vs Unchecked exceptions, try-with-resources, custom exceptions, Java NIO vs classic IO.", "Medium", 2.5),
        ("Multithreading & Concurrency", "Thread lifecycle, Runnable vs Callable, synchronization, volatile, ExecutorService, deadlock prevention.", "Urgent", 4.0),
        ("Java 8+ Features & Mock Interview", "Lambdas, Stream API, Optional, functional interfaces, top 30 Java viva & placement interview questions.", "Urgent", 4.0),
    ],
    "python": [
        ("Python Fundamentals & Data Structures", "Data types, mutable vs immutable, lists, tuples, dicts, sets, list comprehensions.", "High", 2.5),
        ("Functions, Scopes & Functional Constructs", "args/kwargs, closures, decorators, lambda functions, map/filter/reduce, LEGB rule.", "High", 3.0),
        ("Object-Oriented Python", "Classes, self, dunder methods (__init__, __str__, __repr__), inheritance, multiple inheritance & MRO.", "High", 3.0),
        ("Generators, Iterators & Memory", "Iterators protocol, yield, generator expressions, memory profiling, garbage collection in Python.", "Medium", 2.5),
        ("File Handling, JSON & APIs", "Context managers (with statement), reading/writing JSON, requests library, REST API fundamentals.", "Medium", 2.5),
        ("Error Handling & Unit Testing", "Custom exceptions, logging best practices, writing unit tests with pytest.", "High", 2.5),
        ("Asyncio & Final Capstone Review", "Async/await event loop, concurrent execution, mock interview questions & code walkthrough.", "Urgent", 3.5),
    ],
    "dsa": [
        ("Arrays & Two Pointers", "Sliding window, two pointers, prefix sums,kadane's algorithm, time & space complexities.", "Urgent", 3.5),
        ("Strings & Hash Maps", "Anagrams, substring search, frequency counting, fast hashing techniques.", "High", 3.0),
        ("Linked Lists & Stacks/Queues", "Reverse linked list, cycle detection (Floyd's), monotonic stack, valid parentheses.", "Urgent", 3.5),
        ("Binary Trees & BST", "Traversals (Inorder, Preorder, Postorder, Level-order), height, diameter, Lowest Common Ancestor.", "Urgent", 4.0),
        ("Recursion & Backtracking", "Subsets, permutations, N-Queens logic, recursion tree and call stack visualization.", "High", 3.5),
        ("Graphs: BFS & DFS", "Graph representations, topological sort, cycle detection in directed/undirected graphs, connected components.", "Urgent", 4.0),
        ("Dynamic Programming Fundamentals", "Memoization vs Tabulation, 0/1 Knapsack, Longest Common Subsequence, final revision.", "Urgent", 4.5),
    ],
    "dbms": [
        ("Relational Model & SQL Fundamentals", "DDL vs DML vs DCL, joins (INNER, LEFT, RIGHT, FULL), GROUP BY, HAVING, subqueries.", "High", 3.0),
        ("Database Design & Normalization", "ER diagrams, functional dependencies, 1NF, 2NF, 3NF, BCNF, lossy vs lossless decomposition.", "Urgent", 3.5),
        ("Transactions & ACID Properties", "Atomicity, Consistency, Isolation levels (dirty read, non-repeatable read, phantom read), Durability.", "Urgent", 3.5),
        ("Concurrency Control & Deadlocks", "Lock-based protocols (2PL, strict 2PL), timestamp ordering, deadlock detection & recovery.", "High", 3.0),
        ("Indexing & Query Optimization", "B-Trees vs B+ Trees, clustered vs non-clustered indexing, hashing, query cost & execution plans.", "Urgent", 3.5),
        ("NoSQL & Distributed Concepts", "CAP theorem, document vs key-value vs column stores, sharding & replication.", "Medium", 2.5),
        ("DBMS Viva & Placement Questions", "Top 50 DBMS interview questions, schema optimization scenarios, practice queries.", "High", 3.0),
    ]
}


def generate_study_plan(
    goal_title: str,
    duration_days: int = 7,
    category: str = "Study",
    custom_notes: str = "",
) -> Dict[str, Any]:
    """
    Generates a structured multi-day goal plan.
    Decomposes the goal into actionable daily milestones with titles, descriptions,
    priority levels, and suggested deadlines starting from tomorrow.
    """
    cleaned_title = goal_title.strip()
    if not cleaned_title:
        raise ValueError("Goal title cannot be empty.")

    days = max(1, min(duration_days, 30))  # limit between 1 and 30 days
    today = date.today()
    target_date = (today + timedelta(days=days)).isoformat()

    tasks: List[Dict[str, Any]] = []

    # If LLM is available, attempt dynamic online curriculum generation
    import services.llm_service as llm_service
    if llm_service.is_llm_available():
        try:
            sys_prompt = (
                "You are an expert Computer Science professor and curriculum planner. "
                f"Deconstruct the user's goal into exactly {days} daily chronological milestones. "
                "Respond ONLY with a JSON object containing a 'tasks' list. Each item must have: "
                "'day_number' (int 1..N), 'title' (string), 'description' (string with key topics), "
                "'priority' (Low, Medium, High, or Urgent), and 'estimated_hours' (float)."
            )
            usr_prompt = f"Goal: {cleaned_title}\nDuration: {days} days\nCategory: {category}\nNotes: {custom_notes}"
            res = llm_service.chat_completion(
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": usr_prompt}],
                temperature=0.2,
            )
            raw = res["content"].strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw.strip())
            if isinstance(parsed, dict) and "tasks" in parsed and len(parsed["tasks"]) > 0:
                for idx, t in enumerate(parsed["tasks"][:days]):
                    deadline_str = (today + timedelta(days=idx + 1)).isoformat()
                    tasks.append({
                        "day_number": t.get("day_number", idx + 1),
                        "title": t.get("title", f"Day {idx + 1}: Milestone"),
                        "description": t.get("description", ""),
                        "priority": t.get("priority", "High") if t.get("priority") in {"Low", "Medium", "High", "Urgent"} else "High",
                        "estimated_hours": float(t.get("estimated_hours", 2.5)),
                        "suggested_deadline": deadline_str,
                    })
                if len(tasks) == days:
                    return {
                        "title": cleaned_title,
                        "category": category,
                        "duration_days": days,
                        "target_date": target_date,
                        "notes": custom_notes,
                        "tasks": tasks,
                        "source": "Online AI Model",
                    }
        except Exception:
            tasks = []  # Fallback to curriculum templates below

    lower_title = cleaned_title.lower()
    selected_template = None

    for key, template in CURRICULUM_TEMPLATES.items():
        if key in lower_title:
            selected_template = template
            break

    tasks: List[Dict[str, Any]] = []

    if selected_template and len(selected_template) >= days:
        for i in range(days):
            t_title, t_desc, t_prio, t_hrs = selected_template[i]
            deadline_str = (today + timedelta(days=i + 1)).isoformat()
            tasks.append({
                "day_number": i + 1,
                "title": f"Day {i + 1}: {t_title}",
                "description": f"{t_desc} (Est. {t_hrs} hrs)",
                "priority": t_prio,
                "estimated_hours": t_hrs,
                "suggested_deadline": deadline_str,
            })
    elif selected_template:
        # Scale template items to fit the number of days
        for i in range(days):
            template_idx = i % len(selected_template)
            t_title, t_desc, t_prio, t_hrs = selected_template[template_idx]
            deadline_str = (today + timedelta(days=i + 1)).isoformat()
            tasks.append({
                "day_number": i + 1,
                "title": f"Day {i + 1}: {t_title} (Part {(i // len(selected_template)) + 1})",
                "description": f"{t_desc} (Est. {t_hrs} hrs)",
                "priority": t_prio,
                "estimated_hours": t_hrs,
                "suggested_deadline": deadline_str,
            })
    else:
        # Generic algorithmic breakdown
        for i in range(days):
            deadline_str = (today + timedelta(days=i + 1)).isoformat()
            if i == 0:
                step_title = "Foundations, Setup & Core Concepts"
                step_desc = f"Review prerequisite concepts and set up workspace for '{cleaned_title}'."
                prio = "High"
            elif i == days - 1:
                step_title = "Comprehensive Review, Mock Testing & Final Assessment"
                step_desc = f"Synthesize all concepts, solve practice problems, and self-assess on '{cleaned_title}'."
                prio = "Urgent"
            else:
                progress_pct = int(((i + 1) / days) * 100)
                step_title = f"Milestone #{i + 1} - In-Depth Practice & Application"
                step_desc = f"Deep dive into milestone {i + 1} ({progress_pct}% target completion) for '{cleaned_title}'."
                prio = "High" if i > days // 2 else "Medium"

            tasks.append({
                "day_number": i + 1,
                "title": f"Day {i + 1}: {step_title}",
                "description": step_desc,
                "priority": prio,
                "estimated_hours": 2.5,
                "suggested_deadline": deadline_str,
            })

    return {
        "title": cleaned_title,
        "category": category,
        "duration_days": days,
        "target_date": target_date,
        "notes": custom_notes,
        "tasks": tasks,
    }


def save_confirmed_plan(
    title: str,
    category: str = "Study",
    target_date: Optional[str] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Saves a confirmed goal and all its generated daily tasks atomically in SQLite.
    Links each task to the created goal using goal_id.
    """
    if not title:
        raise ValueError("Goal title cannot be empty.")
    if not tasks:
        raise ValueError("Plan must contain at least one task.")

    now = datetime.now().isoformat()
    plan_json = json.dumps(tasks)

    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO goals (title, description, category, target_date, status, plan_data, created_at)
            VALUES (?, ?, ?, ?, 'Active', ?, ?)
            """,
            (title, f"Structured goal with {len(tasks)} tasks", category, target_date, plan_json, now),
        )
        goal_id = cur.lastrowid

    log_activity("goal_planned", f"Created Goal #{goal_id}: '{title}' with {len(tasks)} milestones", db_path=db_path)

    saved_tasks: List[Dict[str, Any]] = []
    for item in tasks:
        t_title = item.get("title", f"Goal Task")
        t_desc = item.get("description", "")
        t_prio = item.get("priority", "Medium")
        t_deadline = item.get("suggested_deadline") or item.get("deadline")

        created = create_task(
            title=t_title,
            description=t_desc,
            category=category,
            priority=t_prio,
            deadline=t_deadline,
            goal_id=goal_id,
            db_path=db_path,
        )
        saved_tasks.append(created)

    return {
        "goal_id": goal_id,
        "title": title,
        "category": category,
        "target_date": target_date,
        "tasks_count": len(saved_tasks),
        "tasks": saved_tasks,
    }


def list_goals(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists all goals with calculated progress metrics."""
    with get_db(db_path) as conn:
        cur = conn.execute("SELECT * FROM goals ORDER BY id DESC")
        rows = [dict(r) for r in cur.fetchall()]

    enriched = []
    for g in rows:
        goal_id = g["id"]
        progress = get_goal_progress(goal_id, db_path=db_path)
        g["progress"] = progress
        enriched.append(g)
    return enriched


def get_goal(goal_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single goal with its linked tasks."""
    with get_db(db_path) as conn:
        cur = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
        row = cur.fetchone()
        if not row:
            return None
        goal_dict = dict(row)

    with get_db(db_path) as conn:
        cur = conn.execute("SELECT * FROM tasks WHERE goal_id = ? ORDER BY id ASC", (goal_id,))
        tasks = [dict(r) for r in cur.fetchall()]

    goal_dict["tasks"] = tasks
    goal_dict["progress"] = get_goal_progress(goal_id, db_path=db_path)
    return goal_dict


def get_goal_progress(goal_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Calculates completion stats for a specific goal."""
    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress
            FROM tasks WHERE goal_id = ?
            """,
            (goal_id,),
        )
        row = cur.fetchone()
        total = row["total"] or 0
        completed = row["completed"] or 0
        pending = row["pending"] or 0
        in_progress = row["in_progress"] or 0
        rate = round((completed / total * 100), 1) if total > 0 else 0.0

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "completion_rate": rate,
        }


def update_goal_status(goal_id: int, status: str, db_path: Optional[str] = None) -> bool:
    """Updates the status of a goal (Active, Completed, Paused)."""
    with get_db(db_path) as conn:
        cur = conn.execute(
            "UPDATE goals SET status = ?, completed_at = ? WHERE id = ?",
            (status, datetime.now().isoformat() if status == "Completed" else None, goal_id),
        )
        return cur.rowcount > 0
