
import os
import re
import json
import requests
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

_job_match_cache: dict[str, dict] = {}

load_dotenv()

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "") or os.getenv("_API_KEY", "")
_GROQ_MODEL = "llama-3.1-8b-instant"  

# CATEGORY ANCHORS

_CATEGORY_ANCHORS = {
    "Programming Language":  "a programming or scripting language used to write software",
    "Framework or Library":  "a software framework, library, or development toolkit",
    "Cloud & DevOps":        "a cloud platform or devops tool for infrastructure and deployment",
    "Database & Storage":    "a database, data warehouse, or storage technology",
    "Analytics & BI Tool":   "an analytics, business intelligence, or data visualization software",
    "Concept or Practice":   "a software engineering concept, methodology, or development practice",
    "Soft Skill":            "a communication, leadership, or interpersonal soft skill",
}

_ANCHOR_LABELS      = list(_CATEGORY_ANCHORS.keys())
_ANCHOR_TEXTS       = list(_CATEGORY_ANCHORS.values())
_ANCHOR_EMBEDDINGS  = get_model().encode(_ANCHOR_TEXTS)
_MIN_CATEGORY_SIM   = 0.28

# 1.  RESUME SKILLSss

def extract_resume_skills(resume_json: dict) -> list[str]:
    raw: list = resume_json.get("skills", [])
    skills: list[str] = []

    for item in raw:
        if not isinstance(item, str) or not item.strip():
            continue
        parts = re.split(r'[|,/;&\n\t]+', item)
        for part in parts:
            skill = part.strip().lower()
            if not skill or re.match(r'^\d+$', skill):
                continue
            original = part.strip()
            if len(skill) == 1 and not original.isupper():
                continue
            skills.append(skill)

    seen: set = set()
    result: list[str] = []
    for s in skills:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result

# 2.  JD SKILLS — extracted by Groq (Free, No Card)

_JD_EXTRACTION_PROMPT = """\
Extract only concrete, actionable technical skills, tools, programming languages,
frameworks, libraries, or platforms mentioned in the job description below.
Soft skills: only include if clearly emphasized or critical for the role.
Focus on skills that could be listed in a resume's skills section.

Do not include:
- Generic or abstract terms that describe concepts, processes, or broad categories
- Words describing actions, responsibilities, least important soft skills
- Anything related to company names, job titles, experience requirements, or education

Rules:
1. Each skill should be 1–3 words.
2. Use the exact spelling as in the job description.
3. Remove duplicates.
4. Return ONLY a valid JSON array of strings, no explanations, no markdown fences.

Job Description:
{jd_text}"""


