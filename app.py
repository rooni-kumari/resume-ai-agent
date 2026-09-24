"""app.py - the web page (Streamlit). Run with: streamlit run app.py"""

import streamlit as st

from tools import read_pdf
from agent import ResumeAgent


st.set_page_config(
    page_title="AI Resume Assistant",
    layout="wide"
)

st.title("AI Resume Assistant Agent")

st.caption(
    "Upload your resume, choose a target role, and get a role-focused review."
)


# ---------------- Sidebar: inputs ---------------

with st.sidebar:

    st.header("1. Your resume")

    uploaded = st.file_uploader(
        "Upload a PDF resume",
        type=["pdf"]
    )

    pasted = st.text_area(
        "...or paste the resume text",
        height=180
    )

    st.header("2. Target role(s)")

    count = st.radio(
        "How many roles to compare?",
        [1, 2, 3],
        horizontal=True
    )

    targets = []

    for i in range(count):

        targets.append(
            st.text_area(
                f"Role {i + 1}: job title or full job description",
                key=f"role_{i}",
                height=110
            )
        )

    analyze_clicked = st.button(
        "Analyze my resume",
        type="primary"
    )


# ---------------- Run the agent ---------------

if analyze_clicked:

    resume_text = ""

    try:

        resume_text = (
            read_pdf(uploaded)
            if uploaded
            else pasted.strip()
        )

    except Exception as e:

        st.error(
            f"Could not read that PDF ({e}). "
            "Try pasting the text instead."
        )

    targets = [
        t.strip()
        for t in targets
        if t.strip()
    ]

    if len(resume_text) < 150:

        st.error(
            "Please upload a resume PDF or paste at least a few lines of it."
        )

    elif not targets:

        st.error(
            "Please enter at least one target role or job description."
        )

    else:

        try:

            agent = ResumeAgent(resume_text)

            with st.status(
                "The agent is working ...",
                expanded=True
            ) as status:

                analysis = agent.analyze_all(
                    targets,
                    progress=st.write
                )

                status.update(
                    label="Analysis complete",
                    state="complete"
                )

            st.session_state["agent"] = agent

            st.session_state["analysis"] = analysis

            st.session_state.pop(
                "improved",
                None
            )

        except Exception as e:

            st.error(
                f"Something went wrong: {e}"
            )


analysis = st.session_state.get("analysis")

agent = st.session_state.get("agent")


if not analysis:

    st.info(
        "Fill in the sidebar and click **Analyze my resume**. "
        "Tip: sample files are in the sample_data folder."
    )

    st.stop()


roles = analysis["roles"]

completeness = analysis["completeness"]


tab_names = [
    "Completeness",
    "Role fit"
]

if len(roles) > 1:
    tab_names.append("Compare roles")

tab_names += [
    "Improved content",
    "Final review",
    "Agent trace"
]


tabs = dict(
    zip(
        tab_names,
        st.tabs(tab_names)
    )
)


# ---------------- Tab: completeness ---------------

with tabs["Completeness"]:

    st.subheader(
        "Resume completeness report"
    )

    st.metric(
        "Completeness score",
        f"{completeness['score']} / 100"
    )

    st.progress(
        completeness["score"] / 100
    )

    st.caption(
        f"Word count: {completeness['word_count']}"
    )

    for c in completeness["checks"]:

        if c["passed"]:

            st.write(
                f"[PASS] {c['name']}"
            )

        else:

            st.write(
                f"[FIX] **{c['name']}** - {c['tip']}"
            )


# ---------------- Tab: role fit ---------------

with tabs["Role fit"]:

    for r in roles:

        fit = r["fit"]

        role = r["role"]

        st.subheader(
            role["role_title"]
        )

        st.metric(
            "Role match score",
            f"{fit['score']} / 100"
        )

        st.progress(
            fit["score"] / 100
        )

        col1, col2 = st.columns(2)

        with col1:

            st.markdown(
                "**Skills you already show**"
            )

            st.write(
                ", ".join(
                    fit["must_matched"]
                    + fit["nice_matched"]
                )
                or "None found"
            )

            st.markdown(
                "**Strengths**"
            )

            for s in fit["strengths"]:

                st.write(
                    f"- {s}"
                )

        with col2:

            st.markdown(
                "**Missing required skills**"
            )

            st.write(
                ", ".join(
                    fit["must_missing"]
                )
                or "None - great!"
            )

            st.markdown(
                "**Weak areas**"
            )

            for w in fit["weak_areas"]:

                st.write(
                    f"- {w}"
                )

        st.markdown(
            "**Specific suggestions**"
        )

        for sug in fit["suggestions"]:

            if isinstance(sug, dict):

                st.write(
                    f"- **{sug.get('section', '')}**: "
                    f"{sug.get('issue', '')} -> "
                    f"{sug.get('fix', '')}"
                )

            else:

                st.write(
                    f"- {sug}"
                )

        st.divider()


# ---------------- Tab: compare roles ---------------

