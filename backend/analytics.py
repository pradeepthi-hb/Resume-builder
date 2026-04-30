import re
import mysql.connector

from db_settings import get_mysql_config, load_environment

load_environment()


def _load_tech_keywords():
    conn = mysql.connector.connect(**get_mysql_config(include_database=True))
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT technology FROM technology_skills")
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


TECH_KEYWORDS = _load_tech_keywords()

ACTION_VERBS = {
    "developed", "designed", "implemented", "built", "optimized", "managed",
    "led", "created", "improved", "engineered", "automated", "analyzed",
    "delivered", "increased", "reduced", "launched", "configured", "maintained",
    "spearheaded", "streamlined", "architected", "deployed", "migrated",
    "integrated", "refactored", "mentored", "coordinated", "established"
}

WEAK_VERBS = {
    "worked", "helped", "assisted", "responsible", "participated",
    "supported", "handled", "involved"
}

_TECH_KEYWORD_PATTERNS = {
    kw: re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
    for kw in TECH_KEYWORDS
}

_QUANTIFIED_RE = re.compile(r'\d+%|\d+x|\$[\d,]+|\d[\d,]*\+')
_EMAIL_RE      = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
_PHONE_RE      = re.compile(r'\+?\d[\d\s\-\(\)]{7,}\d')
_WORD_STRIP_RE = re.compile(r"[^\w'/\+#]")

def _collect(value, parts):
    if isinstance(value, str):
        if value.strip():
            parts.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            _collect(v, parts)
    elif isinstance(value, list):
        for item in value:
            _collect(item, parts)
    elif value is not None:
        parts.append(str(value))


def extract_text(data):
    parts = []
    _collect(data, parts)
    return " ".join(parts)


def _clean_word(w):
    return _WORD_STRIP_RE.sub("", w).lower()

def readability_score(words, sentences):
    if sentences == 0 or words == 0:
        return 0
    return round(206.835 - (1.015 * (words / sentences)) - (84.6 * (words / words)))

