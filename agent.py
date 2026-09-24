"""agent.py - the 'brain'. It plans, calls tools, checks its own work, and keeps a trace."""

import time

from llm import ask

from tools import (
    extract_skills,
    skill_match,
    completeness_report,
    find_weak_bullets,
    preset_for,
)


SYSTEM = (
    "You are an expert career coach and technical recruiter helping college students "
    "get internships. Be specific, honest and encouraging. NEVER invent facts about the "
    "candidate: no fake tools, numbers, companies, degrees or achievements."
)


def as_list(value):
    return value if isinstance(value, list) else []


class ResumeAgent:

    def __init__(self, resume_text):
        self.resume_text = resume_text
        self.trace = []    # every step the agent takes (shown in the UI)
        self.memory = {}   # things the agent remembers: parsed resume, role results

    # ---------- helpers ---------

    def log(self, tool, note):
        self.trace.append({
            "time": time.strftime("%H:%M:%S"),
            "tool": tool,
            "note": note
        })

    # ---------- TOOL 1: understand the resume ---------

    def parse_resume(self):

        if "resume" in self.memory:
            self.log("parse_resume", "Used cached result (memory)")
            return self.memory["resume"]

        prompt = f"""
Extract this resume into JSON with exactly these keys:
name, email, phone, links (list), summary, education (list of strings),
skills (list of strings), projects (list of objects: name, description, tech),
experience (list of objects: title, org, description), certifications (list),
achievements (list). Use "" or [] when something is missing. Do not invent anything.

RESUME:
{self.resume_text}
"""

        data = ask(
            prompt,
            SYSTEM,
            as_json=True
        )

        if not isinstance(data, dict):
            data = {}

        self.memory["resume"] = data

        self.log(
            "parse_resume",
            f"Found {len(as_list(data.get('projects')))} projects, "
            f"{len(as_list(data.get('skills')))} skills"
        )

        return data

    # ---------- TOOL 2: understand the target role ---------

    def analyze_role(self, target):

        text = target.strip()

        is_name_only = len(text.split()) <= 6

        kind = (
            "a job title only"
            if is_name_only
            else "a full job description"
        )

        prompt = f"""
The user gave {kind} for a target role:

\"\"\"{text}\"\"\"

Return JSON with keys:

role_title (string),

must_have_skills (list, max 10, each a SHORT skill/tool name of 1-3 words such as
"Python", "SQL", "Power BI", "REST API"),

nice_to_have_skills (list, max 6, same style),

keywords (list, max 8, words an ATS would scan for),

responsibilities (list, max 5, short).

If only a title was given, list what a typical entry-level/internship role needs.
"""

        role = ask(
            prompt,
            SYSTEM,
            as_json=True
        )

        if not isinstance(role, dict):
            role = {}

        must = [
            m
            for m in as_list(role.get("must_have_skills"))
            if isinstance(m, str)
        ]

        if len(must) < 4:
            # AI gave too little -> add skills spotted in the text itself
            existing = [m.lower() for m in must]

            must += [
                s
                for s in extract_skills(text)
                if s.lower() not in existing
            ]

        if not must:
            # safety net if the AI returned nothing useful
            must = preset_for(text)

        role["must_have_skills"] = must[:12]

        role["nice_to_have_skills"] = [
            n
            for n in as_list(role.get("nice_to_have_skills"))
            if isinstance(n, str)
        ]

        role["role_title"] = (
            role.get("role_title")
            or text[:40]
        )

        self.log(
            "analyze_role",
            f"'{role['role_title']}': "
            f"{len(role['must_have_skills'])} must-have skills identified"
        )

        return role

    # ---------- TOOL 3: score the match + find gaps ---------

    def analyze_fit(self, role):

        must = skill_match(
            self.resume_text,
            role["must_have_skills"]
        )

        nice = skill_match(
            self.resume_text,
            role["nice_to_have_skills"]
        )

        if role["nice_to_have_skills"]:
            score = round(
                0.7 * must["percent"]
                + 0.3 * nice["percent"]
            )
        else:
            score = must["percent"]

        self.log(
            "skill_match",
            f"{role['role_title']}: {score}/100 "
            f"(missing: {', '.join(must['missing']) or 'none'})"
        )

        prompt = f"""
Target role: {role['role_title']}

Skills the resume already shows:
{must['matched'] + nice['matched']}

Required skills NOT found in the resume:
{must['missing']}

RESUME:
{self.resume_text}

Return JSON with keys:

strengths (list, max 4, specific to THIS resume),

weak_areas (list, max 5, e.g. vague bullets, missing sections, no metrics),

suggestions (list, max 6, each an object: section, issue, fix),

keywords_to_add (list, max 8 keywords the resume should honestly include).

Only recommend adding a skill if the candidate could truthfully claim it
based on the resume; otherwise suggest learning it or a project to prove it.
"""

        insights = ask(
            prompt,
            SYSTEM,
            as_json=True
        )

        if not isinstance(insights, dict):
            insights = {}

        self.log(
            "analyze_fit",
            "Strengths, weak areas and suggestions generated"
        )

        return {
            "score": score,
            "must_matched": must["matched"],
            "must_missing": must["missing"],
            "nice_matched": nice["matched"],
            "nice_missing": nice["missing"],
            "strengths": as_list(
                insights.get("strengths")
            ),
            "weak_areas": as_list(
                insights.get("weak_areas")
            ),
            "suggestions": as_list(
                insights.get("suggestions")
            ),
            "keywords_to_add": as_list(
                insights.get("keywords_to_add")
            ),
        }

    # ---------- MAIN JOB 1: analyze one or more roles ---------

    def analyze_all(self, targets, progress=None):

        def say(msg):
            self.log("planner", msg)

            if progress:
                progress(msg)

        say(
            f"Plan: parse resume -> completeness check -> "
            f"analyze {len(targets)} role(s)"
            + (
                " -> compare roles"
                if len(targets) > 1
                else ""
            )
        )

        say("Reading the resume ...")

        resume = self.parse_resume()

        say("Running the completeness check ...")

        completeness = completeness_report(
            self.resume_text
        )

        self.log(
            "completeness_report",
            f"Score {completeness['score']}/100"
        )

        results = []

        for i, target in enumerate(targets, start=1):

            say(
                f"Analyzing role {i} of {len(targets)} ..."
            )

            role = self.analyze_role(target)

            fit = self.analyze_fit(role)

            results.append({
                "target": target,
                "role": role,
                "fit": fit
            })

        if len(results) > 1:

            best = max(
                results,
                key=lambda r: r["fit"]["score"]
            )

            say(
                f"Comparison done. Best match: "
                f"{best['role']['role_title']}"
            )

        say("Analysis complete.")

        return {
            "resume": resume,
            "completeness": completeness,
            "roles": results
        }

    # ---------- TOOL 4: improve content (with self-check) ---------

    def improve(self, role, fit):

        weak = find_weak_bullets(
            self.resume_text
        )

        self.log(
            "find_weak_bullets",
            f"{len(weak)} weak bullets found"
        )

        prompt = f"""
Improve this student's resume for the role:
{role['role_title']}

Keywords to weave in ONLY where truthful:
{fit['keywords_to_add']}

Weak bullets to rewrite:
{weak}

RESUME:
{self.resume_text}

Return JSON with keys:

summary (a 2-3 line professional summary for this role, using only facts in the resume),

rewritten_bullets (list of objects: original, improved). Start each improved bullet
with a strong action verb. If a number is needed but unknown, use a placeholder like
[X%] or [N users] for the student to fill in. NEVER invent numbers or tools.

skills_section (one line, skills grouped and ordered by relevance to the role).
"""

        draft = ask(
            prompt,
            SYSTEM,
            as_json=True
        )

        if not isinstance(draft, dict):
            draft = {}

        self.log(
            "improve",
            "First draft of improved content written"
        )

        # ---- reflection loop: a critic checks the draft for made-up facts ---

        critic_prompt = f"""
ORIGINAL RESUME:
{self.resume_text}

IMPROVED CONTENT:
{draft}

Check the improved content. Flag any tool, number, company, degree or achievement
that is NOT supported by the original resume. Placeholders in [square brackets] are
allowed.

Return JSON:
{{"ok": true or false, "issues": [list of short strings]}}
"""

        verdict = ask(
            critic_prompt,
            SYSTEM,
            as_json=True
        )

        issues = (
            as_list(verdict.get("issues"))
            if isinstance(verdict, dict)
            else []
        )

        if (
            isinstance(verdict, dict)
            and verdict.get("ok") is False
            and issues
        ):

            self.log(
                "critic",
                f"Found {len(issues)} unsupported claims -> revising"
            )

            fix_prompt = f"""
Rewrite the improved content below and fix these problems:

{issues}

ORIGINAL RESUME:
{self.resume_text}

IMPROVED CONTENT:
{draft}

Return the same JSON keys:
summary, rewritten_bullets, skills_section.
"""

            fixed = ask(
                fix_prompt,
                SYSTEM,
                as_json=True
            )

            if isinstance(fixed, dict):
                draft = fixed

            self.log(
                "improve",
                "Revised draft after critic feedback"
            )

        else:

            self.log(
                "critic",
                "Draft passed the honesty check"
            )

        return {
            "summary": draft.get(
                "summary",
                ""
            ),

            "rewritten_bullets": as_list(
                draft.get("rewritten_bullets")
            ),

            "skills_section": draft.get(
                "skills_section",
                ""
            ),

            "critic_issues": issues,
        }

    # ---------- TOOL 5: structured final review ---------

    def final_review(
        self,
        role,
        fit,
        completeness
    ):

        overall = round(
            0.6 * fit["score"]
            + 0.4 * completeness["score"]
        )

        failed_checks = [
            c["name"]
            for c in completeness["checks"]
            if not c["passed"]
        ]

        prompt = f"""
Write a final resume review for the role:
{role['role_title']}.

Role fit score:
{fit['score']}/100.

Completeness score:
{completeness['score']}/100.

Missing required skills:
{fit['must_missing']}

Weak areas found:
{fit['weak_areas']}

Failed completeness checks:
{failed_checks}

RESUME:
{self.resume_text}

Return JSON with keys:

verdict (one honest sentence),

top_strengths (list of 3),

priority_fixes (list of 5, most important first, each specific and actionable),

section_ratings (object with keys Summary, Education, Skills, Projects, Experience,
Formatting; each value one of "Good", "Needs work", "Missing"),

next_steps (list of 3 things to do this week, e.g. a project or course to close a gap).
"""

        review = ask(
            prompt,
            SYSTEM,
            as_json=True
        )

        if not isinstance(review, dict):
            review = {}

        review["overall_score"] = overall

        self.log(
            "final_review",
            f"Overall score {overall}/100"
        )

        return review

    # ---------- MAIN JOB 2: improve + review for one chosen role ---------

    def improve_and_review(
        self,
        result,
        completeness
    ):

        improved = self.improve(
            result["role"],
            result["fit"]
        )

        review = self.final_review(
            result["role"],
            result["fit"],
            completeness
        )

        return {
            "improved": improved,
            "review": review
        }