"""
Phase 9 & 10: QA Dashboard + Database
FYP II - Bug Severity Classification System

Full application: login-protected dashboard, bug submission,
bug reports list, bug detail view, analytics, and account settings.
Every submitted bug is saved to the database so these pages show
real data, not placeholders.

Run this from your FYP 2 root folder, with venv active:
    python app.py

Then open your browser to:
    http://127.0.0.1:5000
"""

import re
import os
from datetime import datetime, timedelta
from collections import defaultdict

import joblib
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from xgboost import XGBClassifier
from dotenv import load_dotenv
import anthropic

from models import db, User, BugReport

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-this")

# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------
# Reads from .env. For your setup with XAMPP, this points at
# your local MySQL server. Format:
#   mysql+pymysql://root:@localhost/intellibug
# (XAMPP's default MySQL user is root with no password)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///intellibug.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# ---------------------------------------------------------
# Login manager
# ---------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------
# Load the trained model once, when the server starts.
# ---------------------------------------------------------
print("Loading model...")
model = XGBClassifier()
model.load_model("dataset/xgb_model.json")

bundle = joblib.load("dataset/severity_model.pkl")
label_encoder = bundle["label_encoder"]
vectorizer = bundle["vectorizer"]
print("Model loaded. Ready.")

claude_client = anthropic.Anthropic()


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_recommendation(title, description, severity):
    prompt = f"""A bug was reported with the following details:

Title: {title}
Description: {description}
Predicted severity: {severity}

Suggest a brief, practical fix or next step for a developer to investigate this bug. Keep it to 2-3 sentences. Do not repeat the bug details back, just give the recommendation."""
    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in message.content:
            if block.type == "text":
                return block.text.strip()
        return "Claude did not return a text response."
    except Exception as e:
        print("Claude API error:", e)
        return "Recommendation unavailable right now. The severity prediction above is still valid."


# ---------------------------------------------------------
# Auth routes
# ---------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or not password:
            flash("Please fill in every field.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.")
            return redirect(url_for("register"))

        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    critical_count = BugReport.query.filter_by(severity="Critical", status="Open").count()
    medium_count = BugReport.query.filter_by(severity="Medium", status="Open").count()
    low_count = BugReport.query.filter_by(severity="Low", status="Open").count()

    recent = BugReport.query.order_by(BugReport.created_at.desc()).limit(5).all()

    latest_critical = (
        BugReport.query.filter_by(severity="Critical")
        .order_by(BugReport.created_at.desc())
        .first()
    )

    return render_template(
        "dashboard.html",
        critical_count=critical_count,
        medium_count=medium_count,
        low_count=low_count,
        recent=recent,
        latest_critical=latest_critical,
    )


# ---------------------------------------------------------
# Submit bug
# ---------------------------------------------------------
@app.route("/submit", methods=["GET"])
@login_required
def submit_bug_page():
    return render_template("submit_bug.html")


@app.route("/classify", methods=["POST"])
@login_required
def classify():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    product = request.form.get("product", "").strip()
    environment = request.form.get("environment", "").strip()
    steps = request.form.get("steps", "").strip()

    if not title or not description:
        return jsonify({"error": "Please fill in both the title and description."}), 400

    combined_text = clean_text(title + " " + description)
    features = vectorizer.transform([combined_text])
    prediction = model.predict(features)[0]
    severity = label_encoder.inverse_transform([prediction])[0]

    recommendation = get_recommendation(title, description, severity)

    report = BugReport(
        title=title,
        description=description,
        product=product,
        environment=environment,
        steps_to_reproduce=steps,
        severity=severity,
        recommendation=recommendation,
        status="Open",
        reported_by=current_user.id,
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        "id": report.id,
        "title": title,
        "severity": severity,
        "recommendation": recommendation,
    })


