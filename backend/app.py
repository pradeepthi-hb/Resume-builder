from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from extensions import db, jwt
from routes.auth import auth_bp
from routes.ai import ai_bp
from routes.integration import integration_bp
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.resume import Resume
from flask import send_file
from io import BytesIO
from routes.occupation_routes import occupation_bp
from analytics import analyze_resume, extract_text
from job_match import semantic_match, get_model
from transformers import logging
from services.resume_rendering import render_html, render_pdf_bytes

logging.set_verbosity_error()  # suppress warnings/info logs

app = Flask(__name__)
app.config.from_object(Config)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/resume_builder?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

CORS(app,
    resources={r"/api/*": {"origins": "http://localhost:3000"}},supports_credentials=True)
db.init_app(app)
jwt.init_app(app)

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

    resume = Resume(
        user_id=user_id,
        resume_data=resume_data,
        template=template_name
    )

    db.session.add(resume)          
    db.session.commit()

    analytics = analyze_resume(resume_data)
    html = render_html(template_name, resume.resume_data)

    return jsonify({
        "message": "Resume created",
        "resume_id": resume.id,
        "resume_html": html,
        "analytics": analytics
    }), 201

@app.route("/api/resumes", methods=["GET"])
@jwt_required()
def get_all_resumes():
    user_id = int(get_jwt_identity())

    resumes = Resume.query.filter_by(user_id=user_id).all()

    result = []
    for r in resumes:
        data= r.resume_data

        html = render_html(r.template, data)

        result.append({
            "id": r.id,
            "template": r.template,
            "created_at": r.created_at,
            "resume_html": html
        })

    return jsonify(result), 200

@app.route("/api/resume/<int:resume_id>", methods=["GET"])
@jwt_required()
def get_resume(resume_id):
    user_id = int(get_jwt_identity())

    resume = Resume.query.filter_by(
        id=resume_id,
        user_id=user_id
    ).first()

    if not resume:
        return jsonify({"error": "Not found"}), 404

    data = {**resume.resume_data, "template": resume.template}
    analytics = analyze_resume(resume.resume_data)
    html = render_html(resume.template, data)

    return jsonify({**data, "resume_html": html, "analytics": analytics}), 200

@app.route("/api/resume/<int:resume_id>", methods=["PUT"])
@jwt_required()
def update_resume(resume_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()

    resume = Resume.query.filter_by(
        id=resume_id,
        user_id=user_id
    ).first()

    if not resume:
        return jsonify({"error": "Not found"}), 404

    template_name = data.get("template", "classic")

    resume.resume_data = {k: v for k, v in data.items() if k != "template"}
    resume.template = template_name

    analytics = analyze_resume(resume.resume_data)

    html = render_html(template_name, data)

    db.session.commit()

    return jsonify({"resume_html": html,
                    "id":resume.id,
                    "analytics": analytics,
                    'template': resume.template}), 200

@app.route("/api/resume/<int:resume_id>", methods=["DELETE"])
@jwt_required()
def delete_resume(resume_id):
    user_id = int(get_jwt_identity())

    resume = Resume.query.filter_by(
        id=resume_id,
        user_id=user_id
    ).first()

    if not resume:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(resume)
    db.session.commit()

    return jsonify({"message": "Deleted"}), 200


@app.route("/api/resume/<int:resume_id>/download", methods=["GET"])
@jwt_required()
def download_resume(resume_id):

    user_id = int(get_jwt_identity())

    resume = Resume.query.filter_by(
        id=resume_id,
        user_id=user_id
    ).first()

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