def _generate_suggestions(data, metrics):
    suggestions = []

    summary    = data.get("summary", "")
    experience = data.get("experience", [])
    skills     = data.get("skills", [])
    education  = data.get("education", [])
    projects   = data.get("projects", [])
    certs      = data.get("certifications", [])

    # Summary
    if not summary:
        suggestions.append({"type": "error", "text": "Add a professional summary — it's the first thing recruiters read."})
    elif len(summary.split()) < 30:
        suggestions.append({"type": "warn", "text": f"Your summary is only {len(summary.split())} words. Aim for 40-60 words that highlight your unique value."})
    else:
        first_word = _clean_word(summary.strip().split()[0]) if summary.strip() else ""
        if first_word not in ACTION_VERBS:
            suggestions.append({"type": "info", "text": "Consider starting your summary with a strong action verb or adjective like 'Results-driven' or 'Seasoned'."})

    # Quantified achievements
    q = metrics["quantified_achievements"]
    if q == 0:
        suggestions.append({"type": "error", "text": "No quantified achievements found. Add numbers like 'Reduced load time by 40%' or 'Managed $2M budget' to stand out."})
    elif q < 3:
        suggestions.append({"type": "warn", "text": f"Only {q} quantified bullet{'s' if q > 1 else ''}. Aim for 3-5 across all roles — numbers make impact concrete."})

    # Action verbs
    av = metrics["action_verbs_used"]
    if av < 3:
        suggestions.append({"type": "error", "text": "Too few action verbs. Start each bullet with a strong verb like 'Built', 'Led', 'Reduced', 'Automated'."})
    elif av < 6:
        suggestions.append({"type": "warn", "text": f"Only {av} action verbs found. Aim for one per bullet point to communicate ownership."})

    # ATS keywords
    kc = metrics["keywords_count"]
    if kc < 4:
        suggestions.append({"type": "error", "text": "Very few tech keywords. Add relevant tools, languages and platforms to pass Applicant Tracking Systems (ATS)."})
    elif kc < 8:
        suggestions.append({"type": "warn", "text": f"Only {kc} tech keywords. Mirror language from job descriptions you're targeting to improve ATS match rate."})

    # Skills
    sc = metrics["skills_count"]
    if sc == 0:
        suggestions.append({"type": "error", "text": "Skills section is empty. Add at least 8-12 relevant technical and soft skills."})
    elif sc < 5:
        suggestions.append({"type": "warn", "text": f"Only {sc} skills listed. Recruiters scan skills first — aim for 8-12 relevant ones."})

    # Contact info
    if not metrics["has_email"]:
        suggestions.append({"type": "error", "text": "No email address found. Ensure your email is in the Personal section."})
    if not metrics["has_phone"]:
        suggestions.append({"type": "warn", "text": "No phone number detected. Add one so recruiters can reach you directly."})
    if not metrics["has_linkedin"]:
        suggestions.append({"type": "warn", "text": "No LinkedIn profile detected. Adding it significantly increases recruiter response rates."})

    # Thin experience bullets
    if experience:
        thin = [e.get("title") or "a role" for e in experience
                if len([b for b in str(e.get("description","")).split("\n") if b.strip()]) < 2]
        if thin:
            names = ", ".join(f'"{t}"' for t in thin[:2])
            extra = f" and {len(thin)-2} more" if len(thin) > 2 else ""
            suggestions.append({"type": "warn", "text": f"Roles with thin descriptions: {names}{extra}. Aim for 3-5 bullet points per position."})

    # Word count
    wc = metrics["word_count"]
    if wc < 150:
        suggestions.append({"type": "warn", "text": "Resume looks sparse. Expand experience descriptions and add more detail to projects."})
    elif wc > 900:
        suggestions.append({"type": "info", "text": f"At {wc} words, your resume may be too long. Aim for 1 page if you have under 5 years of experience."})

    # Missing sections
    if not education:
        suggestions.append({"type": "info", "text": "No education entries. Even ongoing or incomplete degrees are worth including."})
    if not projects and len(experience) < 2:
        suggestions.append({"type": "info", "text": "Add projects to demonstrate skills — especially valuable with limited work experience."})
    if not certs:
        suggestions.append({"type": "info", "text": "No certifications listed. Relevant certs (AWS, Google Cloud, Azure) boost credibility."})

    if not suggestions:
        suggestions.append({"type": "success", "text": "Your resume looks strong across all key areas. Keep it updated as you grow!"})

    return suggestions


