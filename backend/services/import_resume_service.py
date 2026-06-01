import logging
import re
from copy import deepcopy
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)

VALID_TEMPLATES = {
    "classic",
    "twocolumn",
    "ats",
    "corporate",
    "modern",
    "creative",
    "sidebar",
    "minimal",
    "timeline",
    "academic",
    "striped",
    "pastel",
    "warm",
    "technical",
    "typographic",
    "architect",
    "bold",
}

VALID_LANGUAGE_LEVELS = {
    "Beginner",
    "Elementary",
    "Intermediate",
    "Upper Intermediate",
    "Advanced",
    "Native",
    "Native / Bilingual",
}

DEFAULT_RESUME = {
    "personal": {
        "firstName": "",
        "lastName": "",
        "profession": "",
        "onet_code": "",
        "city": "",
        "country": "",
        "pincode": "",
        "phone": "",
        "email": "",
        "linkedin": "",
        "websites": [],
    },
    "summary": "",
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "languages": [],
    "template": "classic",
}

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_RE = re.compile(r"^\+?\d[\d\-\s\(\)]{7,}\d$")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
YEAR_RE = re.compile(r"(19\d{2}|20\d{2})")


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value).strip()
    return ""


def _norm_space(text: str) -> str:
    t = _as_str(text)
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        raw = re.split(r"[,;\n|]+", value)
    else:
        raw = []
    out: list[str] = []
    seen = set()
    for item in raw:
        s = _norm_space(_as_str(item))
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _coerce_year(value: Any) -> str:
    text = _as_str(value)
    if not text:
        return ""
    m = YEAR_RE.findall(text)
    if not m:
        return ""
    # Graduation range handling: use end year if present.
    year = m[-1]
    try:
        y = int(year)
    except ValueError:
        return ""
    if y < 1900 or y > datetime.now().year + 2:
        return ""
    return str(y)


def _clean_url(value: Any) -> str:
    url = _norm_space(_as_str(value))
    if not url:
        return ""
    if not URL_RE.search(url):
        if "linkedin.com" in url.lower():
            url = f"https://{url}"
        elif "." in url and " " not in url:
            url = f"https://{url}"
        else:
            return ""
    return url


def _clean_phone(value: Any) -> str:
    phone = _norm_space(_as_str(value))
    if not phone:
        return ""
    return phone if PHONE_RE.search(phone) else ""


def _clean_email(value: Any) -> str:
    email = _norm_space(_as_str(value))
    if not email:
        return ""
    return email if EMAIL_RE.search(email) else ""


def _normalize_description(value: Any) -> str:
    desc = _norm_space(_as_str(value))
    if not desc:
        return ""
    desc = re.sub(r"\s*[•·]\s*", "\n- ", desc)
    desc = re.sub(r"\s*-\s+", "\n- ", desc)
    desc = re.sub(r"\.\s+(?=[A-Z])", ".\n", desc)
    desc = re.sub(r"\n{3,}", "\n\n", desc)
    return desc.strip()


def _split_title_employer(title: str, employer: str) -> tuple[str, str]:
    t = _norm_space(title)
    e = _norm_space(employer)
    if t and not e:
        parts = [p.strip() for p in re.split(r"\s+\-\s+|\s+\|\s+|\s+@\s+|\s+ at \s+", t, flags=re.IGNORECASE) if p.strip()]
        if len(parts) >= 2:
            left, right = parts[0], " - ".join(parts[1:])
            company_tokens = ("ltd", "pvt", "inc", "llc", "corp", "company", "technologies", "solutions", "systems")
            if any(tok in left.lower() for tok in company_tokens):
                return right, left
            if any(tok in right.lower() for tok in company_tokens):
                return left, right
    return t, e


