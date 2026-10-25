"""
Study and Interview Helper Service for PersonalAI.
Supports concept explanations, interview question generation, interactive quizzes,
and answer evaluation. Works online with LLM or offline via structured knowledge banks.
"""

import json
from typing import List, Dict, Any, Optional
import services.llm_service as llm_service
from services.llm_service import LLMServiceError


def is_llm_available() -> bool:
    """Checks whether the LLM is available, delegating to llm_service."""
    return llm_service.is_llm_available()


def chat_completion(*args, **kwargs):
    """Executes chat completion, delegating to llm_service."""
    return llm_service.chat_completion(*args, **kwargs)

# High-yield curated CSE technical interview question bank (offline fallback)
OFFLINE_KNOWLEDGE_BANK = {
    "java": [
        {
            "id": 1,
            "topic": "Core Java",
            "question": "Why is String immutable in Java?",
            "expected_key_points": [
                "String Pool caching reduces memory footprint",
                "Security in network connections, class loaders, and file paths",
                "Thread-safety without synchronization",
                "Hashcode caching makes it optimal as HashMap key"
            ],
            "difficulty": "Intermediate",
            "quiz_options": [
                "To allow thread-safety, security, and string constant pool caching",
                "Because strings cannot be stored in heap memory",
                "Because Java does not allow garbage collection of text",
                "To prevent developers from using StringBuilder"
            ],
            "correct_option_index": 0,
            "explanation": "String immutability enables the String Constant Pool to save memory, ensures thread safety across concurrent operations, and secures sensitive data like database credentials or URLs."
        },
        {
            "id": 2,
            "topic": "Collections",
            "question": "How does HashMap work internally in Java 8?",
            "expected_key_points": [
                "Array of Nodes (buckets) using hash(key) & (n-1)",
                "Handles collisions via LinkedList chaining",
                "Converts LinkedList into a Red-Black Tree (TreeNode) when bucket size reaches TREEIFY_THRESHOLD (8)",
                "Reduces worst-case search time from O(n) to O(log n)"
            ],
            "difficulty": "Hard",
            "quiz_options": [
                "It uses an array and converts colliding buckets to Red-Black Trees when count >= 8",
                "It always uses a doubly linked list without arrays",
                "It stores keys in binary files on disk",
                "It uses linear probing with fixed size 100"
            ],
            "correct_option_index": 0,
            "explanation": "In Java 8, HashMap resolves collisions using buckets of linked lists; once a bucket holds 8 or more entries and table capacity is at least 64, it treeifies into a Red-Black tree to guarantee O(log n) performance."
        },
        {
            "id": 3,
            "topic": "Multithreading",
            "question": "What is the difference between Runnable and Callable in Java?",
            "expected_key_points": [
                "Runnable run() returns void; Callable call() returns a Future with generic result V",
                "Callable can throw checked exceptions; Runnable cannot",
                "Both can be submitted to ExecutorService"
            ],
            "difficulty": "Medium",
            "quiz_options": [
                "Callable can return a value and throw checked exceptions, while Runnable cannot",
                "Runnable creates a new process while Callable creates a light thread",
                "Runnable was introduced in Java 8 while Callable is deprecated",
                "Callable only works with single-threaded programs"
            ],
            "correct_option_index": 0,
            "explanation": "Callable<V> provides a call() method returning V and allows throwing checked exceptions, whereas Runnable's run() returns void and cannot throw checked exceptions."
        }
    ],
    "python": [
        {
            "id": 4,
            "topic": "Python Core",
            "question": "What is the Global Interpreter Lock (GIL) and how does it affect concurrency?",
            "expected_key_points": [
                "Mutex that protects access to Python objects, preventing multiple threads from executing Python bytecode simultaneously",
                "Limits CPU-bound multithreaded performance to single core",
                "I/O-bound tasks benefit from threading because GIL is released during I/O",
                "Multiprocessing bypasses GIL by using separate memory spaces"
            ],
            "difficulty": "Hard",
            "quiz_options": [
                "A mutex ensuring only one thread executes Python bytecode at a time in CPython",
                "A security feature preventing unauthorized file reading",
                "A compiler lock that prevents code execution before compilation",
                "A hardware locking mechanism in x86 CPUs"
            ],
            "correct_option_index": 0,
            "explanation": "CPython's GIL prevents multi-core parallel execution of native Python bytecode within a single process. CPU-bound concurrency is typically achieved using the multiprocessing module or sub-interpreters."
        },
        {
            "id": 5,
            "topic": "Python Core",
            "question": "What is the difference between a generator and a regular list in Python?",
            "expected_key_points": [
                "Generators evaluate items lazily using yield one at a time",
                "Lists allocate all items in memory simultaneously",
                "Generators have O(1) memory footprint for large datasets",
                "Generators can only be iterated over once"
            ],
            "difficulty": "Medium",
            "quiz_options": [
                "Generators generate items lazily using yield, consuming minimal memory",
                "Generators are sorted lists with hash indices",
                "Lists are immutable whereas generators are mutable",
                "Generators can only store integer types"
            ],
            "correct_option_index": 0,
            "explanation": "Generators produce items on-demand using the iterator protocol, resulting in substantial memory savings when processing large data streams."
        }
    ],
    "dbms": [
        {
            "id": 6,
            "topic": "Transactions",
            "question": "Explain ACID properties in relational database management systems.",
            "expected_key_points": [
                "Atomicity: All operations complete or entire transaction aborts",
                "Consistency: Database transitions from one valid state to another satisfying all constraints",
                "Isolation: Concurrent transactions do not interfere with each other (e.g. Serializability)",
                "Durability: Committed changes survive system crashes and power failures"
            ],
            "difficulty": "Intermediate",
            "quiz_options": [
                "Atomicity, Consistency, Isolation, Durability",
                "Accuracy, Concurrency, Integrity, Durability",
                "Availability, Consistency, Isolation, Distribution",
                "Access, Concurrency, Indexing, Decoupling"
            ],
            "correct_option_index": 0,
            "explanation": "ACID ensures reliable transaction processing: Atomicity (all or nothing), Consistency (preserves invariants), Isolation (concurrency control), and Durability (persistence on disk)."
        }
    ]
}


