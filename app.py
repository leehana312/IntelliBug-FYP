"""
Phase 7: Connect XGBoost Model
FYP II - Bug Severity Classification System

This connects your trained model (severity_model.pkl) to the Flask
backend. The /classify route now runs real predictions instead of
returning placeholder text.

Phase 8 will add Claude's recommendation on top of this.

Run this from your FYP 2 root folder, with venv active:
    python app.py

Then open your browser to:
    http://127.0.0.1:5000
"""

import re
import joblib
from flask import Flask, render_template, request, jsonify
from xgboost import XGBClassifier

app = Flask(__name__)

# ---------------------------------------------------------
# Load the trained model once, when the server starts.
# The XGBoost model loads from its own native file format,
# xgb_model.json, while the label encoder and vectorizer load
# from the joblib bundle. Splitting them this way avoids a
# corrupted-buffer error XGBoost's pickle format hit on
# Windows during file transfer.
# ---------------------------------------------------------
print("Loading model...")
model = XGBClassifier()
model.load_model("dataset/xgb_model.json")

bundle = joblib.load("dataset/severity_model.pkl")
label_encoder = bundle["label_encoder"]
vectorizer = bundle["vectorizer"]
print("Model loaded. Ready.")


def clean_text(text):
    """
    Same cleaning steps as Phase 4's nlp_pipeline.py.
    The model was trained on text cleaned this exact way, so a new
    bug report needs the same treatment before prediction, otherwise
    the TF-IDF vectorizer sees different-looking input than it
    learned from.
    """
    text = str(text).lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@app.route("/")
def index():
    """Show the bug submission form."""
    return render_template("index.html")


@app.route("/classify", methods=["POST"])
def classify():
    """
    Receives a bug title and description, runs the real XGBoost
    model, returns the predicted severity.
    """
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not description:
        return jsonify({"error": "Please fill in both the title and description."}), 400

    # Combine title and description, same as how short_desc was
    # used during training. Title carries most of the signal, but
    # combining both gives the model more words to work with.
    combined_text = clean_text(title + " " + description)

    # Turn the cleaned text into the same TF-IDF feature space
    # the model was trained on.
    features = vectorizer.transform([combined_text])

    prediction = model.predict(features)[0]
    severity = label_encoder.inverse_transform([prediction])[0]

    # Phase 8 replaces this line with a real Claude API call.
    recommendation = "Not yet connected to Claude API"

    result = {
        "title": title,
        "description": description,
        "severity": severity,
        "recommendation": recommendation,
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)

