"""
AI Assistant Chat Interface for PersonalAI.
Provides interactive conversational interface with tool-calling execution traces,
smart prompt suggestions, and persistent session state.
"""

import streamlit as st
from agent.orchestrator import run_agent_turn
from services.llm_service import is_llm_available, get_llm_config


def render_assistant_chat():
    st.title("🤖 AI Personal Assistant (Agentic Chat)")
    st.caption("Autonomous Agent Loop: Planning ➔ Tool Selection ➔ Python Execution ➔ Observation ➔ Response")

    from services.llm_service import get_connection_status
    conn_status = get_connection_status()

    if conn_status["verified"]:
        st.success(
            f"🟢 **Online AI Mode Active:** Connected to **{conn_status['provider']}** "
            f"(Model: `{conn_status['model']}`). Multi-step agent reasoning and tool calling are enabled."
        )
    elif conn_status["mode"] == "Online AI Error":
        st.error(
            f"🔴 **AI Connection Error:** {conn_status['error']}\n\n"
            "Go to **Settings** to update your API key or model. Offline fallback commands remain available."
        )
    elif conn_status["configured"]:
        st.info(
            f"🟡 **AI Configured ({conn_status['provider']}):** Key set for model `{conn_status['model']}`. "
            "Click **Test AI Connection** in Settings to verify live status."
        )
    else:
        st.warning(
            "ℹ️ **Running in Offline Agent Mode:** No `OPENAI_API_KEY` is configured. "
            "You can still interactively run real tool commands (e.g., 'List tasks', 'Recommend next task', 'Prepare for Java interview in 7 days'). "
            "To enable live multi-turn reasoning with an LLM, provide your API key in the **Settings** tab."
        )

    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am **PersonalAI**, your autonomous personal assistant and CSE academic mentor. "
                    "I can manage your tasks, create structured 7-day interview plans, track deadlines, and recall your study preferences.\n\n"
                    "How can I help you achieve your goals today?"
                ),
                "logs": None,
            }
        ]

    # Quick prompt shortcuts
    st.markdown("**Suggested Quick Prompts:**")
    prompt_cols = st.columns(4)
    suggested_prompt = None

    if prompt_cols[0].button("📅 7-Day Java Interview Prep", use_container_width=True):
        suggested_prompt = "Help me prepare for my Java interview in 7 days."
    if prompt_cols[1].button("🎯 What should I do next?", use_container_width=True):
        suggested_prompt = "What task should I focus on next based on my deadlines and priority?"
    if prompt_cols[2].button("📋 Show my pending tasks", use_container_width=True):
        suggested_prompt = "List all my pending tasks."
    if prompt_cols[3].button("📊 Show dashboard stats", use_container_width=True):
        suggested_prompt = "Give me a summary of my tasks and completion progress."

    # Render previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # If tool execution logs exist, show the expandable agent trace
            logs = msg.get("logs")
            if logs and logs.get("tool_calls"):
                with st.expander(f"🛠️ Agent Tool Execution Trace ({logs['tool_calls_count']} tools called, {logs.get('iterations', 1)} iterations)", expanded=False):
                    st.caption(f"Execution Mode: `{logs.get('mode', 'LLM')}`")
                    for idx, tc in enumerate(logs["tool_calls"], 1):
                        st.markdown(f"**Step {idx}: Called `{tc['tool']}`**")
                        st.json({"arguments": tc["arguments"], "result": tc["result"]})

    # Chat input
    user_prompt = st.chat_input("Ask PersonalAI to plan a goal, manage tasks, or recall notes...") or suggested_prompt

    if user_prompt:
        # Append user message
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Run agent turn
        with st.chat_message("assistant"):
            with st.spinner("PersonalAI is reasoning and choosing tools..."):
                result = run_agent_turn(
                    user_input=user_prompt,
                    chat_history=st.session_state.messages[:-1],
                )

            st.markdown(result["response"])

            logs = result.get("logs")
            if logs and logs.get("tool_calls"):
                with st.expander(f"🛠️ Agent Tool Execution Trace ({logs['tool_calls_count']} tools called)", expanded=True):
                    st.caption(f"Execution Mode: `{logs.get('mode', 'LLM')}`")
                    for idx, tc in enumerate(logs["tool_calls"], 1):
                        st.markdown(f"**Step {idx}: Called `{tc['tool']}`**")
                        st.json({"arguments": tc["arguments"], "result": tc["result"]})

        # Save assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["response"],
            "logs": result.get("logs"),
        })

    # Footer actions
    col_clear, _ = st.columns([1, 4])
    with col_clear:
        if st.button("🗑️ Clear Conversation", key="clear_chat_btn"):
            st.session_state.messages = []
            st.rerun()
