"""
Study and Interview Helper UI for PersonalAI.
Supports concept explanation, placement interview question simulation,
candidate answer evaluation, and interactive quizzes.
"""

import streamlit as st
from services.study_service import (
    explain_concept,
    generate_interview_questions,
    get_quiz_questions,
    evaluate_user_answer,
)


def render_study_helper():
    st.title("🎓 Study & Placement Interview Helper")
    st.caption("AI-powered preparation assistant tailored for CSE placements, viva questions, and technical exams.")

    tab_explain, tab_practice, tab_quiz = st.tabs([
        "💡 Concept Explainer",
        "🎯 Mock Interview & Answer Evaluation",
        "📝 Practice Quiz",
    ])

    # --- TAB 1: Concept Explainer ---
    with tab_explain:
        st.subheader("Understand Any Technical Concept")
        st.markdown("Get a clear, intuitive explanation with analogies and common viva pitfalls to watch out for.")

        col_in1, col_in2 = st.columns([3, 1])
        with col_in1:
            concept_input = st.text_input(
                "Enter concept name",
                placeholder="e.g. HashMap collision resolution in Java 8, ACID properties, GIL in Python...",
            )
        with col_in2:
            audience = st.selectbox("Target Audience", ["College Viva Student", "Placement Interview Candidate", "Absolute Beginner"])

        # Quick concept buttons
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("Java String Pool"):
            concept_input = "Java String Constant Pool and Immutability"
        if b2.button("Python GIL"):
            concept_input = "Python Global Interpreter Lock (GIL)"
        if b3.button("Database Normalization"):
            concept_input = "Database Normalization (1NF to BCNF)"
        if b4.button("Process vs Thread"):
            concept_input = "Process vs Thread and Context Switching"

        if st.button("🔍 Explain Concept", type="primary", use_container_width=True):
            if concept_input.strip():
                with st.spinner("Generating clear explanation and viva notes..."):
                    result = explain_concept(concept_input.strip(), target_audience=audience)
                st.markdown(result["explanation"])
                st.caption(f"Source: {result['source']}")
            else:
                st.warning("Please enter a concept name.")

    # --- TAB 2: Mock Interview & Answer Evaluation ---
    with tab_practice:
        st.subheader("Placement Interview Practice")
        st.markdown("Practice answering real CSE placement interview questions and receive instant scoring and feedback.")

        topic_choice = st.selectbox("Select Topic", ["Java", "Python", "DBMS"], key="mock_topic_select")
        questions = generate_interview_questions(topic=topic_choice, count=5)

        q_titles = [f"Q{idx}: {q['question']}" for idx, q in enumerate(questions, 1)]
        selected_q_idx = st.selectbox("Choose a Question to Answer", range(len(q_titles)), format_func=lambda i: q_titles[i])
        selected_q = questions[selected_q_idx]

        st.info(f"**Difficulty:** `{selected_q['difficulty']}` | **Topic Area:** {selected_q['topic']}")
        st.markdown(f"### {selected_q['question']}")

        user_answer = st.text_area(
            "Write your answer as you would speak it in an interview:",
            placeholder="Structure your answer with definition, internal working, and practical example...",
            height=130,
            key=f"user_ans_text_{selected_q['id']}",
        )

        if st.button("🚀 Submit Answer for Evaluation", type="primary"):
            if not user_answer.strip():
                st.error("Please enter your answer before submitting.")
            else:
                with st.spinner("Evaluating your response against technical rubrics..."):
                    eval_result = evaluate_user_answer(
                        question=selected_q["question"],
                        user_answer=user_answer.strip(),
                        expected_points=selected_q.get("expected_key_points"),
                    )

                score = eval_result.get("score", 5)
                score_color = "green" if score >= 8 else "orange" if score >= 5 else "red"
                st.markdown(f"### Evaluation Score: :{score_color}[{score}/10]")
                st.write(eval_result.get("feedback", ""))

                c_str, c_gaps = st.columns(2)
                with c_str:
                    st.success("**Strengths Identified:**")
                    for s in eval_result.get("strengths", []):
                        st.write(f"- {s}")
                with c_gaps:
                    st.warning("**Points for Improvement:**")
                    for g in eval_result.get("gaps", []):
                        st.write(f"- {g}")

                with st.expander("🌟 View Ideal Model Answer", expanded=True):
                    st.markdown(eval_result.get("model_answer", ""))

    # --- TAB 3: Interactive Practice Quiz ---
    with tab_quiz:
        st.subheader("Multiple Choice Quick Assessment")
        quiz_topic = st.selectbox("Select Quiz Topic", ["Java", "Python", "DBMS"], key="quiz_topic_sel")
        quiz_items = get_quiz_questions(topic=quiz_topic)

        user_choices = {}
        with st.form("interactive_quiz_form"):
            for idx, q in enumerate(quiz_items, 1):
                st.markdown(f"**Question {idx}: {q['question']}**")
                choice = st.radio(
                    "Select an option:",
                    q["quiz_options"],
                    key=f"quiz_opt_{q['id']}",
                    index=None,
                )
                user_choices[q["id"]] = choice
                st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

            quiz_submitted = st.form_submit_button("📊 Submit Quiz and See Score", use_container_width=True)

        if quiz_submitted:
            correct_count = 0
            total_count = len(quiz_items)
            st.divider()

            for q in quiz_items:
                sel = user_choices.get(q["id"])
                correct_opt = q["quiz_options"][q["correct_option_index"]]
                is_correct = sel == correct_opt

                if is_correct:
                    correct_count += 1
                    st.success(f"✅ **{q['question']}**\n\nYour answer: *{sel}*")
                else:
                    st.error(f"❌ **{q['question']}**\n\nYour answer: *{sel or 'Unanswered'}*\n\n**Correct Answer:** *{correct_opt}*")

                st.caption(f"Explanation: {q['explanation']}")
                st.write("")

            pct = int((correct_count / total_count) * 100) if total_count > 0 else 0
            st.subheader(f"🏁 Final Quiz Result: {correct_count} / {total_count} ({pct}%)")
            if pct >= 80:
                st.balloons()
