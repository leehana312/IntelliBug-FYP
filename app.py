import re
import os
import joblib
from flask import Flask, render_template, request, jsonify
from xgboost import XGBClassifier
from dotenv import load_dotenv
import anthropic

load_dotenv()

app = Flask(__name__)

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

# ---------------------------------------------------------
# Set up the Claude client once, reused across requests.
# Reads ANTHROPIC_API_KEY from your .env file automatically.
# ---------------------------------------------------------
claude_client = anthropic.Anthropic()


def clean_text(text):
    """Same cleaning steps as Phase 4's nlp_pipeline.py."""
    text = str(text).lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_recommendation(title, description, severity):
    """
    Sends the bug details to Claude, asks for a short, practical
    suggested fix. Kept intentionally brief, two to three sentences,
    since this is a suggestion for a developer to act on, not a
    full essay.

    If the API call fails for any reason, missing key, network
    issue, rate limit, the app still returns a severity result
    instead of crashing the whole request. The user just sees a
    clear message instead of a recommendation.
    """
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
        # Printed to your terminal for debugging, not shown raw to the user.
        print("Claude API error:", e)
        return "Recommendation unavailable right now. The severity prediction above is still valid."


@app.route("/")
def index():
    """Show the bug submission form."""
    return render_template("index.html")


@app.route("/classify", methods=["POST"])
def classify():
    """
    Receives a bug title and description, runs the XGBoost model
    for severity, then asks Claude for a recommended fix.
    """
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not description:
        return jsonify({"error": "Please fill in both the title and description."}), 400

    combined_text = clean_text(title + " " + description)
    features = vectorizer.transform([combined_text])
    prediction = model.predict(features)[0]
    severity = label_encoder.inverse_transform([prediction])[0]

    recommendation = get_recommendation(title, description, severity)

    result = {
        "title": title,
        "description": description,
        "severity": severity,
        "recommendation": recommendation,
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)


