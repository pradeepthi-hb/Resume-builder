def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def render(data):
    personal       = data.get("personal", {})
    summary        = data.get("summary", "")
    skills         = data.get("skills", [])
    education      = data.get("education", [])
    experience     = data.get("experience", [])
    projects       = data.get("projects", [])
    certifications = data.get("certifications", [])
    languages      = data.get("languages", [])

    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
        "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        # long-form fallback
        "January": 1, "February": 2, "March": 3, "April": 4,
        "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }

    # ── Sort Education (latest first) ─────────────────────────────────────────
    education = sorted(
        education,
        key=lambda x: (
            safe_int(x.get("gradYear", 0)),
            month_map.get(x.get("gradMonth", ""), 0)
        ),
        reverse=True
    )

    # ── Sort Experience (latest first, current job first) ─────────────────────
    experience = sorted(
        experience,
        key=lambda x: (
            9999 if x.get("current") else safe_int(x.get("endYear", 0)),
            12   if x.get("current") else month_map.get(x.get("endMonth", ""), 0)
        ),
        reverse=True
    )

    # ── Education HTML ────────────────────────────────────────────────────────
    education_html = ""
    for edu in education:
        gpa_html = f'<div class="item-meta">GPA: {edu.get("gpa")}</div>' if edu.get("gpa", "").strip() else ""
        education_html += f"""
        <div class="item">
            <div class="item-title">{edu.get("degree", "")}{" in " + edu.get("field", "") if edu.get("field") else ""}</div>
            <div class="item-sub">{edu.get("school", "")}{", " + edu.get("location", "") if edu.get("location") else ""}</div>
            <div class="item-date">{edu.get("gradMonth", "")} {edu.get("gradYear", "")}</div>
            {gpa_html}
        </div>
        """

    # ── Experience HTML ───────────────────────────────────────────────────────
    experience_html = ""
    for exp in experience:
        end_date = (
            "Present"
            if exp.get("current")
            else f"{exp.get('endMonth', '')} {exp.get('endYear', '')}"
        )
        experience_html += f"""
        <div class="item">
            <div class="item-title">{exp.get("title", "")}</div>
            <div class="item-sub">{exp.get("employer", "")}{", " + exp.get("location", "") if exp.get("location") else ""}</div>
            <div class="item-date">{exp.get("startMonth", "")} {exp.get("startYear", "")} &ndash; {end_date}</div>
            {"<div class='item-desc'>" + exp.get('description','') + "</div>" if exp.get('description','').strip() else ""}
        </div>
        """

    # ── Projects HTML ─────────────────────────────────────────────────────────
    projects_html = ""
    for proj in projects:
        role_tools = []
        if proj.get("role", "").strip():
            role_tools.append(f"<strong>Role:</strong> {proj.get('role')}")
        if proj.get("tools", "").strip():
            role_tools.append(f"<strong>Tools:</strong> {proj.get('tools')}")

        role_tools_html = f'<div class="item-sub">{" &nbsp;|&nbsp; ".join(role_tools)}</div>' if role_tools else ""
        desc_html = f'<div class="item-desc">{proj.get("description", "")}</div>' if proj.get("description", "").strip() else ""
        url_html  = f'<div class="item-meta"><a href="{proj.get("url")}" target="_blank" class="item-link">{proj.get("url")}</a></div>' if proj.get("url", "").strip() else ""

        projects_html += f"""
        <div class="item">
            <div class="item-title">{proj.get("title", "")}</div>
            {role_tools_html}
            {desc_html}
            {url_html}
        </div>
        """

    # ── Certifications HTML ───────────────────────────────────────────────────
    certifications_html = ""
    for cert in certifications:
        org_date_parts = []
        if cert.get("issuingOrg", "").strip():
            org_date_parts.append(cert.get("issuingOrg"))
        if cert.get("achievedDate", "").strip():
            org_date_parts.append(cert.get("achievedDate"))

        meta_html = f'<div class="item-sub">{" &bull; ".join(org_date_parts)}</div>' if org_date_parts else ""
        url_html  = f'<div class="item-meta"><a href="{cert.get("url")}" target="_blank" class="item-link">View Credential</a></div>' if cert.get("url", "").strip() else ""

        certifications_html += f"""
        <div class="item">
            <div class="item-title">{cert.get("name", "")}</div>
            {meta_html}
            {url_html}
        </div>
        """

    # ── Languages HTML (progress bars) ───────────────────────────────────────
    level_widths = {
        "Beginner":           20,
        "Elementary":         35,
        "Intermediate":       55,
        "Upper Intermediate": 70,
        "Advanced":           85,
        "Native":             100,
        "Native / Bilingual": 100,
    }

    languages_html = ""
    if languages:
        languages_html = "<div class='lang-list'>"
        for lang in languages:
            if not lang.get("name", "").strip():
                continue
            level = lang.get("level", "Intermediate")
            pct   = level_widths.get(level, 55)
            languages_html += f"""
            <div class="lang-item">
              <div class="lang-name-row">
                <span class="lang-name">{lang.get("name", "")}</span>
                <span class="lang-level">{level}</span>
              </div>
              <div class="lang-bar-bg">
                <div class="lang-bar-fill" style="width:{pct}%"></div>
              </div>
            </div>
            """
        languages_html += "</div>"

    # ── Skills HTML ───────────────────────────────────────────────────────────
    skills_html = (
        "<ul class='skills-list'>" +
        "".join([f"<li>{s}</li>" for s in skills if s.strip()]) +
        "</ul>"
    ) if skills else ""

    # ── Websites ──────────────────────────────────────────────────────────────
    websites = personal.get("websites", [])
    websites_str = ""
    if websites:
        links = [w.strip() for w in websites if w.strip()]
        if links:
            websites_str = " | " + " | ".join(links)

    # ── Section builder ───────────────────────────────────────────────────────
    def section(title, content):
        if not content.strip():
            return ""
        return (
            f"<div class='section'>"
            f"<div class='section-header'>{title}</div>"
            f"{content}"
            f"</div>"
        )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Resume</title>

