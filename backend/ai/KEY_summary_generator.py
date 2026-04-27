from groq import Groq
from ai.key import groq_api_key

from ai.experience_classifier import calculate_total_experience
from ai.skill_ranker import rank_skills
from ai.impact_detector import extract_impact_statements
from ai.education_analyzer import extract_education_highlights


MAX_LENGTH = 700

client = Groq(api_key=groq_api_key)

MODEL_NAME = "llama-3.1-8b-instant"


def generate_summary_ai(resume_data, variation=0):

    personal = resume_data.get("personal", {})
    role = personal.get("profession", "Professional")

    experience_list = resume_data.get("experience", [])
    total_years = calculate_total_experience(experience_list)

    skills = rank_skills(resume_data)
    impacts = extract_impact_statements(resume_data)
    education = extract_education_highlights(resume_data)

    skills_text = ", ".join(skills[:5]) if skills else ""
    impact_text = impacts[0] if impacts else ""
    education_text = ", ".join(education) if education else ""

    if total_years < 1:
        prompt = f"""
Write a professional resume summary.

Role: {role}
Education: {education_text}
Skills: {skills_text}

Rules:
- 3–4 sentences
- No headings
- No bullet points
- Professional tone
- Minimum length 250 characters
- Maximum length 350 characters
"""
    else:
        prompt = f"""
Write a professional resume summary.

Role: {role}
Experience: {total_years} years
Skills: {skills_text}
Key impact: {impact_text}

Rules:
- 3–4 sentences
- No headings
- No bullet points
- Professional tone
- Minimum length 250 characters
- Maximum length 350 characters
"""

    try:

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=200
        )

        summary = response.choices[0].message.content.strip()

    except Exception as e:
        print("Groq error:", e)
        return ""

    if len(summary) > MAX_LENGTH:
        summary = summary[:MAX_LENGTH]

    return summary