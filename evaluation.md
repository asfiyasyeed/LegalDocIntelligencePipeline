# Evaluation

## Approach

Since this is a small system with synthetic sample documents, the evaluation is manual and evidence-based rather than automated. For each dimension, specific examples from the actual run output are used.

---

## 1. Grounding Score

For each generated draft, every factual claim was checked against the source document to see if it could be traced back to the text.

**case1 (financial dispute):**

| Claim in draft | Present in source? |
|---|---|
| Case number CIV-2023-00451 | Yes |
| Plaintiff: Rajan Mehta | Yes |
| Defendant: Apex Financial Solutions Pvt. Ltd. | Yes |
| Loan amount Rs. 12,00,000 at 14% per annum | Yes |
| Unauthorized fees of Rs. 45,000 on February 1, 2022 | Yes |
| Statement requests on April 10 and June 3, 2022 | Yes |
| CIBIL report on August 15, 2022 | Yes |
| Relief: Rs. 2,00,000 damages | Yes |

**Grounding score: 8/8 claims traceable to source. 100%**

**case2 (noisy environmental case):**

| Claim in draft | Present in source? |
|---|---|
| Case number ENV-2022-00789 | Yes (extracted despite noise) |
| Parties: Gr33n Earth Foundation vs Ind0 Chem | Yes (noise preserved correctly) |
| Chemical waste discharge since April 2021 | Yes |
| Violation of Environment Protection Act 1986 | Yes |
| Clause 3.1 of factory operating license | Yes |
| Relief: closure of Plant No.3 and Rs. 50,00,000 fine | Yes |

**Grounding score: 6/6 claims traceable. 100%**

Notable: the draft correctly preserved the noisy party names (Gr33n, Ind0) rather than silently correcting them, which is the right behaviour — the system should not silently alter source content.

---

## 2. Extraction Accuracy

**Clean documents (case1, case3):**
- Case numbers extracted correctly in both
- All parties identified correctly
- Dates extracted: 6 from case1, 2 from case3
- Confidence score: 1.0 for both (all pages used native extraction, no OCR needed)

**Noisy document (case2_noisy.txt):**
- Case number extracted correctly from the noisy text
- Parties extracted despite character substitutions
- Dates extracted: 0 (expected failure — the digit substitutions broke the date regex patterns)
- Confidence: 0.0 (txt file, no native PDF extraction path)

The date extraction failure on case2 is a known limitation of regex-based extraction on noisy text. The LLM compensated for this in the draft — it correctly identified "July 2, 2022" as the filing date even though the structured extractor missed it, because the LLM is more tolerant of character noise than regex patterns are.

---

## 3. Retrieval Relevance

Four queries were run per document. Because the sample documents are short (single-page), each produced one chunk that contained the entire document. This means retrieval was trivially correct — the top chunk was always the right one.

On longer real documents with multiple pages, the value of the retrieval layer becomes more significant. The architecture is designed to scale to that case — the chunking and FAISS search operate identically regardless of document length, they just have more candidates to rank.

---

## 4. Edit Improvement Loop

A simulated operator edit was applied to case1's draft. The original draft had:
- Abbreviated party name ("Apex Financial" instead of "Apex Financial Solutions Pvt. Ltd.")
- Missing filing date in the key dates section
- Minimal address information for the plaintiff

The operator's edited version added the full legal name, the filing date, and more complete party details.

The system extracted 3 patterns from this edit and saved them to `learned_patterns.json`. On the next pipeline run, those patterns were loaded and appended to the prompt — visible in the terminal output: "Applying 3 learned patterns from past edits."

The resulting drafts for all three documents reflected the learned preferences: full legal names were used, filing dates were included where present, and party details were more complete.

---

## Summary

| Dimension | Result |
|---|---|
| Grounding (case1) | 8/8 claims supported by source |
| Grounding (case2) | 6/6 claims supported by source |
| Clean document extraction | Accurate on case numbers, parties, dates |
| Noisy document extraction | LLM handles noise well; regex date extraction fails as expected |
| Edit learning | 3 patterns extracted, applied on next run, output visibly improved |