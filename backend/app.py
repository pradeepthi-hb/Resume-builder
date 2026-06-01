import logging
from datetime import datetime
from io import BytesIO

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from analytics import analyze_resume
from config import Config
from extensions import db, jwt
from job_match import semantic_match, get_model
from models.resume import Resume
from routes.ai import ai_bp
from routes.auth import auth_bp
from routes.integration import integration_bp
from routes.occupation_routes import occupation_bp
from services.import_resume_service import (
    normalize_imported_resume,
    validate_parser_response,
)
from services.parser_client import ParserClient, ParserClientConfig, ParserClientError
from services.resume_rendering import render_html, render_pdf_bytes
from transformers import logging as hf_logging

hf_logging.set_verbosity_error()  # suppress warnings/info logs
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

CORS(
    app,
    resources={r"/api/*": {"origins": app.config.get("CORS_ALLOWED_ORIGINS", ["http://localhost:3000"])}},
    supports_credentials=True,
    allow_headers="*",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
db.init_app(app)
jwt.init_app(app)


META_KEY = "_meta"
LOCAL_ID_KEY = "local_resume_id"
MAX_IMPORT_FILE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_IMPORT_EXTENSIONS = {"pdf", "docx", "jpg", "jpeg", "png"}



def _extract_local_resume_id(resume):
    data = resume.resume_data if isinstance(resume.resume_data, dict) else {}
    meta = data.get(META_KEY) if isinstance(data.get(META_KEY), dict) else {}
    rid = meta.get(LOCAL_ID_KEY)
    return rid if isinstance(rid, int) and rid > 0 else None


def _next_local_resume_id(user_id):
    existing = _ensure_local_ids_for_user(user_id)
    return max([_extract_local_resume_id(r) or 0 for r in existing], default=0) + 1


def _coerce_confidence(value):
    try:
        conf = float(value)
        if conf < 0:
            return 0.0
        if conf > 1:
            return 1.0
        return conf
    except (TypeError, ValueError):
        return None


def _extract_import_file():
    uploaded = request.files.get("file")
    if not uploaded:
        return None, ("No file was uploaded.", 400, "missing_file")

    if not uploaded.filename:
        return None, ("Uploaded file has no filename.", 400, "invalid_file")

    filename = secure_filename(uploaded.filename)
    if "." not in filename:
        return None, ("Unsupported file type.", 400, "unsupported_format")
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_IMPORT_EXTENSIONS:
        logger.warning("Unsupported import format attempted: %s", ext)
        return None, ("Unsupported file type. Allowed: pdf, docx, jpg, jpeg, png.", 400, "unsupported_format")

    content_bytes = uploaded.read()
    if not content_bytes:
        return None, ("Uploaded file is empty.", 400, "empty_file")
    if len(content_bytes) > MAX_IMPORT_FILE_SIZE_BYTES:
        return None, ("Uploaded file is too large (max 10MB).", 413, "file_too_large")

    return (
        {
            "filename": filename,
            "content_type": uploaded.content_type or "application/octet-stream",
            "content_bytes": content_bytes,
        },
        None,
    )


def _get_parser_client():
    return ParserClient(
        ParserClientConfig(
            base_url=app.config.get("PARSER_API_URL", "http://localhost:8001"),
            connect_timeout=float(app.config.get("PARSER_CONNECT_TIMEOUT_SECONDS", 5)),
            read_timeout=float(app.config.get("PARSER_READ_TIMEOUT_SECONDS", 45)),
            max_retries=int(app.config.get("PARSER_MAX_RETRIES", 2)),
        )
    )


def _build_import_meta_for_db(parser_response, uploaded_filename):
    parser_metadata = parser_response.get("parser_metadata") if isinstance(parser_response, dict) else {}
    parser_metadata = parser_metadata if isinstance(parser_metadata, dict) else {}

    mapping_version = parser_metadata.get("parser_mapping_version") or parser_metadata.get("mapping_version")
    generated_at_raw = (
        parser_metadata.get("parser_generated_at")
        or parser_metadata.get("generated_at")
        or parser_metadata.get("created_at")
    )

    parser_generated_at = None
    if isinstance(generated_at_raw, str) and generated_at_raw.strip():
        try:
            parser_generated_at = datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            logger.warning("Invalid parser_generated_at format: %s", generated_at_raw)

    return {
        "source_type": "imported",
        "parser_confidence": _coerce_confidence(parser_response.get("confidence")),
        "original_resume_file": uploaded_filename,
        "parser_generated_at": parser_generated_at,
        "parser_mapping_version": str(mapping_version).strip()[:64] if mapping_version is not None else None,
    }


def _ensure_local_ids_for_user(user_id):
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.id.asc()).all()
    used = set()
    next_id = 1
    dirty = False

    for resume in resumes:
        rid = _extract_local_resume_id(resume)
        if rid is None or rid in used:
            while next_id in used:
                next_id += 1
            data = dict(resume.resume_data) if isinstance(resume.resume_data, dict) else {}
            meta = dict(data.get(META_KEY)) if isinstance(data.get(META_KEY), dict) else {}
            meta[LOCAL_ID_KEY] = next_id
            data[META_KEY] = meta
            resume.resume_data = data
            rid = next_id
            dirty = True
        used.add(rid)
        if rid >= next_id:
            next_id = rid + 1

    if dirty:
        db.session.commit()
    return resumes


