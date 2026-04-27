import os
import tempfile

from playwright.sync_api import sync_playwright

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
    payload = dict(data or {})
    experience = payload.get("experience", [])
    normalized_experience = []

    for exp in experience:
        item = dict(exp)
        description = item.get("description", "")
        if isinstance(description, str):
            item["description"] = description.replace("\n", "<br>")
        normalized_experience.append(item)

    payload["experience"] = normalized_experience
    return payload


def render_html(template_name, data):
    prepared_data = preprocess_descriptions(data)

    match template_name:
        case "modern":
            return modern.render(prepared_data)
        case "classic":
            return classic.render(prepared_data)
        case "twocolumn":
            return twocolumn.render(prepared_data)
        case "creative":
            return creative.render(prepared_data)
        case "corporate":
            return corporate.render(prepared_data)
        case "academic":
            return academic.render(prepared_data)
        case "ats":
            return ats.render(prepared_data)
        case "minimal":
            return minimal.render(prepared_data)
        case "sidebar":
            return sidebar.render(prepared_data)
        case "timeline":
            return timeline.render(prepared_data)
        case "striped":
            return striped.render(prepared_data)
        case "architect":
            return architect.render(prepared_data)
        case "pastel":
            return pastel.render(prepared_data)
        case "warm":
            return warm.render(prepared_data)
        case "technical":
            return technical.render(prepared_data)
        case "typographic":
            return typographic.render(prepared_data)
        case "bold":
            return bold.render(prepared_data)
        case _:
            return classic.render(prepared_data)


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