# ---------------------------------------------------------
# Bug reports list
# ---------------------------------------------------------
@app.route("/reports")
@login_required
def bug_reports():
    severity_filter = request.args.get("severity", "All")
    status_filter = request.args.get("status", "All")
    search = request.args.get("q", "").strip()

    query = BugReport.query

    if severity_filter != "All":
        query = query.filter_by(severity=severity_filter)
    if status_filter != "All":
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(BugReport.title.ilike(f"%{search}%"))

    reports = query.order_by(BugReport.created_at.desc()).all()

    return render_template(
        "bug_reports.html",
        reports=reports,
        severity_filter=severity_filter,
        status_filter=status_filter,
        search=search,
    )


@app.route("/reports/<int:report_id>")
@login_required
def bug_detail(report_id):
    report = db.session.get(BugReport, report_id)
    if report is None:
        flash("Bug report not found.")
        return redirect(url_for("bug_reports"))

    # Recompute which words in this bug's text carried the most
    # TF-IDF weight, real values from the actual vectorizer, not
    # decorative placeholder tags.
    combined_text = clean_text(report.title + " " + report.description)
    vec = vectorizer.transform([combined_text])
    feature_names = vectorizer.get_feature_names_out()
    row = vec.toarray()[0]
    top_indices = row.argsort()[::-1][:6]
    top_terms = [feature_names[i] for i in top_indices if row[i] > 0]

    return render_template("bug_detail.html", report=report, top_terms=top_terms)


@app.route("/reports/<int:report_id>/status", methods=["POST"])
@login_required
def update_status(report_id):
    report = db.session.get(BugReport, report_id)
    if report is None:
        return jsonify({"error": "Not found"}), 404

    new_status = request.form.get("status")
    if new_status not in ("Open", "In Progress", "Resolved"):
        return jsonify({"error": "Invalid status"}), 400

    report.status = new_status
    if new_status == "Resolved" and report.resolved_at is None:
        report.resolved_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"status": report.status})


# ---------------------------------------------------------
# Analytics
# ---------------------------------------------------------
@app.route("/analytics")
@login_required
def analytics():
    all_reports = BugReport.query.all()

    # Bug reports over time, last 8 weeks, grouped by severity
    weeks = [(datetime.utcnow() - timedelta(weeks=i)).isocalendar()[1] for i in range(7, -1, -1)]
    weekly_counts = {sev: defaultdict(int) for sev in ("Critical", "Medium", "Low")}
    for r in all_reports:
        week = r.created_at.isocalendar()[1]
        if week in weeks and r.severity in weekly_counts:
            weekly_counts[r.severity][week] += 1

    trend_labels = [f"W{w}" for w in weeks]
    trend_data = {
        sev: [weekly_counts[sev][w] for w in weeks] for sev in weekly_counts
    }

    # Open bugs by product
    product_counts = defaultdict(int)
    for r in all_reports:
        if r.status == "Open" and r.product:
            product_counts[r.product] += 1
    product_labels = list(product_counts.keys())
    product_data = list(product_counts.values())

    # Average resolution time by severity, in hours
    resolution_hours = {"Critical": [], "Medium": [], "Low": []}
    for r in all_reports:
        if r.resolved_at and r.severity in resolution_hours:
            delta = (r.resolved_at - r.created_at).total_seconds() / 3600
            resolution_hours[r.severity].append(delta)

    avg_resolution = {}
    for sev, values in resolution_hours.items():
        avg_resolution[sev] = round(sum(values) / len(values), 1) if values else None

    # Model performance, from your Phase 5 evaluation, not live data.
    model_performance = {
        "accuracy": 55.5,
        "precision": 38.9,
        "recall": 52.6,
        "f1": 36.5,
    }

    return render_template(
        "analytics.html",
        trend_labels=trend_labels,
        trend_data=trend_data,
        product_labels=product_labels,
        product_data=product_data,
        avg_resolution=avg_resolution,
        model_performance=model_performance,
    )


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", current_user.full_name).strip()
        db.session.commit()
        flash("Changes saved.")
        return redirect(url_for("settings"))

    return render_template("settings.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
