"""
Memory and Settings UI for PersonalAI.
Manages LLM API keys, provider presets, live connection diagnostics,
persistent memory records, and safe database management.
"""

import os
import streamlit as st
from dotenv import set_key, find_dotenv
from services.llm_service import (
    get_llm_config,
    is_api_key_configured,
    test_connection,
    get_connection_status,
    mask_api_key,
    reload_environment,
)
from agent.memory import list_memories, save_memory, delete_memory, clear_all_memories
from database.db import reset_database, get_db_path

# Presets configuration dictionary
PROVIDER_PRESETS = {
    "Custom / Manual": {
        "base_url": "",
        "model": "gpt-4o-mini",
        "description": "Enter your own custom OpenAI-compatible endpoint and model name.",
    },
    "OpenAI (Official)": {
        "base_url": "",
        "model": "gpt-4o-mini",
        "description": "Official OpenAI endpoint (https://api.openai.com/v1). High reliability & performance.",
    },
    "Groq (Free Tier & Fast)": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "description": "Ultra-fast inference with free tier available at console.groq.com.",
    },
    "Google Gemini (OpenAI Endpoint)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash",
        "description": "Google AI Studio API key with generous free tier via standard OpenAI-compatible URL.",
    },
    "OpenRouter (Aggregator)": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "description": "Multi-model router supporting hundreds of open and commercial models.",
    },
    "Ollama (Local & Free)": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1",
        "description": "Runs completely locally on your machine. No API key or internet required.",
    },
}


