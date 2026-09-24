"""tools.py - simple, non-AI 'tools' the agent can call (fast, free, predictable)."""

import re

from pypdf import PdfReader


# ---------- 1. Reading a resume ----------

def read_pdf(file):
    """Extract text from an uploaded PDF (file can be a path or an uploaded file)."""

    reader = PdfReader(file)

    pages = [(page.extract_text() or "") for page in reader.pages]

    return "\n".join(pages).strip()


# ---------- 2. Skills knowledge ----------

SKILL_BANK = [
    "python", "java", "c", "c++", "c#", "javascript", "typescript", "sql", "r",
    "html", "css", "react", "angular", "node.js", "express", "django", "flask",
    "fastapi", "spring boot", "php", "kotlin", "swift", "flutter", "git", "github",
    "docker", "kubernetes", "linux", "aws", "azure", "gcp", "mysql", "postgresql",
    "mongodb", "firebase", "rest api", "graphql", "excel", "power bi", "tableau",
    "pandas", "numpy", "matplotlib", "seaborn", "scikit-learn", "tensorflow",
    "pytorch", "keras", "opencv", "machine learning", "deep learning", "nlp",
    "data analysis", "data visualization", "statistics", "data structures",
    "algorithms", "oop", "agile", "scrum", "figma", "ui/ux", "testing", "selenium",
    "communication", "teamwork", "leadership", "problem solving", "jira",
]


ALIASES = {
    "javascript": ["js"],
    "machine learning": ["ml"],
    "power bi": ["powerbi"],
    "scikit-learn": ["sklearn"],
    "node.js": ["nodejs", "node"],
    "react": ["reactjs", "react.js"],
    "postgresql": ["postgres"],
    "nlp": ["natural language processing"],
    "aws": ["amazon web services"],
    "mongodb": ["mongo"],
    "tensorflow": ["tf"],
    "data structures": ["dsa"],
    "sql": ["mysql", "postgresql", "sqlite", "sql server"],
    "rest api": ["rest apis", "restful"],
    "oop": ["object oriented", "object-oriented"],
}


# Fallback requirements if the AI cannot work out a role

ROLE_PRESETS = {
    "data analyst": [
        "sql",
        "excel",
        "python",
        "power bi",
        "tableau",
        "statistics",
        "data visualization",
        "pandas",
    ],

    "web developer": [
        "html",
        "css",
        "javascript",
        "react",
        "git",
        "node.js",
        "rest api",
    ],

    "software engineer": [
        "data structures",
        "algorithms",
        "python",
        "java",
        "git",
        "sql",
        "oop",
    ],

    "machine learning": [
        "python",
        "machine learning",
        "pandas",
        "numpy",
        "scikit-learn",
        "tensorflow",
        "statistics",
    ],

    "data scientist": [
        "python",
        "sql",
        "machine learning",
        "statistics",
        "pandas",
        "data visualization",
    ],
}


def has_skill(text, skill):
    """True if the skill (or one of its aliases) appears as a whole word in the text."""

    low = text.lower()

    for name in [skill.lower()] + ALIASES.get(skill.lower(), []):

        pattern = r"(?<![a-z0-9+#])" + re.escape(name) + r"(?![a-z0-9+#])"

        if re.search(pattern, low):
            return True

    return False


def extract_skills(text):
    """Find every known skill mentioned in a piece of text."""

    return [s for s in SKILL_BANK if has_skill(text, s)]


def preset_for(role_text):
    low = role_text.lower()

    for key, skills in ROLE_PRESETS.items():

        if key in low:
            return list(skills)

    return []


def skill_match(resume_text, required_skills):
    """Compare required skills with the resume. Returns matched, missing and percent."""

    required = []

    for s in required_skills:

        if (
            isinstance(s, str)
            and s.strip()
            and s.lower() not in [r.lower() for r in required]
        ):
            required.append(s.strip())

    matched = [s for s in required if has_skill(resume_text, s)]

    missing = [s for s in required if s not in matched]

    percent = round(100 * len(matched) / len(required)) if required else 0

    return {
        "matched": matched,
        "missing": missing,
        "percent": percent,
    }


# ---------- 3. Completeness report ----------

ACTION_VERBS = [
    "developed",
    "built",
    "designed",
    "implemented",
    "created",
    "led",
    "analyzed",
    "optimized",
    "improved",
    "automated",
    "deployed",
    "managed",
    "trained",
    "engineered",
    "reduced",
    "increased",
    "achieved",
    "launched",
    "collaborated",
    "organized",
    "conducted",
    "integrated",
    "tested",
    "delivered",
    "researched",
]


