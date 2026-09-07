"""
Phase 6: Flask Backend
FYP II - Bug Severity Classification System

This is your web application's backend.
For now, it handles:
- Serving the bug submission page
- Receiving a bug title and description from the form

Phase 7 will connect this to your trained XGBoost model.
Phase 8 will connect this to Claude for recommendations.

Run this from your dataset folder, with venv active:
    python app.py

Then open your browser to:
    http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    """Show the bug submission form."""
    return render_template("index.html")


@app.route("/classify", methods=["POST"])
def classify():
    """
    Receives a bug title and description from the form.

    Right now this just echoes the input back, so you can confirm
    your form and backend are talking to each other correctly.
    Phase 7 replaces the placeholder result below with a real
    XGBoost prediction.
    """
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not description:
        return jsonify({"error": "Please fill in both the title and description."}), 400

    # Placeholder result, Phase 7 replaces this with the real model.
    result = {
        "title": title,
        "description": description,
        "severity": "Not yet connected to model",
        "recommendation": "Not yet connected to Claude API",
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