<style>


#resume-preview * {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

#resume-preview body {{
  font-family: Arial, sans-serif;
  font-size: 11pt;
  margin: 0;
  background: #ffffff;
  color: #222;
}}

#resume-preview .page {{
  width: 210mm;
  min-height: 277mm;
  padding: 18mm;
  box-sizing: border-box;
}}


@media print {{
  body, html {{ margin: 0; padding: 0; }}

  #resume-preview .page {{
    width: 190mm;
    min-height: 277mm;
    padding: 0;
    margin: 0;

    box-shadow: none;
  }}

  #resume-preview .page:last-child {{
    page-break-after: avoid;
    break-after: avoid;
  }}

  #resume-preview .section,
  #resume-preview .cv-section,
  #resume-preview .m-section,
  #resume-preview .ats-section {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  #resume-preview .item,
  #resume-preview .cv-entry,
  #resume-preview .m-item {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  #resume-preview .page-break {{
    display: block;
    page-break-before: always;
    break-before: always;
    height: 0;
    margin: 0;
    padding: 0;
  }}
}}

/* ================= HEADER ================= */

#resume-preview .header {{
  text-align: center;
  margin-bottom: 22px;
}}

#resume-preview .name {{
  font-size: 26pt;
  font-weight: bold;
  letter-spacing: 1px;
  text-transform: uppercase;
}}

#resume-preview .profession {{
  font-size: 12pt;
  color: #555;
  margin-top: 4px;
  font-style: italic;
}}

#resume-preview .contact {{
  margin-top: 8px;
  font-size: 10.5pt;
  color: #444;
  line-height: 1.6;
}}

#resume-preview .contact a {{
  color: #444;
  text-decoration: none;
}}

/* ================= TWO-COLUMN LAYOUT ================= */

#resume-preview .content {{
  display: flex;
  gap: 28px;
}}

#resume-preview .left-column {{
  width: 35%;
  flex-shrink: 0;
}}