def _get_resume_for_user(user_id, resume_id):
    if resume_id < 1:
        return None

    for resume in _ensure_local_ids_for_user(user_id):
        if _extract_local_resume_id(resume) == resume_id:
            return resume
    return Resume.query.filter_by(user_id=user_id, id=resume_id).first()

@jwt.unauthorized_loader
def missing_token(reason):
    return jsonify({"error": "JWT missing", "reason": reason}), 401

@jwt.invalid_token_loader
def invalid_token(reason):
    return jsonify({"error": "JWT invalid", "reason": reason}), 401

@jwt.expired_token_loader
def expired_token(jwt_header, jwt_payload):
    return jsonify({"error": "JWT expired"}), 401


app.register_blueprint(auth_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(occupation_bp)
app.register_blueprint(integration_bp)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Resume Builder API"})

@app.route("/api/resume", methods=["POST"])
@jwt_required()
def create_resume():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    template_name = data.get("template", "classic")
    resume_data = {k: v for k, v in data.items() if k != "template"}
    local_resume_id = _next_local_resume_id(user_id)

    meta = dict(resume_data.get(META_KEY)) if isinstance(resume_data.get(META_KEY), dict) else {}
    meta[LOCAL_ID_KEY] = local_resume_id
    resume_data[META_KEY] = meta

    resume = Resume(
        user_id=user_id,
        resume_data=resume_data,
        template=template_name,
        source_type="manual",
    )

    db.session.add(resume)          
    db.session.commit()

    analytics = analyze_resume(resume_data)
    html = render_html(template_name, resume.resume_data)

    return jsonify({
        "message": "Resume created",
        "resume_id": local_resume_id,
        "resume_html": html,
        "analytics": analytics
    }), 201


@app.route("/api/resumes/import", methods=["POST"])
@jwt_required()
def import_resume():
    user_id = int(get_jwt_identity())

    upload_payload, upload_error = _extract_import_file()
    if upload_error:
        message, status_code, error_code = upload_error
        return jsonify({"error": message, "code": error_code}), status_code

    parser_client = _get_parser_client()
    if not parser_client.check_availability():
        logger.error("Parser service unavailable before import attempt.")
        return jsonify({"error": "Parser service is currently unavailable.", "code": "parser_unavailable"}), 503

    try:
        parser_response = parser_client.parse_resume(
            filename=upload_payload["filename"],
            content_type=upload_payload["content_type"],
            content_bytes=upload_payload["content_bytes"],
        )
        validated = validate_parser_response(parser_response)
        normalized_resume, corrections = normalize_imported_resume(validated.get("resume_data"))
        if corrections:
            logger.warning("Import normalization corrections applied: %s", corrections)
    except ParserClientError as exc:
        logger.error("Parser API failure during import: %s | details=%s", exc, exc.details)
        return (
            jsonify(
                {
                    "error": str(exc),
                    "code": exc.code,
                    "details": exc.details,
                }
            ),
            exc.status_code,
        )
    except ValueError as exc:
        logger.error("Invalid parser response: %s", exc)
        return jsonify({"error": "Parser returned invalid data.", "code": "invalid_parser_response"}), 502
    except Exception:
        logger.exception("Unexpected failure while importing resume.")
        return jsonify({"error": "Failed to import resume.", "code": "import_failed"}), 500

    try:
        local_resume_id = _next_local_resume_id(user_id)
        resume_data = {k: v for k, v in normalized_resume.items() if k != "template"}

        meta = dict(resume_data.get(META_KEY)) if isinstance(resume_data.get(META_KEY), dict) else {}
        meta[LOCAL_ID_KEY] = local_resume_id
        meta["source_type"] = "imported"
        if corrections:
            meta["normalization_corrections"] = corrections
        resume_data[META_KEY] = meta

        import_meta = _build_import_meta_for_db(validated, upload_payload["filename"])

        resume = Resume(
            user_id=user_id,
            resume_data=resume_data,
            template=normalized_resume.get("template", "classic"),
            source_type=import_meta["source_type"],
            parser_confidence=import_meta["parser_confidence"],
            original_resume_file=import_meta["original_resume_file"],
            parser_generated_at=import_meta["parser_generated_at"],
            parser_mapping_version=import_meta["parser_mapping_version"],
        )
        db.session.add(resume)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to create imported resume draft.")
        return jsonify({"error": "Could not save imported resume draft.", "code": "draft_creation_failed"}), 500

    logger.info(
        "Imported resume created for user_id=%s local_resume_id=%s confidence=%s",
        user_id,
        local_resume_id,
        import_meta.get("parser_confidence"),
    )

    return (
        jsonify(
            {
                "message": "Resume imported successfully.",
                "resume_id": local_resume_id,
                "template": normalized_resume.get("template", "classic"),
                "parser_confidence": import_meta.get("parser_confidence"),
                "normalization_corrections": corrections,
            }
        ),
        201,
    )
@app.route("/api/resumes", methods=["GET"])
@jwt_required()
def get_all_resumes():
    user_id = int(get_jwt_identity())

    resumes = _ensure_local_ids_for_user(user_id)
    resumes.sort(key=lambda r: _extract_local_resume_id(r) or 0)

    result = []
    for r in resumes:
        data= r.resume_data

        html = render_html(r.template, data)

        result.append({
            "id": _extract_local_resume_id(r),
            "template": r.template,
            "source_type": r.source_type,
            "parser_confidence": r.parser_confidence,
            "created_at": r.created_at,
            "resume_html": html
        })

    return jsonify(result), 200

@app.route("/api/resume/<int:resume_id>", methods=["GET"])
@jwt_required()
def get_resume(resume_id):
    user_id = int(get_jwt_identity())

    resume = _get_resume_for_user(user_id, resume_id)

    if not resume:
        return jsonify({"error": "Not found"}), 404

    data = {**resume.resume_data, "template": resume.template}
    response_data = {k: v for k, v in data.items() if k != META_KEY}
    analytics = analyze_resume(resume.resume_data)
    html = render_html(resume.template, response_data)

    return jsonify({
        **response_data,
        "resume_html": html,
        "analytics": analytics,
        "source_type": resume.source_type,
        "parser_confidence": resume.parser_confidence,
        "original_resume_file": resume.original_resume_file,
        "parser_generated_at": resume.parser_generated_at,
        "parser_mapping_version": resume.parser_mapping_version,
    }), 200

@app.route("/api/resume/<int:resume_id>", methods=["PUT"])
@jwt_required()
def update_resume(resume_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()

    resume = _get_resume_for_user(user_id, resume_id)

    if not resume:
        return jsonify({"error": "Not found"}), 404

    template_name = data.get("template", "classic")

    updated_resume_data = {k: v for k, v in data.items() if k != "template"}
    updated_meta = dict(updated_resume_data.get(META_KEY)) if isinstance(updated_resume_data.get(META_KEY), dict) else {}
    updated_meta[LOCAL_ID_KEY] = _extract_local_resume_id(resume)
    updated_resume_data[META_KEY] = updated_meta

    resume.resume_data = updated_resume_data
    resume.template = template_name

    analytics = analyze_resume(resume.resume_data)

    html = render_html(template_name, data)

    db.session.commit()

    return jsonify({"resume_html": html,
                    "id": _extract_local_resume_id(resume),
                    "analytics": analytics,
                    'template': resume.template,
                    "resume_data": resume.resume_data}), 200

@app.route("/api/resume/<int:resume_id>", methods=["DELETE"])
@jwt_required()
def delete_resume(resume_id):
    user_id = int(get_jwt_identity())

    resume = _get_resume_for_user(user_id, resume_id)

    if not resume:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(resume)
    db.session.commit()

    return jsonify({"message": "Deleted"}), 200


@app.route("/api/resume/<int:resume_id>/download", methods=["GET"])
@jwt_required()
def download_resume(resume_id):

    user_id = int(get_jwt_identity())

    resume = _get_resume_for_user(user_id, resume_id)

    if not resume:
        return jsonify({"error": "Not found"}), 404

    data = {**resume.resume_data, "template": resume.template}
    html = render_html(resume.template, data)

    return send_file(
        BytesIO(render_pdf_bytes(html)),
        as_attachment=True,
        download_name="resume.pdf",
        mimetype="application/pdf"
    )


@app.route("/api/job-match", methods=["POST"])
def job_match():
    model = get_model() 
    data = request.get_json()

    resume_json = data.get("resume", {})
    jd_text = data.get("job_description", "")

    if not resume_json or not jd_text:
        return jsonify({
            "error": "Could not extract meaningful content from one or both inputs."
        })

    result = semantic_match(resume_json, jd_text)

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
