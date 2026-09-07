"""
Phase 5: XGBoost Model
FYP II - Bug Severity Classification System

This script does:
1. Split the dataset into training and testing sets.
2. Train an XGBoost classifier on the TF-IDF features.
3. Test the model on unseen data.
4. Evaluate performance with accuracy, precision, recall, F1, confusion matrix.
5. Uses class weighting to handle the Medium class dominating the data.

Run this from your dataset folder, with venv active:
    python train_model.py

Input:  tfidf_features.pkl   (from Phase 4)
Output: severity_model.pkl   (trained model + label encoder)
        confusion_matrix.png (visual evaluation result, for your report)
"""

import joblib
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Save plots to file, don't try to open a window
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

# ---------------------------------------------------------
# Step 1: Load TF-IDF features from Phase 4
# ---------------------------------------------------------
print("Loading tfidf_features.pkl...")
data = joblib.load("tfidf_features.pkl")
X = data["X"]
y_raw = data["y"]

# ---------------------------------------------------------
# Step 2: Encode labels
# ---------------------------------------------------------
# XGBoost needs numeric labels, not text.
# Critical/Medium/Low become 0/1/2 (order assigned alphabetically
# by LabelEncoder, we print the mapping below so it's on record).
label_encoder = LabelEncoder()
y = label_encoder.fit_transform(y_raw)
print("Label mapping:", dict(zip(label_encoder.classes_, range(len(label_encoder.classes_)))))

# ---------------------------------------------------------
# Step 3: Split the dataset
# ---------------------------------------------------------
# 80% training, 20% testing.
# stratify=y keeps the same class proportions in both splits,
# important here since Medium dominates the data.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Training rows: {X_train.shape[0]}")
print(f"Testing rows:  {X_test.shape[0]}")

# ---------------------------------------------------------
# Step 4: Compute sample weights to handle class imbalance
# ---------------------------------------------------------
# Medium is about 89% of the data. Without this, XGBoost would
# just learn to predict Medium most of the time and still score
# a high accuracy, without actually being useful.
# "balanced" gives rare classes (Critical, Low) more weight
# during training.
sample_weights = compute_sample_weight(class_weight="balanced", y=y_train)

# ---------------------------------------------------------
# Step 5: Train XGBoost
# ---------------------------------------------------------
print("Training XGBoost...")
model = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    objective="multi:softmax",
    num_class=len(label_encoder.classes_),
    eval_metric="mlogloss",
    random_state=42,
)
model.fit(X_train, y_train, sample_weight=sample_weights)
print("Training done.")

# ---------------------------------------------------------
# Step 6: Test the model
# ---------------------------------------------------------
y_pred = model.predict(X_test)

# ---------------------------------------------------------
# Step 7: Evaluate the model
# ---------------------------------------------------------
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average="macro")
recall = recall_score(y_test, y_pred, average="macro")
f1 = f1_score(y_test, y_pred, average="macro")

print("\n=== Evaluation ===")
print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}  (macro average)")
print(f"Recall:    {recall:.4f}  (macro average)")
print(f"F1-score:  {f1:.4f}  (macro average)")

print("\nFull classification report:")
print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

# ---------------------------------------------------------
# Step 8: Confusion matrix
# ---------------------------------------------------------
cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=label_encoder.classes_)
disp.plot(cmap="Blues", values_format="d")
plt.title("Confusion Matrix - Bug Severity Classification")
plt.tight_layout()
plt.savefig("confusion_matrix.png")
print("\nSaved confusion_matrix.png")

# ---------------------------------------------------------
# Step 9: Save the trained model
# ---------------------------------------------------------
joblib.dump(
    {"model": model, "label_encoder": label_encoder},
    "severity_model.pkl"
)
print("Saved severity_model.pkl")
