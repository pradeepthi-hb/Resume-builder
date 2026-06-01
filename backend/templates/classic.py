def render(data):
    personal       = data.get("personal", {})
    summary        = data.get("summary", "")
    skills         = data.get("skills", [])
    education      = data.get("education", [])
    experience     = data.get("experience", [])
    projects       = data.get("projects", [])
    certifications = data.get("certifications", [])
    languages      = data.get("languages", [])

    #  Skills 
    skills_html = ""
    if skills:
        skills_html = "<ul class='skills-list'>"
        for s in skills:
            if s.strip():
                skills_html += f"<li>{s}</li>"
        skills_html += "</ul>"

    #  Education 
    education_html = ""
    for edu in education:
        school = edu.get("school", "").strip()
        location = edu.get("location", "").strip()
        degree = edu.get("degree", "").strip()
        field = edu.get("field", "").strip()
        gpa = edu.get("gpa", "").strip()
        grad_month = edu.get("gradMonth", "").strip()
        grad_year = edu.get("gradYear", "").strip()

        if not any([school, location, degree, field, gpa, grad_month, grad_year]):
            continue

        gpa_str = f" &nbsp;|&nbsp; GPA: {gpa}" if gpa else ""
        degree_line = ""
        if degree and field:
            degree_line = f"{degree} &ndash; {field}"
        elif degree:
            degree_line = degree
        elif field:
            degree_line = field

        school_line = school if school else ""
        if location:
            school_line = f"{school_line}{', ' if school_line else ''}{location}"

        date_line = f"{grad_month} {grad_year}".strip()
        education_html += f"""
        <div class="item">
          {f"<div class='item-header'><strong>{school_line}</strong></div>" if school_line else ""}
          {f"<div class='item-subheader'>{degree_line}{gpa_str}</div>" if degree_line or gpa_str else ""}
          {f"<div class='item-date'>{date_line}</div>" if date_line else ""}
        </div>
        """

    #  Experience 
    experience_html = ""
    for exp in experience:
        title = exp.get("title", "").strip()
        employer = exp.get("employer", "").strip()
        location = exp.get("location", "").strip()
        start = f"{exp.get('startMonth', '').strip()} {exp.get('startYear', '').strip()}".strip()
        end_date = "Present" if exp.get("current") else f"{exp.get('endMonth', '').strip()} {exp.get('endYear', '').strip()}".strip()
        date_line = f"{start} &ndash; {end_date}".strip(" &ndash;")
        if not title and not employer and not exp.get("description", "").strip():
            continue
        experience_html += f"""
        <div class="item">
          {f"<div class='item-header'><strong>{title}</strong>{' &ndash; ' + employer if employer else ''}</div>" if title else ""}
          {f"<div class='item-header'><strong>{employer}</strong></div>" if (not title and employer) else ""}
          {f"<div class='item-subheader'>{location}</div>" if location else ""}
          {f"<div class='item-date'>{date_line}</div>" if date_line else ""}
          {"<div class='item-desc'>" + exp.get('description','') + "</div>" if exp.get('description','').strip() else ""}
          
        </div>
        """

    #  Projects 
    projects_html = ""
    for proj in projects:
        url_html = ""
        if proj.get("url", "").strip():
            url_html = f'<div class="item-link"><a href="{proj.get("url")}" target="_blank">{proj.get("url")}</a></div>'

        role_tools_parts = []
        if proj.get("role", "").strip():
            role_tools_parts.append(f"<strong>Role:</strong> {proj.get('role')}")
        if proj.get("tools", "").strip():
            role_tools_parts.append(f"<strong>Tools &amp; Tech:</strong> {proj.get('tools')}")
        role_tools_html = f'<div class="item-subheader">{" &nbsp;|&nbsp; ".join(role_tools_parts)}</div>' if role_tools_parts else ""

        desc_html = f'<div class="item-desc">{proj.get("description", "")}</div>' if proj.get("description", "").strip() else ""

        projects_html += f"""
        <div class="item">
          <div class="item-header">
            <strong>{proj.get("title", "")}</strong>
          </div>
          {role_tools_html}
          {desc_html}
          {url_html}
        </div>
        """

    # ── Certifications & Achievements ─────────────────────────────────────────
    certifications_html = ""
    for cert in certifications:
        url_html = ""
        if cert.get("url", "").strip():
            url_html = f'<a class="item-link" href="{cert.get("url")}" target="_blank">View Credential</a>'

        org_date_parts = []
        if cert.get("issuingOrg", "").strip():
            org_date_parts.append(cert.get("issuingOrg"))
        if cert.get("achievedDate", "").strip():
            org_date_parts.append(cert.get("achievedDate"))

        meta_html = f'<div class="item-subheader">{" &nbsp;&bull;&nbsp; ".join(org_date_parts)}</div>' if org_date_parts else ""

        certifications_html += f"""
        <div class="item">
          <div class="item-header">
            <strong>{cert.get("name", "")}</strong>
            {" &nbsp;" + url_html if url_html else ""}
          </div>
          {meta_html}
        </div>
        """

    # ── Languages ─────────────────────────────────────────────────────────────
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
        languages_html = "<div class='languages-grid'>"
        for lang in languages:
            if not lang.get("name", "").strip():
                continue
            level  = lang.get("level", "Intermediate")
            pct    = level_widths.get(level, 55)
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

    # ── Websites (personal) ───────────────────────────────────────────────────
    websites = personal.get("websites", [])
    websites_html = ""
    if websites:
        links = [f'<a href="{w}" target="_blank">{w}</a>' for w in websites if w.strip()]
        if links:
            websites_html = " | ".join(links)

    contact_parts = []
    city = personal.get("city", "").strip()
    country = personal.get("country", "").strip()
    pincode = personal.get("pincode", "").strip()
    phone = personal.get("phone", "").strip()
    email = personal.get("email", "").strip()
    linkedin = personal.get("linkedin", "").strip()

    location_line = ""
    if city:
        location_line = city
        if country:
            location_line += ", " + country
        if pincode:
            location_line += " " + pincode
    elif country:
        location_line = country + (f" {pincode}" if pincode else "")

    if phone:
        contact_parts.append(phone)
    if email:
        contact_parts.append(email)
    if linkedin:
        contact_parts.append(f"<a href='{linkedin}' target='_blank'>{linkedin}</a>")
    if websites_html:
        contact_parts.append(websites_html)

    # ── Conditional section builder ───────────────────────────────────────────
    def section(title, content):
        if not content.strip():
            return ""
        return f"<div class='section'><h3>{title}</h3>{content}</div>"

    return f"""
    <style>
        #resume-preview * {{
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }}

        #resume-preview {{
          font-family: Arial, sans-serif;
          font-size: 11pt;
          line-height: 1.4;
          color: #000;
          background: #fff;
        }}

        #resume-preview .page {{
          width: 210mm;
          min-height: 277mm;
          padding: 20mm;
          background: white;
        }}


        #resume-preview h1 {{
          font-size: 24pt;
          margin-bottom: 4px;
          font-weight: bold;
          text-transform: uppercase;
        }}

        #resume-preview h3 {{
          font-size: 14pt;
          margin-bottom: 8px;
          color: #333;
        }}

        #resume-preview .contact-info {{
          margin-bottom: 16px;
          font-size: 10pt;
          line-height: 1.6;
          color: #444;
        }}

        #resume-preview .contact-info a {{
          color: #444;
          text-decoration: none;
        }}

        #resume-preview .section {{
          margin-bottom: 16px;
          page-break-inside: auto;
          break-inside: auto;
        }}


        #resume-preview .section h3 {{
          font-size: 12pt;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border-bottom: 1.5px solid #333;
          padding-bottom: 4px;
          margin-bottom: 10px;
          color: #000;
        }}

        #resume-preview .item {{
          margin-bottom: 12px;
          page-break-inside: avoid;
          break-inside: avoid;
        }}

        #resume-preview .item-header {{
          font-size: 11pt;
          margin-bottom: 2px;
        }}

        #resume-preview .item-subheader {{
          font-size: 10pt;
          color: #333;
          margin-bottom: 2px;
        }}

        #resume-preview .item-date {{
          font-size: 10pt;
          color: #666;
          font-style: italic;
          margin-bottom: 2px;
        }}

        #resume-preview .item-desc {{
          font-size: 10pt;
          color: #333;
          margin-top: 4px;
          line-height: 1.5;
        }}

        #resume-preview .item-link {{
          font-size: 9.5pt;
          margin-top: 3px;
        }}

        #resume-preview .item-link a {{
          color: #2563EB;
          text-decoration: none;
        }}

        #resume-preview .item-link a:hover {{
          text-decoration: underline;
        }}

        /* ── Skills ── */
        #resume-preview .skills-list {{
          list-style-type: disc;
          margin-left: 20px;
          column-count: 2;
          column-gap: 20px;
        }}

        #resume-preview .skills-list li {{
          margin-bottom: 4px;
          break-inside: avoid;
          font-size: 10.5pt;
        }}

        /* ── Languages ── */
        #resume-preview .languages-grid {{
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          column-gap: 24px;
          row-gap: 10px;
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
          font-size: 10.5pt;
          font-weight: bold;
          color: #111;
        }}

        #resume-preview .lang-level {{
          font-size: 9pt;
          color: #666;
          font-style: italic;
        }}

        #resume-preview .lang-bar-bg {{
          width: 100%;
          height: 5px;
          background: #e5e7eb;
          border-radius: 3px;
          overflow: hidden;
        }}

        #resume-preview .lang-bar-fill {{
          height: 100%;
          background: #374151;
          border-radius: 3px;
          transition: width 0.3s ease;
        }}

        @media print {{
          body, html {{ margin: 0; padding: 0; }}

          #resume-preview .page {{
            min-height: 277mm;
            padding: 0;
            margin: 0;
            width: 190mm;
            box-shadow: none;
          }}

          #resume-preview .page:last-child {{
            page-break-after: avoid;
            break-after: avoid;
          }}

          #resume-preview .section{{
            margin-top: 14px;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
          }}

          #resume-preview.section-header {{
            page-break-after: avoid;
          }}

          #resume-preview .item {{
            page-break-inside: avoid !important;
            break-inside: avoid !important;
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
                  
       
      </style>
    <div id="resume-preview" >
    <div class="page">

        <!-- HEADER -->
        <h1>{personal.get("firstName", "")} {personal.get("lastName", "")}</h1>
        {"<h3>" + personal.get("profession", "") + "</h3>" if personal.get("profession") else ""}

        <div class="contact-info">
          {location_line + "<br>" if location_line else ""}
          {" | ".join(contact_parts)}
        </div>

        <!-- SUMMARY -->
        {section("Professional Summary", "<p>" + summary + "</p>" if summary else "")}

        <!-- SKILLS -->
        {section("Skills", skills_html)}

        <!-- EDUCATION -->
        {section("Education", education_html)}

        <!-- EXPERIENCE -->
        {section("Experience", experience_html)}

        <!-- PROJECTS -->
        {section("Projects", projects_html)}

        <!-- CERTIFICATIONS & ACHIEVEMENTS -->
        {section("Certifications &amp; Achievements", certifications_html)}

        <!-- LANGUAGES -->
        {section("Languages", languages_html)}

        </div>
      </div>
    """