def _dedupe_dicts(items: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen = set()
    for item in items:
        key = "|".join(_as_str(item.get(f)).lower() for f in fields)
        if not key.strip("|") or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _clean_personal(raw: Any, corrections: list[str]) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    if not isinstance(raw, dict):
        corrections.append("personal section malformed; defaults applied.")

    websites = [_clean_url(u) for u in _clean_list(source.get("websites", []))]
    websites = [u for u in websites if u]
    linkedin = _clean_url(source.get("linkedin"))
    if linkedin and linkedin not in websites:
        websites.append(linkedin)

    city = _norm_space(_as_str(source.get("city")))
    if re.search(r"\b(BE|BTECH|MTECH|GPA|CGPA)\b", city, re.IGNORECASE):
        city = ""
        corrections.append("invalid city value suppressed in header rendering.")

    return {
        "firstName": _norm_space(_as_str(source.get("firstName"))),
        "lastName": _norm_space(_as_str(source.get("lastName"))),
        "profession": _norm_space(_as_str(source.get("profession"))),
        "onet_code": _norm_space(_as_str(source.get("onet_code"))),
        "city": city,
        "country": _norm_space(_as_str(source.get("country"))),
        "pincode": _norm_space(_as_str(source.get("pincode"))),
        "phone": _clean_phone(source.get("phone")),
        "email": _clean_email(source.get("email")),
        "linkedin": linkedin,
        "websites": _clean_list(websites),
    }


def _clean_education(raw: Any, corrections: list[str]) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        corrections.append("education section malformed; reset to empty list.")
        return []

    cleaned: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            item = {"school": item}
        if not isinstance(item, dict):
            continue
        degree = _norm_space(_as_str(item.get("degree")))
        field = _norm_space(_as_str(item.get("field")))
        school = _norm_space(_as_str(item.get("school")))
        gpa = _norm_space(_as_str(item.get("gpa")))
        grad_year = _coerce_year(item.get("gradYear"))
        location = _norm_space(_as_str(item.get("location")))

        # render-time duplication cleanup only (not OCR parsing)
        if school and gpa and school.lower() == gpa.lower():
            gpa = ""
            corrections.append("duplicate education value removed from GPA.")
        if degree and school and degree.lower() == school.lower():
            school = ""
            corrections.append("duplicate education value removed from school.")

        row = {
            "degree": degree,
            "field": field,
            "school": school,
            "location": location,
            "gpa": gpa,
            "gradMonth": _norm_space(_as_str(item.get("gradMonth"))),
            "gradYear": grad_year,
        }
        if any(row.values()):
            cleaned.append(row)

    return _dedupe_dicts(cleaned, ["degree", "field", "school", "gradYear", "gpa"])


def _clean_experience(raw: Any, corrections: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        corrections.append("experience section malformed; reset to empty list.")
        return []

    cleaned: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            item = {"description": item}
        if not isinstance(item, dict):
            continue

        title, employer = _split_title_employer(
            _as_str(item.get("title")),
            _as_str(item.get("employer")),
        )

        desc = _normalize_description(item.get("description"))
        if not title and (employer or desc):
            title = "Professional Experience"
            corrections.append("missing experience title replaced with safe fallback.")

        current = bool(item.get("current")) or bool(re.search(r"\b(present|current)\b", " ".join([_as_str(item.get("endMonth")), _as_str(item.get("endYear")), desc]), re.IGNORECASE))
        end_month = "" if current else _norm_space(_as_str(item.get("endMonth")))
        end_year = "" if current else _coerce_year(item.get("endYear"))

        row = {
            "title": _norm_space(title),
            "employer": _norm_space(employer),
            "location": _norm_space(_as_str(item.get("location"))),
            "description": desc,
            "startMonth": _norm_space(_as_str(item.get("startMonth"))),
            "startYear": _coerce_year(item.get("startYear")),
            "endMonth": end_month,
            "endYear": end_year,
            "current": current,
            "onet_code": _norm_space(_as_str(item.get("onet_code"))),
            "originalDescription": _normalize_description(item.get("originalDescription")) or desc,
        }
        if "lastTemplateIndex" in item:
            try:
                idx = int(item.get("lastTemplateIndex"))
                if idx >= 0:
                    row["lastTemplateIndex"] = idx
            except (TypeError, ValueError):
                pass

        if row["title"] or row["employer"] or row["description"]:
            cleaned.append(row)

    return _dedupe_dicts(cleaned, ["title", "employer", "startYear", "endYear", "description"])


def _clean_projects(raw: Any, corrections: list[str]) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        corrections.append("projects section malformed; reset to empty list.")
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            item = {"title": item}
        if not isinstance(item, dict):
            continue
        row = {
            "title": _norm_space(_as_str(item.get("title"))),
            "description": _normalize_description(item.get("description")),
            "role": _norm_space(_as_str(item.get("role"))),
            "tools": _norm_space(_as_str(item.get("tools"))),
            "url": _clean_url(item.get("url")),
        }
        if any(row.values()):
            cleaned.append(row)
    return _dedupe_dicts(cleaned, ["title", "description", "role", "tools", "url"])


def _clean_certifications(raw: Any, corrections: list[str]) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        corrections.append("certifications section malformed; reset to empty list.")
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        row = {
            "name": _norm_space(_as_str(item.get("name"))),
            "issuingOrg": _norm_space(_as_str(item.get("issuingOrg"))),
            "achievedDate": _norm_space(_as_str(item.get("achievedDate"))),
            "url": _clean_url(item.get("url")),
        }
        if row["name"]:
            cleaned.append(row)
    return _dedupe_dicts(cleaned, ["name", "issuingOrg", "achievedDate", "url"])


def _normalize_level(value: Any) -> str:
    level = _norm_space(_as_str(value))
    if not level:
        return "Intermediate"
    if level in VALID_LANGUAGE_LEVELS:
        return level
    normalized = " ".join(part.capitalize() for part in level.split())
    if normalized in VALID_LANGUAGE_LEVELS:
        return normalized
    if level.lower() in {"native/bilingual", "native bilingual", "bilingual"}:
        return "Native / Bilingual"
    return "Intermediate"


def _clean_languages(raw: Any, corrections: list[str]) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        corrections.append("languages section malformed; reset to empty list.")
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        row = {
            "name": _norm_space(_as_str(item.get("name"))),
            "level": _normalize_level(item.get("level")),
        }
        if row["name"]:
            cleaned.append(row)
    return _dedupe_dicts(cleaned, ["name", "level"])


def _clean_skills(raw: Any) -> list[str]:
    skills = _clean_list(raw)
    out: list[str] = []
    seen = set()
    for skill in skills:
        normalized = skill.strip()
        if len(normalized) <= 4 and normalized.upper() in {"SQL", "AWS", "SAP", "ERP", "API"}:
            normalized = normalized.upper()
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            out.append(normalized)
    return out


def _build_summary_if_missing(summary: str, personal: dict[str, Any], skills: list[str], experience: list[dict[str, Any]]) -> str:
    s = _norm_space(summary)
    if s:
        return s
    profession = _norm_space(_as_str(personal.get("profession"))) or "Professional"
    years = 0
    current_year = datetime.now().year
    for exp in experience:
        try:
            sy = int(exp.get("startYear")) if exp.get("startYear") else None
        except ValueError:
            sy = None
        try:
            ey = int(exp.get("endYear")) if exp.get("endYear") else current_year
        except ValueError:
            ey = current_year
        if sy:
            years += max(0, ey - sy)
    skill_text = ", ".join(skills[:6])
    if years > 0 and skill_text:
        return f"{profession} with approximately {years}+ years of experience and strong skills in {skill_text}. Delivers reliable outcomes with a focus on quality, collaboration, and continuous improvement."
    if skill_text:
        return f"{profession} with practical strengths in {skill_text}. Detail-oriented and focused on clear execution, stakeholder communication, and high-quality delivery."
    return f"{profession} with a strong focus on professional execution, communication, and consistent results."


def sanitize_resume_for_render(resume_data: Any) -> dict[str, Any]:
    """
    Render-time safety layer for preview/PDF generation.
    Uses already structured JSON only; no OCR parsing.
    """
    corrections: list[str] = []
    if not isinstance(resume_data, dict):
        return deepcopy(DEFAULT_RESUME)

    source = dict(resume_data)
    sanitized = deepcopy(DEFAULT_RESUME)

    sanitized["personal"] = _clean_personal(source.get("personal", {}), corrections)
    sanitized["skills"] = _clean_skills(source.get("skills", []))
    sanitized["education"] = _clean_education(source.get("education", []), corrections)
    sanitized["experience"] = _clean_experience(source.get("experience", []), corrections)
    sanitized["projects"] = _clean_projects(source.get("projects", []), corrections)
    sanitized["certifications"] = _clean_certifications(source.get("certifications", []), corrections)
    sanitized["languages"] = _clean_languages(source.get("languages", []), corrections)
    sanitized["summary"] = _build_summary_if_missing(
        _as_str(source.get("summary")),
        sanitized["personal"],
        sanitized["skills"],
        sanitized["experience"],
    )

    template = _norm_space(_as_str(source.get("template"))) or "classic"
    sanitized["template"] = template if template in VALID_TEMPLATES else "classic"

    # Hide empty sections at render-time by returning truly empty arrays.
    for section in ("skills", "education", "experience", "projects", "certifications", "languages"):
        if not sanitized.get(section):
            sanitized[section] = []

    if corrections:
        logger.info("Render-time sanitization corrections: %s", corrections)
    return sanitized


def normalize_imported_resume(raw_resume_data: Any) -> tuple[dict[str, Any], list[str]]:
    """
    Import-time normalization for builder-native storage.
    Keeps scope limited to structured JSON sanitation and validation.
    """
    corrections: list[str] = []
    if not isinstance(raw_resume_data, dict):
        logger.warning("Parser resume_data is not an object. Resetting to defaults.")
        return deepcopy(DEFAULT_RESUME), ["resume_data root was malformed and reset."]

    sanitized = sanitize_resume_for_render(raw_resume_data)

    if not isinstance(raw_resume_data.get("personal"), dict):
        corrections.append("personal section malformed; defaults applied.")
    for key in ("skills", "education", "experience", "projects", "certifications", "languages"):
        if not isinstance(raw_resume_data.get(key), list):
            corrections.append(f"{key} section malformed; reset to empty list.")
    if _norm_space(_as_str(raw_resume_data.get("template"))) not in VALID_TEMPLATES:
        corrections.append("unsupported template replaced with classic.")

    return sanitized, corrections


def validate_parser_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Parser response is not a JSON object.")
    if payload.get("success") is False:
        raise ValueError("Parser returned success=false.")
    if "resume_data" not in payload:
        raise ValueError("Parser response missing resume_data.")
    resume_data = payload.get("resume_data")
    if not isinstance(resume_data, dict):
        raise ValueError("Parser resume_data is not an object.")
    return payload
