import json
import uuid
from io import BytesIO
from urllib import error, request as urllib_request

from flask import Blueprint, current_app, jsonify, request, send_file

from analytics import analyze_resume
from services.integration_session_store import IntegrationSessionStore
from services.resume_rendering import render_html, render_pdf_bytes

integration_bp = Blueprint("integration", __name__, url_prefix="/api/integrations")

DEFAULT_FORM = {
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


def _split_name(candidate_name):
    if not candidate_name:
        return "", ""

    parts = [part for part in str(candidate_name).strip().split(" ") if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _pick_first_nonempty(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_role(value):
    role = str(value or "").strip().lower()
    if role in {"candidate", "company"}:
        return role
    return ""


def _parse_bool_like(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _get_session_store():
    store = current_app.extensions.get("hireyo_session_store")
    if store:
        return store

    store = IntegrationSessionStore(
        redis_url=current_app.config.get("REDIS_URL", ""),
        ttl_seconds=current_app.config.get("HIREYO_SESSION_TTL_SECONDS", 1800),
        key_prefix=current_app.config.get("HIREYO_SESSION_KEY_PREFIX", "hireyo:session:"),
    )
    current_app.extensions["hireyo_session_store"] = store
    return store


def _draft_to_resume_data(draft):
    return {key: value for key, value in draft.items() if key != "template"}


def _preview_payload(draft):
    resume_data = _draft_to_resume_data(draft)
    analytics = analyze_resume(resume_data)
    html = render_html(draft.get("template", "classic"), draft)
    return analytics, html


def _load_session(token):
    return _get_session_store().get(token)


def _save_session(token, data):
    print("🔥 SESSION SET CALLED", token, data)
    _get_session_store().set(token, data)


def _build_default_draft(candidate_name, candidate_email):
    draft = json.loads(json.dumps(DEFAULT_FORM))
    first_name, last_name = _split_name(candidate_name)
    draft["personal"]["firstName"] = first_name
    draft["personal"]["lastName"] = last_name
    draft["personal"]["email"] = candidate_email or ""
    return draft


def _validate_integration_request():
    token = request.args.get("token")

    if not token and request.is_json:
        token = request.json.get("token")

    token = (token or "").strip()
    if not token:
        return None, (jsonify({"error": "Launch token is required."}), 400)

    session = _load_session(token)
    if not session:
        return None, (jsonify({"error": "Launch session was not found or has expired."}), 404)

    return (token, session), None


def _build_resume_name(session, explicit_name):
    if explicit_name:
        return explicit_name.strip()[:150]

    candidate_name = session.get("candidate_name") or "Candidate"
    return f"{candidate_name} Resume"[:150]


def _encode_multipart(fields, files):
    boundary = f"----ResumeBuilder{uuid.uuid4().hex}"
    chunks = []

    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    for name, file_info in files.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{file_info["filename"]}"\r\n'
            ).encode("utf-8")
        )
        chunks.append(f'Content-Type: {file_info["content_type"]}\r\n\r\n'.encode("utf-8"))
        chunks.append(file_info["content"])
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)
    return body, boundary


@integration_bp.route("/hireyo/session", methods=["GET"])
def hireyo_session():
    token = (request.args.get("token") or "").strip()
    callback_url = (request.args.get("callback_url") or "").strip()
    return_url = (request.args.get("return_url") or "").strip()
    candidate_name = (request.args.get("candidate_name") or "").strip()
    candidate_email = (request.args.get("candidate_email") or "").strip()
    launch_role = _normalize_role(
        _pick_first_nonempty(
            request.args.get("role"),
            request.args.get("candidate_role"),
            request.args.get("user_role"),
            request.args.get("launch_role"),
        )
    )
    launch_is_verified = _parse_bool_like(
        _pick_first_nonempty(
            request.args.get("is_verified"),
            request.args.get("verified"),
            request.args.get("candidate_verified"),
            request.args.get("user_verified"),
        )
    )

    if not token:
        return jsonify({"error": "Launch token is required."}), 400

    session = _load_session(token)
    if not session:
        if not callback_url:
            return jsonify({"error": "callback_url is required for a new integration session."}), 400

        draft = _build_default_draft(candidate_name, candidate_email)
        session = {
            "token": token,
            "callback_url": callback_url,
            "return_url": return_url,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "launch_role": launch_role or "candidate",
            "launch_is_verified": True if launch_is_verified is None else bool(launch_is_verified),
            "draft": draft,
        }
        _save_session(token, session)
    else:
        # Refresh role/verification hints when provided by launcher.
        if launch_role:
            session["launch_role"] = launch_role
        if launch_is_verified is not None:
            session["launch_is_verified"] = bool(launch_is_verified)
        _save_session(token, session)

    analytics, html = _preview_payload(session["draft"])

    return jsonify(
        {
            "token": token,
            "candidate_name": session.get("candidate_name"),
            "candidate_email": session.get("candidate_email"),
            "launch_role": session.get("launch_role", "candidate"),
            "launch_is_verified": bool(session.get("launch_is_verified", True)),
            "return_url": session.get("return_url"),
            "callback_url": session.get("callback_url"),
            "draft": session["draft"],
            "resume_html": html,
            "analytics": analytics,
        }
    )


@integration_bp.route("/hireyo/draft", methods=["PUT"])
def save_hireyo_draft():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()

    if not token:
        return jsonify({"error": "Launch token is required."}), 400

    session = _load_session(token)
    if not session:
        return jsonify({"error": "Launch session was not found or has expired."}), 404

    draft = {**DEFAULT_FORM, **{k: v for k, v in payload.items() if k != "token"}}
    session["draft"] = draft
    _save_session(token, session)

    analytics, html = _preview_payload(draft)

    return jsonify(
        {
            "message": "Draft saved",
            "resume_html": html,
            "analytics": analytics,
            "resume_id": token,
        }
    )


@integration_bp.route("/hireyo/download", methods=["GET"])
def download_hireyo_resume():
    result, error_response = _validate_integration_request()
    if error_response:
        return error_response

    token, session = result
    html = render_html(session["draft"].get("template", "classic"), session["draft"])
    pdf_bytes = render_pdf_bytes(html)

    return send_file(
        BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=f"hireyo-resume-{token}.pdf",
        mimetype="application/pdf",
    )


@integration_bp.route("/hireyo/submit", methods=["POST"])
def submit_hireyo_resume():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()

    if not token:
        return jsonify({"error": "Launch token is required."}), 400

    session = _load_session(token)
    if not session:
        return jsonify({"error": "Launch session was not found or has expired."}), 404

    callback_url = (session.get("callback_url") or "").strip()
    if not callback_url:
        return jsonify({"error": "No callback URL is configured for this launch session."}), 400

    secret = (current_app.config.get("HIREYO_SHARED_SECRET") or "").strip()
    if not secret:
        return jsonify({"error": "HIREYO_SHARED_SECRET is not configured on the resume builder."}), 500

    draft = session["draft"]
    html = render_html(draft.get("template", "classic"), draft)
    pdf_bytes = render_pdf_bytes(html)
    resume_name = _build_resume_name(session, payload.get("resume_name"))

    fields = {
        "token": token,
        "resume_name": resume_name,
        "builder_resume_id": token,
        "template": draft.get("template", "classic"),
    }

    builder_url = (current_app.config.get("HIREYO_BUILDER_URL") or "").strip()
    if builder_url:
        fields["builder_url"] = builder_url

    body, boundary = _encode_multipart(
        fields,
        {
            "resume_file": {
                "filename": "resume.pdf",
                "content_type": "application/pdf",
                "content": pdf_bytes,
            }
        },
    )

    outbound_request = urllib_request.Request(
        callback_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "X-Resume-Builder-Secret": secret,
        },
    )

    try:
        with urllib_request.urlopen(outbound_request, timeout=30) as response:
            raw_body = response.read().decode("utf-8", errors="ignore")
            try:
                callback_response = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                callback_response = {"raw": raw_body}

        return jsonify(
            {
                "message": "Resume submitted to Hireyo successfully.",
                "return_url": session.get("return_url"),
                "callback_response": callback_response,
            }
        )
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return (
            jsonify(
                {
                    "error": "Hireyo rejected the generated resume.",
                    "status": exc.code,
                    "details": details,
                }
            ),
            502,
        )
    except Exception as exc:
        return jsonify({"error": "Failed to send resume to Hireyo.", "details": str(exc)}), 502
