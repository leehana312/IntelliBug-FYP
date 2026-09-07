"""
Phase 3: Data Preparation
FYP II - Bug Severity Classification System

This script does two things:
1. Cleans the raw Eclipse bug dataset.
2. Maps the original severity labels into three categories:
   Critical, Medium, Low.

Run this from FYP 2 folder, with venv active:
    python clean_dataset.py

Input:  eclipse_bug_records_22-07-2022.xlsx
Output: cleaned_dataset.csv
"""

import pandas as pd

# ---------------------------------------------------------
# Step 1: Load the raw dataset
# ---------------------------------------------------------
print("Loading dataset...")
df = pd.read_excel(
    "eclipse_bug_records_22-07-2022.xlsx",
    sheet_name="Bug Reports"
)
print(f"Loaded {len(df)} rows.")

# ---------------------------------------------------------
# Step 2: Keep only the columns we actually need
# ---------------------------------------------------------
# short_desc  -> the bug title, our main text field
# bug_severity -> the label we map to Critical/Medium/Low
# product, component -> extra features you can use later
df = df[["bug_id", "short_desc", "bug_severity", "product", "component"]]

# ---------------------------------------------------------
# Step 3: Drop enhancement requests
# ---------------------------------------------------------
# "enhancement" is a feature request, not a bug.
# It doesn't belong in a severity classification task.
before = len(df)
df = df[df["bug_severity"] != "enhancement"]
print(f"Dropped {before - len(df)} enhancement rows.")

# ---------------------------------------------------------
# Step 4: Drop stray/invalid severity values
# ---------------------------------------------------------
# These are leftover tags that don't belong in bug_severity,
# most likely data entry noise from the original Bugzilla export.
valid_severities = ["blocker", "critical", "major", "normal", "minor", "trivial"]
before = len(df)
df = df[df["bug_severity"].isin(valid_severities)]
print(f"Dropped {before - len(df)} rows with invalid severity values.")

# ---------------------------------------------------------
# Step 5: Drop missing values
# ---------------------------------------------------------
before = len(df)
df = df.dropna(subset=["short_desc", "bug_severity"])
print(f"Dropped {before - len(df)} rows with missing description or severity.")

# ---------------------------------------------------------
# Step 6: Drop duplicate bug reports
# ---------------------------------------------------------
before = len(df)
df = df.drop_duplicates(subset=["bug_id"])
print(f"Dropped {before - len(df)} duplicate bug_id rows.")

# ---------------------------------------------------------
# Step 7: Map severity into three project categories
# ---------------------------------------------------------
severity_map = {
    "blocker": "Critical",
    "critical": "Critical",
    "major": "Medium",
    "normal": "Medium",
    "minor": "Low",
    "trivial": "Low",
}
df["severity_level"] = df["bug_severity"].map(severity_map)

# ---------------------------------------------------------
# Step 8: Clean the text field
# ---------------------------------------------------------
# Lowercase and strip extra whitespace here.
# Tokenization and stopword removal happen in Phase 4, not here.
df["short_desc"] = df["short_desc"].astype(str).str.strip().str.lower()

# ---------------------------------------------------------
# Step 9: Final check and save
# ---------------------------------------------------------
print("\nFinal row count:", len(df))
print("\nSeverity level distribution:")
print(df["severity_level"].value_counts())

df.to_csv("cleaned_dataset.csv", index=False)
print("\nSaved cleaned_dataset.csv")
