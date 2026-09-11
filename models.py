"""
Phase 10: Database Models
FYP II - Bug Severity Classification System

Defines two tables:
- users: one login account per QA staff member
- bug_reports: every bug ever submitted, with its prediction,
  Claude's recommendation, and its current status

Uses SQLAlchemy, so the exact same code works with MySQL
(what you'll actually run, through XAMPP) or SQLite (used only
for local testing during development).
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    role = db.Column(db.String(30), default="QA Engineer")
    profession = db.Column(db.String(50), nullable=True)
    theme = db.Column(db.String(10), default="system")  # light, dark, system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship("BugReport", backref="reporter", lazy=True)


class BugReport(db.Model):
    __tablename__ = "bug_reports"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    product = db.Column(db.String(100))
    environment = db.Column(db.String(100))
    steps_to_reproduce = db.Column(db.Text)

    severity = db.Column(db.String(20), nullable=False)
    recommendation = db.Column(db.Text)
    status = db.Column(db.String(20), default="Open")
    screenshot_path = db.Column(db.String(300), nullable=True)

    reported_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