if "Compare roles" in tabs:

    with tabs["Compare roles"]:

        st.subheader(
            "Which role fits you best?"
        )

        ranked = sorted(
            roles,
            key=lambda r: r["fit"]["score"],
            reverse=True
        )

        rows = [
            {
                "Role": r["role"]["role_title"],
                "Match score": r["fit"]["score"],
                "Skills matched": len(
                    r["fit"]["must_matched"]
                ),
                "Skills missing": ", ".join(
                    r["fit"]["must_missing"]
                )
            }
            for r in ranked
        ]

        st.dataframe(rows)

        st.bar_chart(
            {
                "Role": [
                    r["role"]["role_title"]
                    for r in ranked
                ],
                "Score": [
                    r["fit"]["score"]
                    for r in ranked
                ]
            },
            x="Role",
            y="Score"
        )

        st.success(
            f"Best match: "
            f"{ranked[0]['role']['role_title']}"
        )


# ---------------- Choose a role for improvements ---------------

titles = [
    r["role"]["role_title"]
    for r in roles
]


with tabs["Improved content"]:

    choice = st.selectbox(
        "Improve my resume for:",
        titles
    )

    if st.button(
        "Generate improved content and final review"
    ):

        try:

            with st.spinner(
                "Rewriting and double-checking for made-up facts ..."
            ):

                chosen = roles[
                    titles.index(choice)
                ]

                out = agent.improve_and_review(
                    chosen,
                    completeness
                )

                out["role_title"] = choice

                st.session_state["improved"] = out

        except Exception as e:

            st.error(
                f"Something went wrong: {e}"
            )

    out = st.session_state.get(
        "improved"
    )

    if out:

        imp = out["improved"]

        st.subheader(
            f"Improved content for {out['role_title']}"
        )

        st.markdown(
            "**New summary**"
        )

        st.write(
            imp["summary"]
        )

        st.markdown(
            "**Rewritten bullets**"
        )

        for b in imp["rewritten_bullets"]:

            if isinstance(b, dict):

                st.write(
                    f"Before: {b.get('original', '')}"
                )

                st.success(
                    f"After: {b.get('improved', '')}"
                )

        st.markdown(
            "**Skills section**"
        )

        st.write(
            imp["skills_section"]
        )

        if imp["critic_issues"]:

            st.warning(
                "The agent's honesty check found and fixed: "
                + "; ".join(
                    str(i)
                    for i in imp["critic_issues"]
                )
            )

        st.caption(
            "Replace anything in [brackets] with your real numbers."
        )

    else:

        st.info(
            "Choose a role and click the button above."
        )


# ---------------- Tab: final review ---------------

with tabs["Final review"]:

    out = st.session_state.get(
        "improved"
    )

    if not out:

        st.info(
            "Generate improved content first (previous tab)."
        )

    else:

        rev = out["review"]

        st.subheader(
            f"Final review for {out['role_title']}"
        )

        st.metric(
            "Overall score",
            f"{rev['overall_score']} / 100"
        )

        st.progress(
            rev["overall_score"] / 100
        )

        st.write(
            rev.get("verdict", "")
        )

        st.markdown(
            "**Top strengths**"
        )

        for s in rev.get(
            "top_strengths",
            []
        ):

            st.write(
                f"- {s}"
            )

        st.markdown(
            "**Priority fixes**"
        )

        for n, f in enumerate(
            rev.get("priority_fixes", []),
            start=1
        ):

            st.write(
                f"{n}. {f}"
            )

        st.markdown(
            "**Section ratings**"
        )

        ratings = rev.get(
            "section_ratings",
            {}
        )

        if isinstance(ratings, dict):

            st.table(
                {
                    "Section": list(
                        ratings.keys()
                    ),
                    "Rating": list(
                        ratings.values()
                    )
                }
            )

        st.markdown(
            "**Next steps this week**"
        )

        for s in rev.get(
            "next_steps",
            []
        ):

            st.write(
                f"- {s}"
            )

        lines = [
            f"# Resume review - {out['role_title']}",
            f"Overall score: {rev['overall_score']}/100",
            "",
            rev.get("verdict", ""),
            "",
            "## Priority fixes"
        ]

        lines += [
            f"{n}. {f}"
            for n, f in enumerate(
                rev.get("priority_fixes", []),
                1
            )
        ]

        lines += [
            "",
            "## New summary",
            out["improved"]["summary"],
            "",
            "## Rewritten bullets"
        ]

        for b in out["improved"]["rewritten_bullets"]:

            if isinstance(b, dict):

                lines.append(
                    f"- {b.get('improved', '')}"
                )

        st.download_button(
            "Download review (.md)",
            "\n".join(lines),
            file_name="resume_review.md"
        )


# ---------------- Tab: agent trace ---------------

with tabs["Agent trace"]:

    st.subheader(
        "What the agent did, step by step"
    )

    st.caption(
        "Every tool call the agent made. "
        "Use this to explain the system to judges."
    )

    st.table(
        agent.trace
    )