def _call_ai_batch_match(jd_missing: list[str], resume_skills: list[str]) -> tuple[list[str], list[str]]:
    if not _GROQ_API_KEY:
        print("[job_match] GROQ_API_KEY not set — AI matching unavailable")
        return [], jd_missing

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"

        prompt = f"""
You are an ATS system that matches job description skills with resume skills.

Your task is to determine which job skills from the JD are present in the candidate's resume skills.

Follow these rules carefully:

1. Prefer exact matches between JD skills and resume skills.
2. Match a JD skill only if the exact same skill or a clearly recognized synonym
   literally appears in the resume skills list.
3. A JD skill should be considered matched if the core skill term appears within a longer resume skill phrase that 
   indicates usage, specialization, ecosystem, tools, libraries, or frameworks built around that skill.
4. Include soft skills only if they are clearly emphasized or critical for the role.
5. Do NOT match generic concepts, broad categories, loosely related technologies, or vague phrases.
6. Ignore experience requirements, company names, job titles, or non-resume information.
7. If a relationship between a JD skill and a resume skill is weak, indirect, or ambiguous,
   treat it as NOT matched.
8. Only match when the relationship is **clear, direct, and relevant**.

dont consider resume skills in matched skills or missing skills lists, only JD skills will be considered for that.
Resume skills :
{resume_skills}

JD skills :
{jd_missing}

Return ONLY valid JSON in this format:

{{
 "matched": [],
 "missing": []
}}
"""

        payload = {
            "model": _GROQ_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 512
        }

        headers = {
            "Authorization": f"Bearer {_GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()

        raw_text = resp.json()["choices"][0]["message"]["content"].strip()

        try:
            data = json.loads(raw_text)
            return data.get("matched", []), data.get("missing", jd_missing)
        except Exception:
            print("[job_match] Could not parse AI match response")
            return [], jd_missing

    except Exception as exc:
        print(f"[job_match] AI match error: {exc}")
        return [], jd_missing

def _call_ai_extract(jd_text: str) -> list[str]:
    if not _GROQ_API_KEY:
        print("[job_match] GROQ_API_KEY not set — AI extraction unavailable")
        return []

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        payload = {
            "model": _GROQ_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": _JD_EXTRACTION_PROMPT.format(jd_text=jd_text)
                }
            ],
            "temperature": 0,
            "max_tokens": 1024
        }

        headers = {
            "Authorization": f"Bearer {_GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        
        raw_text = resp.json()["choices"][0]["message"]["content"].strip()
        return _parse_ai_skill_list(raw_text)

    except Exception as exc:
        print(f"[job_match] AI extraction error: {exc}")
        return []


def _parse_ai_skill_list(raw: str) -> list[str]:
    text = raw.strip()

    text = re.sub(r'^```(?:json)?', '', text)
    text = re.sub(r'```$', '', text)

    try:
        skills = json.loads(text)
        if isinstance(skills, list):
            return [s.strip() for s in skills if isinstance(s, str)]
    except json.JSONDecodeError:
        pass

    skills = re.findall(r'"([^"]+)"', text)

    return list(dict.fromkeys(skills)) 


def extract_jd_skills(jd_text: str) -> list[str]:
    skills = _call_ai_extract(jd_text)
    seen: set = set()
    result: list[str] = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result

# 3.  EXPERIENCE EXTRACTION

def extract_years(text: str) -> int:
    patterns = [
        r'(\d+)\s*\+\s*years',
        r'(\d+)\s*(?:to|-)\s*(\d+)\s*years',
        r'minimum\s+(?:of\s+)?(\d+)\s*years',
        r'at\s+least\s+(\d+)\s*years',
        r'(\d+)\s+years?\s+of\s+(?:relevant\s+)?experience',
        r'(\d+)\s+years?',
    ]
    values: list[int] = []
    for pat in patterns:
        for m in re.finditer(pat, text.lower()):
            values.extend(int(g) for g in m.groups() if g)
    return max((v for v in values if 0 < v <= 30), default=0)


def extract_resume_experience(resume_json: dict) -> int:
    parts: list[str] = [resume_json.get("summary", "")]
    for exp in resume_json.get("experience", []):
        parts.append(exp.get("description", ""))
    return extract_years(" ".join(parts))

# 4.  SEMANTIC SKILL MATCHING

_MATCH_THRESHOLD = 0.65

def match_skills(jd_skills: list[str], resume_skills: list[str]) -> tuple[list[str], list[str], dict[str, float]]:

    if not jd_skills or not resume_skills:
        return [], list(jd_skills), {}

    jd_embs = get_model().encode([s.lower() for s in jd_skills])
    resume_embs = get_model().encode([s.lower() for s in resume_skills])

    sim_matrix = cosine_similarity(jd_embs, resume_embs)

    matched: list[str] = []
    missing_candidates: list[str] = []
    match_scores: dict[str, float] = {}


    for i, skill in enumerate(jd_skills):

        best = float(np.max(sim_matrix[i]))

        if best >= _MATCH_THRESHOLD:
            matched.append(skill)
            match_scores[skill] = round(best, 3)
        else:
            missing_candidates.append(skill)

    missing: list[str] = []

    if missing_candidates:
        missing_candidates = sorted(missing_candidates)
        resume_skills = sorted(resume_skills)

        missing_candidates = [s.lower().strip() for s in missing_candidates]
        resume_skills = [s.lower().strip() for s in resume_skills]

    ai_matched, ai_missing = _call_ai_batch_match(
        missing_candidates,
        resume_skills
    )

    verified_ai_matched = [s for s in ai_matched if s.lower() in [m.lower() for m in missing_candidates]]

    for skill in verified_ai_matched:
        if skill not in matched:
            matched.append(skill)
            match_scores[skill] = 0.7

    missing = ai_missing

    return matched, missing, match_scores

# 5.  CATEGORISATION

def _categorise_missing(missing_skills: list[str]) -> dict[str, list[str]]:
    if not missing_skills:
        return {}

    skill_embs = get_model().encode([s.lower() for s in missing_skills])
    sims       = cosine_similarity(skill_embs, _ANCHOR_EMBEDDINGS)

    result: dict[str, list[str]] = {}
    for i, skill in enumerate(missing_skills):
        best_idx = int(np.argmax(sims[i]))
        best_sim = float(sims[i][best_idx])
        if best_sim >= _MIN_CATEGORY_SIM:
            cat = _ANCHOR_LABELS[best_idx]
            result.setdefault(cat, []).append(skill)

    return result

# 6.  RECOMMENDATIONS
_HIGH_PRIORITY_CATS = {
    "Programming Language", "Framework or Library",
    "Cloud & DevOps", "Database & Storage", "Analytics & BI Tool",
}


def _build_recommendations(missing_by_cat: dict[str, list[str]], jd_exp: int, resume_exp: int) -> list[dict]:
    recs: list[dict] = []

    if jd_exp > 0 and resume_exp < jd_exp:
        gap = jd_exp - resume_exp
        recs.append({
            "priority": "high",
            "category": "Experience Gap",
            "message": f"This role requires {jd_exp}+ years; your resume shows ~{resume_exp}. Close the {gap}-year gap bu adding experience in summary."
        })

    for cat, skills in missing_by_cat.items():
        if not skills:
            continue
        top = skills[:6]
        skill_str = ", ".join(f"'{s}'" for s in top)
        recs.append({
            "priority": "high" if cat in _HIGH_PRIORITY_CATS else "medium",
            "category": cat,
            "message": f"Add or strengthen: {skill_str}.",
        })

    if not recs:
        recs.append({
            "priority": "low",
            "category": "General",
            "message": "Strong match. Mirror the JD's exact wording in your resume to maximise ATS keyword scoring."
        })

    return recs

# 7.  SCORING

def _calculate_score(matched: list[str], total_jd: int, resume_exp: int, jd_exp: int) -> int:
    skill_pct = len(matched) / max(total_jd, 1)
    exp_pct   = min(resume_exp / jd_exp, 1.0) if jd_exp > 0 else 1.0
    return min(round(skill_pct * 80 + exp_pct * 20), 100)


def _fit_level(score: int) -> str:
    if   score >= 80: return "Excellent Match"
    elif score >= 60: return "Strong Match"
    elif score >= 40: return "Moderate Match"
    else:             return "Low Match"

# 8.  PUBLIC ENTRY POINT

def semantic_match(resume_json: dict, jd_text: str) -> dict:
    resume_skills = extract_resume_skills(resume_json)
    resume_exp    = extract_resume_experience(resume_json)

    jd_skills     = extract_jd_skills(jd_text)
    jd_exp        = extract_years(jd_text)
    ai_used       = bool(jd_skills)

    if not jd_skills:
        return {
            "error": "Could not extract skills from the job description. Ensure GROQ_API_KEY is set in .env.",
            "ai_extraction_used": False,
        }

    if not resume_skills:
        return {
            "error": "No skills found in the resume. Please add skills in the Skills section.",
            "ai_extraction_used": ai_used,
        }

    matched, missing, match_scores = match_skills(jd_skills, resume_skills)
    total_jd    = len(jd_skills)
    score       = _calculate_score(matched, total_jd, resume_exp, jd_exp)
    fit         = _fit_level(score)

    skill_pct   = len(matched) / max(total_jd, 1)
    exp_pct     = min(resume_exp / jd_exp, 1.0) if jd_exp > 0 else 1.0

    missing_by_cat = _categorise_missing(missing)
    recs = _build_recommendations(missing_by_cat, jd_exp, resume_exp)

    return {
        "job_match_score":      score,
        "fit_level":            fit,
        "matched_skills":       matched,
        "missing_skills":       missing,
        "matched_skill_scores": match_scores,
        "missing_by_category":  missing_by_cat,
        "resume_skills":        resume_skills,
        "jd_skills":            jd_skills,
        "experience_required":  jd_exp,
        "experience_in_resume": resume_exp,
        "experience_gap":       max(0, jd_exp - resume_exp),
        "score_breakdown": {
            "skill_match_pct":  round(skill_pct * 100, 1),
            "skill_component":  round(skill_pct * 80, 1),
            "exp_component":    round(exp_pct * 20, 1),
            "total_score":            score,
        },
        "recommendations":      recs,
        "ai_extraction_used":   ai_used,
        "total_jd_skills":      total_jd,
        "total_resume_skills":  len(resume_skills),
    }
