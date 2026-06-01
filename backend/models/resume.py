from extensions import db
from datetime import datetime

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref("resumes", cascade="all, delete", passive_deletes=True)
    )
    resume_data = db.Column(db.JSON, nullable=False)
    template = db.Column(db.String(50), default="classic")
    source_type = db.Column(db.String(20), nullable=False, default="manual")
    parser_confidence = db.Column(db.Float, nullable=True)
    original_resume_file = db.Column(db.String(255), nullable=True)
    parser_generated_at = db.Column(db.DateTime, nullable=True)
    parser_mapping_version = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
