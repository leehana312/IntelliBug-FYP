"""
Phase 4: NLP Pipeline
FYP II - Bug Severity Classification System

This script does two things:
1. Text preprocessing: cleans, tokenizes, and removes stopwords
   from the bug title (short_desc).
2. Feature extraction: converts the cleaned text into TF-IDF
   numerical features, ready for XGBoost in Phase 5.

Run this from your dataset folder, with venv active:
    python nlp_pipeline.py

Input:  cleaned_dataset.csv   (from Phase 3)
Output: tfidf_features.pkl    (TF-IDF matrix + vectorizer + labels)
        preprocessed_dataset.csv  (readable version, for your report)
"""

import pandas as pd
import nltk
import joblib
import re

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer

# ---------------------------------------------------------
# Step 0: Download NLTK data (only runs once, then cached)
# ---------------------------------------------------------
print("Checking NLTK resources...")
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

stop_words = set(stopwords.words("english"))

# ---------------------------------------------------------
# Step 1: Load cleaned dataset from Phase 3
# ---------------------------------------------------------
print("Loading cleaned_dataset.csv...")
df = pd.read_csv("cleaned_dataset.csv")
print(f"Loaded {len(df)} rows.")

# ---------------------------------------------------------
# Step 2: Text cleaning
# ---------------------------------------------------------
# Remove anything that isn't a letter or space.
# Numbers, bug IDs in brackets, and symbols add noise, not signal,
# for a text classification task like this.
def clean_text(text):
    text = str(text).lower()
    # Remove bracketed content first, e.g. "(1G8G6RR)".
    # These are internal reference codes, not real words, and
    # leaving them in adds junk tokens like "g" or "rr" after
    # the digits get stripped out below.
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

df["clean_text"] = df["short_desc"].apply(clean_text)

# ---------------------------------------------------------
# Step 3: Tokenization
# ---------------------------------------------------------
# Splits each bug title into a list of individual words.
# Example: "login page crashes" -> ["login", "page", "crashes"]
df["tokens"] = df["clean_text"].apply(word_tokenize)

# ---------------------------------------------------------
# Step 4: Stopword removal
# ---------------------------------------------------------
# Removes common filler words that carry no severity signal,
# like "the", "is", "at", "on".
def remove_stopwords(tokens):
    return [word for word in tokens if word not in stop_words]

df["tokens"] = df["tokens"].apply(remove_stopwords)

# Rebuild cleaned text from tokens, this is what TF-IDF actually reads.
df["final_text"] = df["tokens"].apply(lambda tokens: " ".join(tokens))

# ---------------------------------------------------------
# Step 5: Drop rows that became empty after cleaning
# ---------------------------------------------------------
# Some titles are just numbers or symbols, e.g. "(1G8G6RR)".
# After cleaning, nothing useful is left, so drop those rows.
before = len(df)
df = df[df["final_text"].str.strip() != ""]
print(f"Dropped {before - len(df)} rows that became empty after cleaning.")

# ---------------------------------------------------------
# Step 6: TF-IDF feature extraction
# ---------------------------------------------------------
# Converts each bug title into a numerical vector.
# max_features caps vocabulary size, keeps the model manageable.
print("Running TF-IDF...")
vectorizer = TfidfVectorizer(max_features=5000)
X = vectorizer.fit_transform(df["final_text"])
y = df["severity_level"]

print(f"TF-IDF matrix shape: {X.shape}")
print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")

# ---------------------------------------------------------
# Step 7: Save everything for Phase 5
# ---------------------------------------------------------
joblib.dump(
    {"X": X, "y": y, "vectorizer": vectorizer},
    "tfidf_features.pkl"
)
print("Saved tfidf_features.pkl")

# Also save a readable CSV, useful for screenshots in your report.
df[["bug_id", "short_desc", "final_text", "severity_level"]].to_csv(
    "preprocessed_dataset.csv", index=False
)
print("Saved preprocessed_dataset.csv")

# ---------------------------------------------------------
# Step 8: Show a few examples
# ---------------------------------------------------------
print("\nSample before and after:")
print(df[["short_desc", "final_text"]].head(5).to_string(index=False))