def analyze_resume(resume_data):
    analytics = {}

    text        = extract_text(resume_data)
    raw_words   = text.split()
    clean_words = [_clean_word(w) for w in raw_words if _clean_word(w)]

    experience     = resume_data.get("experience", [])
    skills         = resume_data.get("skills", [])
    education      = resume_data.get("education", [])
    projects       = resume_data.get("projects", [])
    certifications = resume_data.get("certifications", [])


    # Completeness
    sections = ["summary", "experience", "education", "skills", "projects", "certifications"]
    filled   = sum(1 for s in sections if resume_data.get(s))
    analytics["completeness_score"] = round((filled / len(sections)) * 100)
    analytics["missing_sections"]   = [s for s in sections if not resume_data.get(s)]

    # Word analytics
    analytics["word_count"]      = len(clean_words)
    analytics["estimated_pages"] = round(len(clean_words) / 450, 1)

    # Skills
    analytics["skills_count"] = len(skills)

    # Experience strength
    analytics["experience_entries"] = len(experience)
    bullet_points = 0
    quantified    = 0

    for exp in experience:
        desc         = str(exp.get("description", ""))
        real_bullets = [b for b in desc.split("\n") if b.strip()]
        bullet_points += len(real_bullets)
        for bullet in real_bullets:
            if _QUANTIFIED_RE.search(bullet):
                quantified += 1

    analytics["bullet_points"]           = bullet_points
    analytics["quantified_achievements"] = quantified

    # Action verbs
    action_verbs_found = 0
    for exp in experience:
        desc = str(exp.get("description", ""))
        for line in desc.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            first = _clean_word(stripped.split()[0]) if stripped.split() else ""
            if first in ACTION_VERBS:
                action_verbs_found += 1

    summary_verbs = sum(1 for w in clean_words if w in ACTION_VERBS)
    analytics["action_verbs_used"] = max(action_verbs_found, summary_verbs)

    # Tech keywords (word-boundary safe)
    keyword_hits = [kw for kw, pat in _TECH_KEYWORD_PATTERNS.items() if pat.search(text)]
    analytics["keywords_found"] = keyword_hits
    analytics["keywords_count"] = len(keyword_hits)

    # Contact checks
    analytics["has_email"]    = bool(_EMAIL_RE.search(text))
    analytics["has_phone"]    = bool(_PHONE_RE.search(text))
    analytics["has_linkedin"] = bool(re.search(r'\blinkedin\b', text, re.IGNORECASE))

    # Score (max 100)
    score  = analytics["completeness_score"]  * 0.25
    score += min(analytics["word_count"] / 400, 1) * 10
    score += min(analytics["action_verbs_used"] / 10, 1) * 20
    score += min(analytics["quantified_achievements"] / 5, 1) * 25
    score += min(analytics["keywords_count"] / 10, 1) * 20
    analytics["resume_score"] = round(score)

    # Suggestions
    analytics["suggestions"] = _generate_suggestions(resume_data, analytics)

    # ----ats score-------
    ats_score = 100

    #  Keyword Alignment (30 pts)
    if analytics["keywords_count"] < 5:
        ats_score -= 20
    elif analytics["keywords_count"] < 8:
        ats_score -= 10

    # Keyword Context (15 pts)
    exp_text = " ".join(str(e.get("description", "")) for e in experience).lower()

    keywords_in_exp = sum(
        1 for kw in analytics["keywords_found"]
        if kw.lower() in exp_text
    )

    if keywords_in_exp < 3:
        ats_score -= 10
    elif keywords_in_exp < 5:
        ats_score -= 5

    analytics["keywords_in_experience"] = keywords_in_exp


    # Quantifiable Achievements (20 pts)
    if analytics["quantified_achievements"] == 0:
        ats_score -= 20
    elif analytics["quantified_achievements"] < 3:
        ats_score -= 10


    # Resume Formatting (15 pts)
    bad_format_patterns = [
        r"\|",        
        r"\t",        
    ]

    formatting_issues = sum(1 for p in bad_format_patterns if re.search(p, text))

    if formatting_issues > 0:
        ats_score -= 10

    analytics["formatting_issues"] = formatting_issues


    # Standard Section Headers (10 pts)

    standard_headers = {
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "summary"
    }

    found_headers = [
        h for h in standard_headers
        if h in text.lower()
    ]

    if len(found_headers) < 3:
        ats_score -= 10

    analytics["standard_sections_found"] = len(found_headers)


    # File Type (10 pts)

    file_type = resume_data.get("file_type", "pdf")

    if file_type not in ["pdf", "docx"]:
        ats_score -= 10

    analytics["file_type"] = file_type


    # Final ATS score clamp
    analytics["ats_score"] = max(0, min(100, ats_score))

    analytics["ats_breakdown"] = {
        "keyword_alignment": min(int((analytics["keywords_count"] / 10) * 100), 100),
        "keyword_context": min(int((keywords_in_exp / 5) * 100), 100),
        "quantified_results": min(int((analytics["quantified_achievements"] / 5) * 100), 100),
        "formatting": 100 if formatting_issues == 0 else 70,
        "sections": min(int((len(found_headers) / 5) * 100), 100),
        "file_type": 100 if file_type in ["pdf", "docx"] else 60
    }

    return analytics