def render_settings():
    st.title("⚙️ Memory & Settings")
    st.caption("Configure AI providers, test live connection health, inspect persistent memories, and manage data.")

    tab_api, tab_mem, tab_db = st.tabs([
        "🔑 AI Provider & Connection",
        "🧠 Persistent Memory Store",
        "🗄️ Database Management",
    ])

    # --- TAB 1: API Configuration ---
    with tab_api:
        st.subheader("AI Provider & Model Configuration")

        conn_status = get_connection_status()
        curr_cfg = get_llm_config()

        # Diagnostic Status Banner
        if conn_status["verified"]:
            st.success(
                f"### 🟢 Online AI Mode Active\n"
                f"- **Provider:** {conn_status['provider']}\n"
                f"- **Model:** `{conn_status['model']}`\n"
                f"- **API Key:** `{conn_status['masked_key']}`\n"
                f"- **Base URL:** `{conn_status['base_url'] or 'Default (https://api.openai.com/v1)'}`\n"
                f"- **Latency:** {conn_status.get('latency_ms', 'N/A')} ms"
            )
        elif conn_status["mode"] == "Online AI Error":
            st.error(
                f"### 🔴 Online AI Connection Failed\n"
                f"- **Error:** {conn_status['error']}\n"
                f"- **Provider:** {conn_status['provider']} | **Model:** `{conn_status['model']}`\n"
                f"- **Configured Key:** `{conn_status['masked_key']}`\n\n"
                f"👉 *The system is temporarily using Offline Mode to keep task management functional. "
                f"Please verify your credentials below and click 'Test AI Connection'.*"
            )
        elif conn_status["configured"]:
            st.warning(
                f"### 🟡 AI Configured (Untested)\n"
                f"- **Provider:** {conn_status['provider']}\n"
                f"- **Model:** `{conn_status['model']}`\n"
                f"- **Configured Key:** `{conn_status['masked_key']}`\n\n"
                f"👉 *Click **🔌 Test AI Connection** below to verify that your provider accepts requests.*"
            )
        else:
            st.info(
                f"### 🟠 Offline Mode Active\n"
                f"No API key is configured. PersonalAI is operating in **Offline Mode** using local rule dispatchers.\n\n"
                f"To activate **Online AI Mode**, choose a provider preset below, enter your API key, and click **Save & Test**."
            )

        st.divider()

        # Provider Preset Selector
        st.markdown("#### 1. Select Provider Preset or Custom")
        preset_choice = st.selectbox(
            "Quick Provider Preset",
            list(PROVIDER_PRESETS.keys()),
            index=0,
            help="Selecting a preset pre-fills recommended endpoint URLs and model names.",
        )

        preset_data = PROVIDER_PRESETS[preset_choice]
        st.caption(f"ℹ️ {preset_data['description']}")

        # Default prefill values
        default_base_url = preset_data["base_url"] if preset_choice != "Custom / Manual" else (curr_cfg["base_url"] or "")
        default_model = preset_data["model"] if preset_choice != "Custom / Manual" else curr_cfg["model"]

        st.markdown("#### 2. Configure Credentials")
        with st.form("api_config_form"):
            new_key = st.text_input(
                "API Key (OPENAI_API_KEY) *",
                type="password",
                placeholder="sk-..." if preset_choice != "Ollama (Local & Free)" else "ollama (or leave blank for local)",
                help="Your private API key. Masked and never logged or exposed in logs.",
            )
            new_model = st.text_input(
                "Model Identifier (OPENAI_MODEL) *",
                value=default_model,
                placeholder="e.g. gpt-4o-mini, llama-3.3-70b-versatile, gemini-2.5-flash",
            )
            new_base_url = st.text_input(
                "Endpoint Base URL (OPENAI_BASE_URL)",
                value=default_base_url,
                placeholder="Leave empty for OpenAI, or enter provider URL",
                help="Base endpoint URL. E.g., https://api.groq.com/openai/v1 or https://generativelanguage.googleapis.com/v1beta/openai/",
            )

            submit_save = st.form_submit_button("💾 Save AI Configuration", use_container_width=True)

        if submit_save:
            env_file = find_dotenv() or os.path.join(os.getcwd(), ".env")
            if not os.path.exists(env_file):
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write("# PersonalAI Environment Configuration\n")

            if new_key.strip():
                os.environ["OPENAI_API_KEY"] = new_key.strip()
                set_key(env_file, "OPENAI_API_KEY", new_key.strip())
            elif preset_choice == "Ollama (Local & Free)":
                os.environ["OPENAI_API_KEY"] = "ollama"
                set_key(env_file, "OPENAI_API_KEY", "ollama")

            os.environ["OPENAI_MODEL"] = new_model.strip() or "gpt-4o-mini"
            set_key(env_file, "OPENAI_MODEL", new_model.strip() or "gpt-4o-mini")

            if new_base_url.strip():
                os.environ["OPENAI_BASE_URL"] = new_base_url.strip()
                set_key(env_file, "OPENAI_BASE_URL", new_base_url.strip())
            else:
                os.environ.pop("OPENAI_BASE_URL", None)
                set_key(env_file, "OPENAI_BASE_URL", "")

            reload_environment()
            st.success("✅ Configuration saved! Click 'Test AI Connection' below to verify.")
            st.rerun()

        # Action Buttons (Test & Clear)
        st.markdown("#### 3. Diagnostics & Actions")
        btn_col1, btn_col2 = st.columns([1, 1])

        with btn_col1:
            if st.button("🔌 Test AI Connection", type="primary", use_container_width=True):
                with st.spinner("Connecting to AI endpoint and validating model response..."):
                    result = test_connection()

                if result["success"]:
                    st.success(f"🎉 **{result['message']}**\n\nOnline AI Mode is now active!")
                    st.rerun()
                else:
                    st.error(f"❌ **Connection Failed:**\n\n{result['error']}")

        with btn_col2:
            if is_api_key_configured():
                if st.button("🗑️ Clear Key (Revert to Offline Mode)", use_container_width=True):
                    env_file = find_dotenv() or os.path.join(os.getcwd(), ".env")
                    os.environ.pop("OPENAI_API_KEY", None)
                    if os.path.exists(env_file):
                        set_key(env_file, "OPENAI_API_KEY", "")
                    reload_environment()
                    st.toast("API Key cleared. App reverted to Offline Mode.")
                    st.rerun()

        # Step-by-Step Provider Setup Guides
        st.divider()
        st.markdown("#### 📖 Provider Setup Instructions")

        with st.expander("⚡ Option A: Groq (Recommended — Ultra-Fast & Free Tier Available)"):
            st.markdown(
                """
                1. Go to [console.groq.com/keys](https://console.groq.com/keys) and create a free account.
                2. Click **Create API Key** and copy your key (`gsk_...`).
                3. In PersonalAI Settings:
                   - Select Preset: **Groq (Free Tier & Fast)**
                   - API Key: Paste your `gsk_...` key
                   - Model: `llama-3.3-70b-versatile`
                   - Base URL: `https://api.groq.com/openai/v1`
                4. Click **Save** then **Test AI Connection**.
                """
            )

        with st.expander("🤖 Option B: OpenAI (Official gpt-4o-mini)"):
            st.markdown(
                """
                1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
                2. Generate a secret key (`sk-proj-...`).
                3. In PersonalAI Settings:
                   - Select Preset: **OpenAI (Official)**
                   - API Key: Paste your `sk-...` key
                   - Model: `gpt-4o-mini`
                   - Base URL: *(Leave empty)*
                4. Click **Save** then **Test AI Connection**.
                """
            )

        with st.expander("✨ Option C: Google Gemini (Generous Free Tier via OpenAI Endpoint)"):
            st.markdown(
                """
                1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and generate a Gemini API key.
                2. In PersonalAI Settings:
                   - Select Preset: **Google Gemini (OpenAI Endpoint)**
                   - API Key: Paste your Gemini key (`AIzaSy...`)
                   - Model: `gemini-2.5-flash`
                   - Base URL: `https://generativelanguage.googleapis.com/v1beta/openai/`
                3. Click **Save** then **Test AI Connection**.
                """
            )

        with st.expander("💻 Option D: Ollama (100% Local & Free, Zero Internet Required)"):
            st.markdown(
                """
                1. Install Ollama from [ollama.com](https://ollama.com).
                2. In your terminal, run: `ollama run llama3.1`
                3. In PersonalAI Settings:
                   - Select Preset: **Ollama (Local & Free)**
                   - Base URL: `http://localhost:11434/v1`
                   - Model: `llama3.1`
                4. Click **Save** then **Test AI Connection**.
                """
            )

    # --- TAB 2: Persistent Memory Store ---
    with tab_mem:
        st.subheader("Persistent User Memory Store")
        st.markdown(
            "PersonalAI stores user preferences, academic context, and profile facts in SQLite. "
            "These records are dynamically injected into the agent's system prompt during conversations."
        )

        with st.expander("➕ Add Explicit User Preference or Fact"):
            with st.form("add_memory_form", clear_on_submit=True):
                m_cat = st.selectbox("Category", ["preference", "fact", "context", "profile", "study_note"])
                m_key = st.text_input("Key Identifier", placeholder="e.g. target_role, preferred_framework, college_name")
                m_val = st.text_area("Value / Note", placeholder="e.g. Java Backend Developer, prefers concise explanations")
                if st.form_submit_button("Save Memory"):
                    if m_key.strip() and m_val.strip():
                        save_memory(category=m_cat, key=m_key.strip(), value=m_val.strip())
                        st.success(f"Saved [{m_cat}] {m_key}")
                        st.rerun()
                    else:
                        st.error("Key and Value are required.")

        mems = list_memories()
        st.write(f"**Stored Memory Records ({len(mems)} items):**")

        if not mems:
            st.caption("No persistent memories stored yet.")
        else:
            for m in mems:
                m_c1, m_c2, m_c3 = st.columns([1.5, 4, 1])
                m_c1.markdown(f"**[{m['category'].upper()}]** `{m['key']}`")
                m_c2.markdown(m["value"])
                if m_c3.button("Delete", key=f"del_mem_{m['id']}"):
                    delete_memory(m["id"])
                    st.toast(f"Deleted memory '{m['key']}'.")
                    st.rerun()
                st.markdown("<hr style='margin: 0.3rem 0;'>", unsafe_allow_html=True)

        if mems and st.button("🗑️ Clear All Memories", key="clear_all_mem_btn"):
            clear_all_memories()
            st.toast("All memories cleared.")
            st.rerun()

    # --- TAB 3: Database Management ---
    with tab_db:
        st.subheader("Database Maintenance")
        st.write(f"Database File: `{get_db_path()}`")

        st.warning("⚠️ **Danger Zone:** Wiping the database permanently deletes all tasks, goals, memories, and logs.")
        confirm_reset = st.checkbox("I understand that this will erase all stored tasks and goals permanently.")
        if confirm_reset:
            if st.button("🔥 Reset Database & Reinitialize Tables", type="primary"):
                reset_database()
                st.success("Database has been reset to an empty state with clean schemas.")
                st.rerun()
