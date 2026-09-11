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
import uuid
from datetime import datetime, timedelta
from collections import defaultdict

import joblib
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from xgboost import XGBClassifier
from dotenv import load_dotenv
import anthropic

from models import db, User, BugReport

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-this")

# ---------------------------------------------------------
# Upload folders, for profile pictures and bug screenshots.
# Both live under static/ so Flask can serve them directly
# at /static/uploads/... without a separate route.
# ---------------------------------------------------------
AVATAR_UPLOAD_DIR = os.path.join(app.static_folder, "uploads", "avatars")
SCREENSHOT_UPLOAD_DIR = os.path.join(app.static_folder, "uploads", "screenshots")
os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(file_storage, upload_dir):
    """
    Saves an uploaded image with a random filename, so two people
    uploading a file called screenshot.png don't overwrite each
    other. Returns the relative static path to store in the
    database, or None if there was no valid file.
    """
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_image(file_storage.filename):
        return None

    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(upload_dir, new_filename))
    folder_name = os.path.basename(upload_dir)
    return f"uploads/{folder_name}/{new_filename}"

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
# Google OAuth setup
# ---------------------------------------------------------
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


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
@app.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login/google")
def login_google():
    redirect_uri = url_for("auth_google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def auth_google_callback():
    token = google.authorize_access_token()
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        flash("Google sign-in failed. Please try again.", "error")
        return redirect(url_for("login"))

    google_id = user_info["sub"]
    email = user_info["email"].lower()
    full_name = user_info.get("name", email.split("@")[0])
    avatar_url = user_info.get("picture")

    # Find by Google ID first, then by email as a fallback, in case
    # this account was created before Google sign-in was added.
    user = User.query.filter_by(google_id=google_id).first()
    if user is None:
        user = User.query.filter_by(email=email).first()

    if user is None:
        user = User(
            full_name=full_name,
            email=email,
            google_id=google_id,
            avatar_url=avatar_url,
        )
        db.session.add(user)
    else:
        user.google_id = google_id
        user.avatar_url = avatar_url

    db.session.commit()
    login_user(user)
    return redirect(url_for("dashboard"))


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
    total_open = critical_count + medium_count + low_count

    recent = BugReport.query.order_by(BugReport.created_at.desc()).limit(5).all()

    recent_screenshots = (
        BugReport.query.filter(BugReport.screenshot_path.isnot(None))
        .order_by(BugReport.created_at.desc())
        .limit(4)
        .all()
    )

    latest_critical = (
        BugReport.query.filter_by(severity="Critical")
        .order_by(BugReport.created_at.desc())
        .first()
    )

    def pct(count):
        return round((count / total_open) * 100) if total_open else 0

    return render_template(
        "dashboard.html",
        critical_count=critical_count,
        medium_count=medium_count,
        low_count=low_count,
        critical_pct=pct(critical_count),
        medium_pct=pct(medium_count),
        low_pct=pct(low_count),
        recent=recent,
        recent_screenshots=recent_screenshots,
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

    if not title or not description:
        return jsonify({"error": "Please fill in both the title and description."}), 400

    screenshot = request.files.get("screenshot")
    screenshot_path = save_uploaded_image(screenshot, SCREENSHOT_UPLOAD_DIR)

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
        screenshot_path=screenshot_path,
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
        flash("Bug report not found.", "error")
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
        current_user.profession = request.form.get("profession", current_user.profession)
        current_user.role = request.form.get("role", current_user.role).strip()
        current_user.theme = request.form.get("theme", current_user.theme)

        photo = request.files.get("profile_picture")
        saved_path = save_uploaded_image(photo, AVATAR_UPLOAD_DIR)
        if saved_path:
            current_user.avatar_url = url_for("static", filename=saved_path)

        db.session.commit()
        flash("Changes saved.", "success")
        return redirect(url_for("settings"))

    return render_template("settings.html")


@app.route("/theme", methods=["POST"])
@login_required
def set_theme():
    """
    Quick theme toggle from the topbar, separate from the full
    Settings form, so switching light/dark doesn't need a page
    reload through the whole settings save flow.
    """
    theme = request.form.get("theme")
    if theme not in ("light", "dark", "system"):
        return jsonify({"error": "Invalid theme"}), 400
    current_user.theme = theme
    db.session.commit()
    return jsonify({"theme": theme})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
