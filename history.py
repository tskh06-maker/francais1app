import json
import os
from datetime import datetime, timezone

HISTORY_PATH = "history.json"


def load_history(path=HISTORY_PATH):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_history(history, path=HISTORY_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def record_result(history, verb, tense, correct):
    tense_entry = history.setdefault(verb, {}).setdefault(
        tense, {"attempts": 0, "wrong_count": 0, "last_result": None, "last_attempted": None}
    )
    tense_entry["attempts"] += 1
    if not correct:
        tense_entry["wrong_count"] += 1
    tense_entry["last_result"] = "correct" if correct else "wrong"
    tense_entry["last_attempted"] = datetime.now(timezone.utc).isoformat()


def get_review_verbs(history, tense, verbs_in_order):
    flagged = {
        verb
        for verb, tenses in history.items()
        if tense in tenses and tenses[tense]["last_result"] == "wrong"
    }
    return [v for v in verbs_in_order if v in flagged]


def get_stats(history):
    total_attempts = 0
    total_wrong = 0
    review_count = 0
    for tenses in history.values():
        for entry in tenses.values():
            total_attempts += entry["attempts"]
            total_wrong += entry["wrong_count"]
            if entry["last_result"] == "wrong":
                review_count += 1
    return {
        "total_attempts": total_attempts,
        "total_wrong": total_wrong,
        "review_count": review_count,
    }
