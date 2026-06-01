import os
import re
import tempfile
from html import escape

from playwright.sync_api import sync_playwright
from services.import_resume_service import sanitize_resume_for_render

from templates import (
    academic,
    architect,
    ats,
    bold,
    classic,
    corporate,
    creative,
    minimal,
    modern,
    pastel,
    sidebar,
    striped,
    technical,
    timeline,
    twocolumn,
    typographic,
    warm,
)


def preprocess_descriptions(data):
    payload = sanitize_resume_for_render(data or {})
    experience = payload.get("experience", [])
    normalized_experience = []
    projects = payload.get("projects", [])
    normalized_projects = []

    def _format_description_as_bullets(description):
        if not isinstance(description, str):
            return ""

        text = description.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return ""

        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) <= 1:
            return escape(text).replace("\n", "<br>")

        bullet_lines = []
        for line in lines:
            # Remove existing bullet/numbering prefixes before reformatting.
            clean = re.sub(r"^\s*(?:[-*•]+|\d+[\.\)])\s*", "", line).strip()
            if not clean:
                continue
            bullet_lines.append(f"&#8226; {escape(clean)}")

        if not bullet_lines:
            return escape(text).replace("\n", "<br>")

        return "<br>".join(bullet_lines)

    for exp in experience:
        item = dict(exp)
        description = item.get("description", "")
        item["description"] = _format_description_as_bullets(description)
        normalized_experience.append(item)

    for proj in projects:
        item = dict(proj)
        description = item.get("description", "")
        item["description"] = _format_description_as_bullets(description)
        normalized_projects.append(item)

    payload["experience"] = normalized_experience
    payload["projects"] = normalized_projects
    return payload


def _sanitize_rendered_html(html):
    if not isinstance(html, str) or not html.strip():
        return ""

    cleaned = html

    # Remove empty heading/strong/paragraph/div blocks that collapse layout.
    cleaned = re.sub(r"<strong>\s*</strong>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<h[1-6][^>]*>\s*</h[1-6]>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<p>\s*</p>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<div[^>]*>\s*</div>", "", cleaned, flags=re.IGNORECASE)

    # Normalize repeated separators and malformed connector fragments.
    cleaned = re.sub(r"(?:\s*\|\s*){2,}", " | ", cleaned)
    cleaned = re.sub(r"(?:\s*&nbsp;\|&nbsp;\s*){2,}", " &nbsp;|&nbsp; ", cleaned)
    cleaned = re.sub(r"(?:\s*-\s*){2,}", " - ", cleaned)
    cleaned = re.sub(r">\s*[|\-]\s*<", "><", cleaned)
    cleaned = re.sub(r"\|\s*(</div>|<br\s*/?>)", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(&nbsp;\|&nbsp;)\s*(</div>|<br\s*/?>)", r"\2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"GPA:\s*(</div>|<br\s*/?>)", r"\1", cleaned, flags=re.IGNORECASE)

    # Remove duplicate consecutive links with same href/text.
    cleaned = re.sub(
        r'(<a[^>]*href="([^"]+)"[^>]*>\s*([^<]+)\s*</a>)\s*(?:\|\s*)?\1',
        r"\1",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Collapse excessive breaks/spaces.
    cleaned = re.sub(r"(<br\s*/?>\s*){3,}", "<br><br>", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def render_html(template_name, data):
    prepared_data = preprocess_descriptions(data)

    match template_name:
        case "modern":
            html = modern.render(prepared_data)
        case "classic":
            html = classic.render(prepared_data)
        case "twocolumn":
            html = twocolumn.render(prepared_data)
        case "creative":
            html = creative.render(prepared_data)
        case "corporate":
            html = corporate.render(prepared_data)
        case "academic":
            html = academic.render(prepared_data)
        case "ats":
            html = ats.render(prepared_data)
        case "minimal":
            html = minimal.render(prepared_data)
        case "sidebar":
            html = sidebar.render(prepared_data)
        case "timeline":
            html = timeline.render(prepared_data)
        case "striped":
            html = striped.render(prepared_data)
        case "architect":
            html = architect.render(prepared_data)
        case "pastel":
            html = pastel.render(prepared_data)
        case "warm":
            html = warm.render(prepared_data)
        case "technical":
            html = technical.render(prepared_data)
        case "typographic":
            html = typographic.render(prepared_data)
        case "bold":
            html = bold.render(prepared_data)
        case _:
            html = classic.render(prepared_data)

    return _sanitize_rendered_html(html)


def render_pdf_bytes(html):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        try:
            page.set_content(html, wait_until="networkidle")

            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf_path = temp_pdf.name
            temp_pdf.close()

            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={
                    "top": "10mm",
                    "bottom": "10mm",
                    "left": "10mm",
                    "right": "10mm",
                },
            )

            with open(pdf_path, "rb") as file_handle:
                return file_handle.read()
        finally:
            browser.close()
            if "pdf_path" in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)