def explain_concept(concept_name: str, target_audience: str = "college student") -> Dict[str, Any]:
    """Explains a technical concept in clear, structured language."""
    if is_llm_available():
        system_prompt = (
            "You are an encouraging, expert Computer Science professor explaining concepts to university students. "
            "Structure your answer with: 1) One-sentence Intuition, 2) Key Principles, 3) Real-world Analogy, "
            "4) Code snippet / Example, and 5) Common Placement/Viva Traps to avoid."
        )
        user_msg = f"Explain the concept of '{concept_name}' for a {target_audience}."
        try:
            res = chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
            )
            return {"concept": concept_name, "explanation": res["content"], "source": "LLM"}
        except LLMServiceError:
            pass

    # Fallback explanation
    return {
        "concept": concept_name,
        "explanation": (
            f"### Concept Overview: **{concept_name}**\n\n"
            f"**1. Core Intuition:**\n"
            f"`{concept_name}` is a fundamental architectural concept in software engineering and computer science, "
            f"designed to manage complexity, improve modularity, and ensure maintainable code.\n\n"
            f"**2. Key Characteristics:**\n"
            f"- Encapsulates responsibilities cleanly.\n"
            f"- Prevents tight coupling between different components.\n"
            f"- Standard topic in placement coding tests, technical interviews, and viva examinations.\n\n"
            f"**3. Practical Advice:**\n"
            f"Always explain the *trade-offs* (time vs memory, flexibility vs complexity) when asked about {concept_name} in viva.\n\n"
            f"> *Note: Connect your LLM API Key in Settings to get real-time dynamic explanations with custom code snippets.*"
        ),
        "source": "KnowledgeBase",
    }


def generate_interview_questions(topic: str = "java", count: int = 5) -> List[Dict[str, Any]]:
    """Generates technical interview questions with key evaluation points."""
    norm_topic = topic.lower()
    selected_questions: List[Dict[str, Any]] = []

    for key, q_list in OFFLINE_KNOWLEDGE_BANK.items():
        if key in norm_topic:
            selected_questions.extend(q_list)

    if not selected_questions:
        # Default fallback to java questions
        selected_questions = OFFLINE_KNOWLEDGE_BANK["java"]

    return selected_questions[:count]


def get_quiz_questions(topic: str = "java") -> List[Dict[str, Any]]:
    """Retrieves multiple choice quiz questions for practice."""
    norm_topic = topic.lower()
    for key, questions in OFFLINE_KNOWLEDGE_BANK.items():
        if key in norm_topic:
            return questions
    # Default return all questions
    all_q = []
    for q_list in OFFLINE_KNOWLEDGE_BANK.values():
        all_q.extend(q_list)
    return all_q


def evaluate_user_answer(
    question: str,
    user_answer: str,
    expected_points: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Evaluates a student's answer to an interview question.
    Gives a score out of 10, highlights strong points, and identifies missed gaps.
    """
    cleaned_ans = (user_answer or "").strip()
    if not cleaned_ans:
        return {
            "score": 0,
            "feedback": "No answer provided.",
            "strengths": [],
            "gaps": ["You did not submit an answer."],
            "model_answer": "Please write a response to receive feedback."
        }

    if is_llm_available():
        system_prompt = (
            "You are a strict but fair technical interviewer at a top tech company evaluating a campus placement candidate. "
            "Evaluate their answer to the interview question. Respond in JSON with keys:\n"
            "- score (integer 1-10)\n"
            "- feedback (concise evaluation summary)\n"
            "- strengths (list of strings)\n"
            "- gaps (list of strings with missing points or inaccuracies)\n"
            "- model_answer (concise ideal answer to ace the interview)"
        )
        user_prompt = f"Question: {question}\nCandidate Answer: {cleaned_ans}"
        if expected_points:
            user_prompt += f"\nExpected key points to check: {', '.join(expected_points)}"

        try:
            res = chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            # Try to parse JSON output
            raw = res["content"].strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw)
            return parsed
        except Exception:
            pass

    # Heuristic evaluation when offline
    score = 5
    strengths = []
    gaps = []

    if len(cleaned_ans) > 80:
        score += 2
        strengths.append("Detailed and comprehensive explanation.")
    else:
        gaps.append("Answer is somewhat brief; consider elaborating with internal mechanisms or examples.")

    if expected_points:
        matched = 0
        for pt in expected_points:
            # Check if key words appear
            words = [w.lower() for w in pt.split() if len(w) > 4]
            if any(w in cleaned_ans.lower() for w in words):
                matched += 1
        if matched >= len(expected_points) // 2:
            score += 2
            strengths.append("Addressed core technical terminology effectively.")
        else:
            gaps.append(f"Consider including key details such as: {expected_points[0]}")

    score = min(10, max(1, score))

    return {
        "score": score,
        "feedback": f"Good effort! You demonstrated understanding of the primary concept with a score of {score}/10.",
        "strengths": strengths or ["Attempted the technical explanation directly."],
        "gaps": gaps or ["Could provide more technical depth or code examples."],
        "model_answer": "An ideal answer covers the definition, the underlying data structures, why it matters for performance, and practical edge cases."
    }