WEAK_PHRASES = [
    "responsible for",
    "worked on",
    "helped with",
    "helped in",
    "assisted in",
    "involved in",
    "participated in",
    "tasked with",
    "duties included",
    "various",
    "etc",
]


def _has_phone(text):
    """Check whether the text contains a likely phone number."""

    for m in re.finditer(r"\+?\d[\d\s\-()]{8,}\d", text):

        if len(re.sub(r"\D", "", m.group())) >= 10:
            return True

    return False


def completeness_report(text):
    """Generate a simple resume completeness report."""

    t = text.lower()

    words = len(text.split())

    verbs_found = len(
        [
            v
            for v in ACTION_VERBS
            if re.search(r"\b" + re.escape(v) + r"\b", t)
        ]
    )

    metrics = len(
        re.findall(
            r"\d+(?:\.\d+)?\s?%|\b\d+\s?\+|\b\d+\s?x\b",
            t,
        )
    )

    metrics += len(
        re.findall(
            r"\b\d+\s+(?:users|records|students|rows|models|members|"
            r"participants|clients|projects|customers|teams)",
            t,
        )
    )

    def any_in(words_list):
        return any(w in t for w in words_list)

    rules = [
        (
            "Email address",
            bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)),
            8,
            "Add a professional email address at the top.",
        ),

        (
            "Phone number",
            _has_phone(text),
            6,
            "Add a phone number recruiters can call.",
        ),

        (
            "LinkedIn or GitHub link",
            any_in(["linkedin", "github"]),
            8,
            "Add your LinkedIn and/or GitHub profile link.",
        ),

        (
            "Education section",
            any_in(
                [
                    "education",
                    "b.tech",
                    "bachelor",
                    "degree",
                    "university",
                    "college",
                ]
            ),
            10,
            "Add an Education section with degree, college and year.",
        ),

        (
            "Skills section",
            "skills" in t,
            10,
            "Add a clear Skills section.",
        ),

        (
            "Projects section",
            "project" in t,
            12,
            "Add 2-3 projects with what you built and which tools you used.",
        ),

        (
            "Experience / internship",
            any_in(
                [
                    "experience",
                    "internship",
                    "intern ",
                ]
            ),
            8,
            "Add internships, freelance, club or volunteer work if you have any.",
        ),

        (
            "Summary / objective",
            any_in(
                [
                    "summary",
                    "objective",
                    "profile",
                    "about me",
                ]
            ),
            6,
            "Add a 2-3 line summary aimed at the target role.",
        ),

        (
            "Certifications / achievements",
            any_in(
                [
                    "certif",
                    "achievement",
                    "award",
                    "hackathon",
                    "coursera",
                    "nptel",
                ]
            ),
            6,
            "Add certifications, awards or hackathons.",
        ),

        (
            "Measurable results (numbers)",
            metrics >= 2,
            10,
            "Add numbers to bullets (percentages, counts, time saved).",
        ),

        (
            "Strong action verbs",
            verbs_found >= 5,
            8,
            "Start bullets with verbs like Built, Designed, Improved.",
        ),

        (
            "Good length (200-800 words)",
            200 <= words <= 800,
            8,
            "Aim for 200-800 words; one page for students.",
        ),
    ]

    checks = [
        {
            "name": n,
            "passed": bool(ok),
            "weight": w,
            "tip": tip,
        }
        for n, ok, w, tip in rules
    ]

    score = sum(
        c["weight"]
        for c in checks
        if c["passed"]
    )

    return {
        "score": score,
        "checks": checks,
        "word_count": words,
    }


def find_weak_bullets(text, limit=6):
    """Return bullet lines that are vague (weak phrases) or have no numbers."""

    lines = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip()
    ]

    bullet_start = r"^[-\*\u2022\u25cf\u25aa\u25e6]+\s*"

    bullets = [
        re.sub(bullet_start, "", ln)
        for ln in lines
        if re.match(bullet_start, ln)
    ]

    if not bullets:
        # PDF lost the bullet symbols -> use long lines instead
        bullets = [
            ln
            for ln in lines
            if len(ln.split()) >= 8
        ]

    weak = []

    for b in bullets:

        low = b.lower()

        vague = any(
            p in low
            for p in WEAK_PHRASES
        )

        if vague or not re.search(r"\d", b):
            weak.append(
                (
                    0 if vague else 1,
                    b,
                )
            )

    weak.sort(
        key=lambda pair: pair[0]
    )

    return [
        b
        for _, b in weak
    ][:limit]