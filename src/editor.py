import json
import os
import difflib
from datetime import datetime


EDIT_HISTORY_FILE = "edit_history.json"
PATTERNS_FILE = "learned_patterns.json"


def load_edit_history():
    if os.path.exists(EDIT_HISTORY_FILE):
        with open(EDIT_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_edit_history(history):
    with open(EDIT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def load_learned_patterns():
    if os.path.exists(PATTERNS_FILE):
        with open(PATTERNS_FILE, "r") as f:
            return json.load(f)
    return []


def save_learned_patterns(patterns):
    with open(PATTERNS_FILE, "w") as f:
        json.dump(patterns, f, indent=2)


def capture_edit(doc_id, original_draft, edited_draft):
    """
    Save the original and edited draft together.
    Compute what changed using difflib.
    """
    diff = list(difflib.unified_diff(
        original_draft.splitlines(),
        edited_draft.splitlines(),
        lineterm=""
    ))

    edit_record = {
        "doc_id": doc_id,
        "timestamp": datetime.now().isoformat(),
        "original_draft": original_draft,
        "edited_draft": edited_draft,
        "diff": diff,
        "lines_changed": len([l for l in diff if l.startswith("+") or l.startswith("-")]),
    }

    history = load_edit_history()
    history.append(edit_record)
    save_edit_history(history)

    print(f"  Edit captured. Lines changed: {edit_record['lines_changed']}")
    return edit_record


def extract_patterns_from_edit(edit_record):
    """
    Look at what the operator changed and figure out a reusable rule.
    This is the learning step.
    """
    diff = edit_record["diff"]
    new_patterns = []

    added_lines = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---")]

    # Pattern 1: operator added something that was missing
    for line in added_lines:
        if "Not found" not in line and len(line) > 10:
            if any(keyword in line.lower() for keyword in ["date", "filed", "filing"]):
                pattern = "Always extract and include filing dates, even if they appear in case headers"
                if pattern not in new_patterns:
                    new_patterns.append(pattern)

            if any(keyword in line.lower() for keyword in ["plaintiff", "defendant", "petitioner"]):
                pattern = "Always use full legal names for all parties, including company suffixes like Pvt. Ltd."
                if pattern not in new_patterns:
                    new_patterns.append(pattern)

    # Pattern 2: operator removed "Not found" and replaced with actual content
    for removed, added in zip(removed_lines, added_lines):
        if "Not found" in removed and len(added) > 5:
            pattern = f"Look more carefully for: {added[:60]}..."
            new_patterns.append(pattern)

    # Pattern 3: structural changes
    original_sections = set(l for l in edit_record["original_draft"].splitlines() if l.isupper())
    edited_sections = set(l for l in edit_record["edited_draft"].splitlines() if l.isupper())
    added_sections = edited_sections - original_sections

    for section in added_sections:
        pattern = f"Always include a '{section}' section in the output"
        new_patterns.append(pattern)

    return new_patterns


def update_learned_patterns(new_patterns):
    """
    Add newly extracted patterns to the master list.
    Avoid duplicates.
    """
    existing = load_learned_patterns()
    added = 0
    for p in new_patterns:
        if p not in existing:
            existing.append(p)
            added += 1
    save_learned_patterns(existing)
    print(f"  Added {added} new patterns. Total patterns: {len(existing)}")
    return existing


def process_operator_edit(doc_id, original_draft, edited_draft):
    """
    Full pipeline: capture edit → extract patterns → update learned patterns.
    Call this whenever an operator submits their edited version.
    """
    print(f"\nProcessing operator edit for: {doc_id}")
    
    edit_record = capture_edit(doc_id, original_draft, edited_draft)
    new_patterns = extract_patterns_from_edit(edit_record)
    all_patterns = update_learned_patterns(new_patterns)

    print(f"  Patterns learned this edit: {new_patterns}")
    return all_patterns


# Simulate an operator edit for testing
if __name__ == "__main__":
    original = """CASE FACT SUMMARY
=================
CASE NUMBER: CIV-2023-00451

PARTIES INVOLVED:
- Plaintiff: Rajan Mehta
- Defendant: Apex Financial

KEY DATES:
- Not found in document

CORE FACTS:
- Loan agreement was signed
- Fees were charged
"""

    # Operator improved this draft:
    edited = """CASE FACT SUMMARY
=================
CASE NUMBER: CIV-2023-00451
FILING DATE: March 14, 2023

PARTIES INVOLVED:
- Plaintiff: Rajan Mehta, 42 MG Road, Bengaluru
- Defendant: Apex Financial Solutions Pvt. Ltd.

KEY DATES:
- January 5, 2022: Loan agreement signed
- February 1, 2022: Unauthorized fees charged
- August 15, 2022: Incorrect CIBIL report filed

CORE FACTS:
- Loan agreement signed January 5, 2022 for Rs. 12,00,000 at 14% per annum
- Unauthorized processing fees of Rs. 45,000 charged
- Defendant failed to provide statements despite written requests
"""

    patterns = process_operator_edit("case1", original, edited)
    print("\nAll learned patterns:", patterns)