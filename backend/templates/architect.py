def safe_int(v):
    try: return int(v)
    except: return 0

def render(data):
    personal       = data.get("personal", {})
    summary        = data.get("summary", "")
    skills         = data.get("skills", [])
    education      = data.get("education", [])
    experience     = data.get("experience", [])
    projects       = data.get("projects", [])
    certifications = data.get("certifications", [])
    languages      = data.get("languages", [])

    month_map = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                 "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    experience = sorted(experience, key=lambda x:(9999 if x.get("current") else safe_int(x.get("endYear",0)),12 if x.get("current") else month_map.get(x.get("endMonth",""),0)),reverse=True)
    education  = sorted(education,  key=lambda x:(safe_int(x.get("gradYear",0)),month_map.get(x.get("gradMonth",""),0)),reverse=True)

    def sec(title, content):
        if not content.strip(): return ""
        return f"""<div class='ar-section'>
          <div class='ar-sec-row'>
            <div class='ar-sec-label'>{title.upper()}</div>
            <div class='ar-sec-content'>{content}</div>
          </div>
        </div>"""

    exp_html = ""
    for e in experience:
        end  = "Present" if e.get("current") else f"{e.get('endMonth','')} {e.get('endYear','')}"
        desc = f"<div class='ar-desc'>{e.get('description','')}</div>" if e.get("description","").strip() else ""
        exp_html += f"""<div class='ar-item'>
          <div class='ar-item-grid'>
            <div class='ar-item-date'>{e.get('startYear','')}&thinsp;&mdash;&thinsp;{end.split(' ')[-1] if end != 'Present' else 'PRESENT'}</div>
            <div class='ar-item-body'>
              <div class='ar-item-title'>{e.get('title','').upper()}</div>
              <div class='ar-item-org'>{e.get('employer','')}{' &thinsp;&middot;&thinsp; '+e.get('location','') if e.get('location') else ''}</div>
              {desc}
            </div>
          </div>
        </div>"""

    edu_html = ""
    for e in education:
        gpa = f" &thinsp;&middot;&thinsp; GPA {e.get('gpa')}" if e.get("gpa","").strip() else ""
        edu_html += f"""<div class='ar-item'>
          <div class='ar-item-grid'>
            <div class='ar-item-date'>{e.get('gradYear','')}</div>
            <div class='ar-item-body'>
              <div class='ar-item-title'>{(e.get('degree','') + (' - ' + e.get('field','') if e.get('field') else '')).upper()}</div>
              <div class='ar-item-org'>{e.get('school','')}{', '+e.get('location','') if e.get('location') else ''}{gpa}</div>
            </div>
          </div>
        </div>"""

    proj_html = ""
    for p in projects:
        lines = []
        if p.get("role","").strip():  lines.append(f"ROLE &thinsp;&mdash;&thinsp; {p.get('role','').upper()}")
        if p.get("tools","").strip(): lines.append(f"TOOLS &thinsp;&mdash;&thinsp; {p.get('tools')}")
        sub_h  = f"<div class='ar-item-org'>{' &nbsp; '.join(lines)}</div>" if lines else ""
        desc_h = f"<div class='ar-desc'>{p.get('description','')}</div>" if p.get("description","").strip() else ""
        url_h  = f"<div class='ar-link'><a href='{p.get('url')}' target='_blank'>{p.get('url')}</a></div>" if p.get("url","").strip() else ""
        proj_html += f"<div class='ar-item'><div class='ar-item-grid'><div class='ar-item-date'></div><div class='ar-item-body'><div class='ar-item-title'>{p.get('title','').upper()}</div>{sub_h}{desc_h}{url_h}</div></div></div>"

    cert_html = ""
    for c in certifications:
        parts = []
        if c.get("issuingOrg","").strip():  parts.append(c.get("issuingOrg").upper())
        if c.get("achievedDate","").strip(): parts.append(c.get("achievedDate"))
        sub_h = f"<div class='ar-item-org'>{' &thinsp;&middot;&thinsp; '.join(parts)}</div>" if parts else ""
        url_h = f"<div class='ar-link'><a href='{c.get('url')}' target='_blank'>VIEW CREDENTIAL</a></div>" if c.get("url","").strip() else ""
        cert_html += f"<div class='ar-item'><div class='ar-item-grid'><div class='ar-item-date'></div><div class='ar-item-body'><div class='ar-item-title'>{c.get('name','').upper()}</div>{sub_h}{url_h}</div></div></div>"

    sk_html = ""
    if skills:
        filtered = [s for s in skills if s.strip()]
        sk_html = "<div class='ar-skill-grid'>" + "".join(f"<span class='ar-skill'>{s.upper()}</span>" for s in filtered) + "</div>"

    lv = {"Beginner":20,"Elementary":35,"Intermediate":55,"Upper Intermediate":70,"Advanced":85,"Native":100,"Native / Bilingual":100}
    lang_html = ""
    if languages:
        lang_html = "<div class='ar-lang-list'>"
        for l in languages:
            if not l.get("name","").strip(): continue
            pct = lv.get(l.get("level","Intermediate"),55)
            lang_html += f"<div class='ar-lang-item'><span class='ar-lang-name'>{l.get('name','').upper()}</span><div class='ar-bar-track'><div class='ar-bar-fill' style='width:{pct}%'></div></div><span class='ar-lang-lv'>{l.get('level','').upper()}</span></div>"
        lang_html += "</div>"

    websites = [w for w in personal.get("websites",[]) if w.strip()]
    c_parts = []
    if personal.get("city"):
        loc = personal.get("city").upper()
        if personal.get("country"): loc += ", " + personal.get("country").upper()
        c_parts.append(loc)
    if personal.get("phone"):    c_parts.append(personal.get("phone"))
    if personal.get("email"):    c_parts.append(personal.get("email"))
    if personal.get("linkedin"): c_parts.append(personal.get("linkedin"))
    for w in websites:           c_parts.append(w)
    contact_html = " &thinsp;&mdash;&thinsp; ".join(c_parts)

    return f"""
<style>
  #resume-preview * {{ margin:0; padding:0; box-sizing:border-box; }}
  #resume-preview {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:9pt; color:#111; background:#fff; line-height:1.5; }}
  #resume-preview .page {{ width:210mm; min-height:277mm; height:auto; padding:16mm 20mm; background:#fff; }}

  /* Header — strict grid top */
  #resume-preview .ar-header {{ border-top:1.5px solid #111; border-bottom:0.5px solid #111; padding:12px 0 10px 0; margin-bottom:18px; display:grid; grid-template-columns:1fr auto; gap:8px; align-items:end; }}
  #resume-preview .ar-name {{ font-size:19pt; font-weight:300; color:#000; text-transform:uppercase; letter-spacing:4px; line-height:1; }}
  #resume-preview .ar-profession {{ font-size:7.5pt; text-transform:uppercase; letter-spacing:3px; color:#555; margin-top:5px; }}
  #resume-preview .ar-contact {{ font-size:7.5pt; color:#555; text-align:right; line-height:1.8; text-transform:uppercase; letter-spacing:0.3px; }}

  /* Section */
  #resume-preview .ar-section {{ margin-bottom:14px; border-top:0.5px solid #aaa; padding-top:10px; page-break-inside:avoid; break-inside:avoid; }}
  #resume-preview .ar-sec-row {{ display:flex; gap:0; }}
  #resume-preview .ar-sec-label {{ width:130px; flex-shrink:0; font-size:7pt; font-weight:700; text-transform:uppercase; letter-spacing:2.5px; color:#777; padding-right:16px; padding-top:1px; }}
  #resume-preview .ar-sec-content {{ flex:1; border-left:0.5px solid #ccc; padding-left:16px; }}

  /* Items */
  #resume-preview .ar-item {{ margin-bottom:10px; page-break-inside:avoid; break-inside:avoid; }}
  #resume-preview .ar-item-grid {{ display:grid; grid-template-columns:60px 1fr; gap:0 12px; }}
  #resume-preview .ar-item-date {{ font-size:7.5pt; color:#888; text-align:right; padding-top:1px; line-height:1.4; text-transform:uppercase; letter-spacing:0.5px; }}
  #resume-preview .ar-item-title {{ font-size:9.5pt; font-weight:700; color:#000; letter-spacing:0.5px; line-height:1.3; }}
  #resume-preview .ar-item-org {{ font-size:8pt; color:#555; margin-top:2px; }}
  #resume-preview .ar-desc {{ font-size:8.5pt; color:#333; margin-top:4px; line-height:1.5; }}
  #resume-preview .ar-link a, #resume-preview a.ar-link {{ font-size:7.5pt; color:#111; text-decoration:underline; text-transform:uppercase; letter-spacing:0.5px; }}

  /* Summary */
  #resume-preview .ar-summary {{ font-size:9pt; color:#555; line-height:1.65; padding-left:72px; }}

  /* Skills */
  #resume-preview .ar-skill-grid {{ display:flex; flex-wrap:wrap; gap:4px 8px; }}
  #resume-preview .ar-skill {{ font-size:7.5pt; color:#111; padding:2px 7px; border:0.5px solid #aaa; text-transform:uppercase; letter-spacing:0.5px; }}

  /* Languages */
  #resume-preview .ar-lang-list {{ display:flex; flex-direction:column; gap:7px; }}
  #resume-preview .ar-lang-item {{ display:grid; grid-template-columns:80px 1fr 110px; gap:10px; align-items:center; }}
  #resume-preview .ar-lang-name {{ font-size:8pt; font-weight:700; text-transform:uppercase; letter-spacing:1px; }}
  #resume-preview .ar-bar-track {{ height:1px; background:#ccc; position:relative; }}
  #resume-preview .ar-bar-fill {{ position:absolute; top:0; left:0; height:100%; background:#111; }}
  #resume-preview .ar-lang-lv {{ font-size:7pt; color:#888; text-transform:uppercase; letter-spacing:0.5px; text-align:right; }}


  @media print {{
  body, html {{ margin: 0; padding: 0; }}

  #resume-preview .page {{
    min-height: 277mm;
    padding: 0;
    margin: 0;
    width: 190mm;
    box-shadow: none;
  }}


  #resume-preview .ar-section{{
    margin-top: 14px;
    page-break-inside: avoid !important;
    break-inside: avoid !important;
  }}

  #resume-preview .ar-section-header {{
    page-break-after: avoid;
  }}

  #resume-preview .ar-item {{
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

<div id="resume-preview"><div class="page">

  <div class="ar-header">
    <div>
      <div class="ar-name">{personal.get("firstName","")} {personal.get("lastName","")}</div>
      {"<div class='ar-profession'>" + personal.get("profession","").upper() + "</div>" if personal.get("profession") else ""}
    </div>
    <div class="ar-contact">{contact_html}</div>
  </div>

  {sec("Profile", f"<div class='ar-summary'>{summary}</div>") if summary else ""}
  {sec("Skills", sk_html)}
  {sec("Experience", exp_html)}
  {sec("Education", edu_html)}
  {sec("Projects", proj_html)}
  {sec("Certifications", cert_html)}
  {sec("Languages", lang_html)}

</div></div>"""