#resume-preview .right-column {{
  width: 65%;
}}

/* ================= SECTIONS ================= */

#resume-preview .section {{
  margin-bottom: 20px;
  page-break-inside: avoid;
  break-inside: avoid;
}}

#resume-preview .section-header {{
  font-size: 13pt;
  font-weight: bold;
  margin-bottom: 8px;
  border-bottom: 2px solid #000;
  padding-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.7px;
}}

/* ================= ITEMS ================= */

#resume-preview .item {{
  margin-bottom: 12px;
  page-break-inside: avoid;
  break-inside: avoid;
}}

#resume-preview .item-title {{
  font-weight: bold;
  font-size: 11pt;
  margin-bottom: 2px;
}}

#resume-preview .item-sub {{
  font-size: 10.5pt;
  color: #444;
  margin-bottom: 2px;
}}

#resume-preview .item-date {{
  font-size: 10pt;
  color: #666;
  font-style: italic;
  margin-bottom: 2px;
}}

#resume-preview .item-meta {{
  font-size: 10pt;
  color: #555;
  margin-top: 2px;
}}

#resume-preview .item-desc {{
  font-size: 10.5pt;
  color: #333;
  margin-top: 3px;
  line-height: 1.5;
}}

#resume-preview .item-link {{
  color: #1d4ed8;
  text-decoration: none;
  font-size: 10pt;
}}

/* ================= LISTS ================= */

#resume-preview ul {{
  margin: 4px 0 4px 18px;
  padding: 0;
}}

#resume-preview li {{
  margin-bottom: 4px;
  font-size: 10.5pt;
}}

#resume-preview .skills-list {{
  list-style-type: square;
}}

#resume-preview p {{
  margin: 0;
  line-height: 1.6;
  font-size: 10.5pt;
}}

/* ================= LANGUAGES ================= */

#resume-preview .lang-list {{
  display: flex;
  flex-direction: column;
  gap: 9px;
}}

#resume-preview .lang-item {{
  break-inside: avoid;
}}

#resume-preview .lang-name-row {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 3px;
}}

#resume-preview .lang-name {{
  font-weight: bold;
  font-size: 10.5pt;
}}

#resume-preview .lang-level {{
  font-size: 9pt;
  color: #777;
  font-style: italic;
}}

#resume-preview .lang-bar-bg {{
  width: 100%;
  height: 5px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}}

#resume-preview .lang-bar-fill {{
  height: 100%;
  background: #222;
  border-radius: 3px;
}}

</style>
</head>

<body>
<div id="resume-preview">
<div class="page">

    <!-- HEADER -->
    <div class="header">
        <div class="name">{personal.get("firstName", "")} {personal.get("lastName", "")}</div>
        {"<div class='profession'>" + personal.get("profession", "") + "</div>" if personal.get("profession") else ""}
        <div class="contact">
            {personal.get("email", "")}
            {" | " + personal.get("phone", "") if personal.get("phone") else ""}
            {" | " + personal.get("city", "") + (", " + personal.get("country", "") if personal.get("country") else "") if personal.get("city") else ""}
            {"<br><a href='" + personal.get("linkedin", "") + "' target='_blank'>" + personal.get("linkedin", "") + "</a>" if personal.get("linkedin") else ""}
            {websites_str}
        </div>
    </div>

    <div class="content">

        <!-- LEFT COLUMN: Skills, Education, Languages -->
        <div class="left-column">

            {section("Skills", skills_html)}

            {section("Education", education_html)}

            {section("Certifications &amp; Achievements", certifications_html)}

            {section("Languages", languages_html)}

        </div>

        <!-- RIGHT COLUMN: Summary, Experience, Projects, Certifications -->
        <div class="right-column">

            {section("Professional Summary", "<p>" + summary + "</p>" if summary else "")}

            {section("Professional Experience", experience_html)}

            {section("Projects", projects_html)}

            

        </div>

    </div>

</div>
</div>
</body>
</html>
"""