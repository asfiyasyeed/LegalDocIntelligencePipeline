# Architecture Overview

## The Core Idea

The system is a linear five-stage pipeline. Each stage does one thing and passes its output to the next. Nothing is hardcoded to a specific document — you can drop any legal PDF into sample_inputs/ and it runs through the same flow.

## Pipeline Workflow

```text
Input Document (PDF or TXT)
        │
        ▼
┌─────────────────────────────┐
│ Stage 1: processor.py       │
│ • Extract raw text          │
│ • Extract structured fields │
│ • PDF parsing               │
│ • OCR fallback if needed    │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Stage 2: retriever.py       │
│ • Chunk text                │
│ • Generate embeddings       │
│ • Build FAISS index         │
│ • Retrieve top-k chunks     │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Stage 3: generator.py       │
│ • Build grounded prompt     │
│ • Call LLM                  │
│ • Return draft + evidence   │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Case Fact Summary           │
│ Saved to sample_outputs/    │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Stage 4: editor.py          │
│ • Operator reviews draft    │
│ • Capture edits/diffs       │
│ • Extract edit patterns     │
│ • Save learned patterns     │
└─────────────────────────────┘
        │
        ▼
 learned_patterns.json
        │
        ▼
Feedback Loop
        │
        └────────────► Used by Stage 3
                        on future runs
```

---

## Stage 1 — Document Processor

**File:** `src/processor.py`

Accepts a `.pdf` or `.txt` file. For PDFs, it tries native text extraction using PyMuPDF first — this works when the PDF has real embedded text. If a page comes back with fewer than 50 characters, that page is treated as a scanned image and goes through pytesseract OCR at 200 DPI instead.

After extraction, regex patterns run over the full text to pull out structured fields: case numbers (patterns like `CIV-2023-00451`), party names (lines starting with "Plaintiff:" or "Defendant:"), and dates in multiple formats.

The output is a dict with `raw_text`, per-page breakdown with which method was used, structured fields, and a confidence score between 0 and 1 based on how many pages needed OCR vs native extraction.

**From the test run:**
- case1.pdf → confidence 1.0, 6 dates found (fully native extraction)
- case2_noisy.txt → confidence 0.0, 0 dates found (expected — the noisy text has characters like `0` replacing `o` which breaks date regex, demonstrating the challenge of real OCR noise)
- case3.pdf → confidence 1.0, 2 dates found

---

## Stage 2 — Retrieval Layer

**File:** `src/retriever.py`

Takes the extracted text and builds a searchable index. The text is split into 300-word chunks with a 50-word overlap. The overlap is important — it prevents a sentence from being cut in half at a chunk boundary, which would break the evidence when retrieved.

Each chunk is embedded using `sentence-transformers` with the `all-MiniLM-L6-v2` model. This runs entirely locally, no API call needed. The embeddings go into a FAISS `IndexFlatL2` index.

At query time, the query string is embedded the same way and the index returns the nearest chunks by vector distance. Four different queries are run per document (claims, parties, dates, clauses) and the results are deduplicated by chunk ID before being passed to generation.

---

## Stage 3 — Draft Generator

**File:** `src/generator.py`

This stage constructs a prompt that contains the retrieved chunks as labelled excerpts, then calls GPT-4o-mini via OpenRouter. The prompt explicitly instructs the model to use only information present in the excerpts and to write "Not found in document" for anything it cannot find. This is the grounding mechanism — the model is not asked to reason from general knowledge.

If learned patterns exist from previous operator edits, they are appended to the prompt as a separate instructions block before the model generates.

The output includes the draft text, the prompt that produced it, token counts, and which chunk IDs were used — so the generation is fully inspectable.

---

## Stage 4 — Operator Edit Loop

**File:** `src/editor.py`

This is what separates the system from a one-shot summarizer. When an operator reviews the generated draft and makes corrections, those changes are captured.

The original and edited drafts are stored together in `edit_history.json` along with a unified diff. The diff is then analyzed: lines the operator added that were not there before are checked for patterns — did they add a date? Did they use a full legal name where the draft had an abbreviated one? Did they add a section that was missing entirely?

Each pattern is converted to a natural language instruction and saved to `learned_patterns.json`. On the next run, `pipeline.py` loads these patterns and passes them to the generator, which appends them to the prompt. The second draft is structurally different from the first because the prompt has changed.

The current run is already applying 3 learned patterns from a prior simulated edit, which is visible in the terminal output.

---

## Design Decisions

**Why FAISS instead of a hosted vector database?**
No external service dependency. The index rebuilds in under a second for documents this size, so persistence is not necessary at this scale.

**Why prompt injection for learning instead of fine-tuning?**
Fine-tuning requires hundreds of examples, compute time, and makes the model behavior opaque. Prompt injection works after a single edit, the learned patterns are human-readable in a JSON file, and they can be reviewed or deleted manually. The tradeoff is that very subtle stylistic preferences are harder to capture this way.

**Why four separate retrieval queries per document?**
A single query like "summarize this document" retrieves the most topically central chunk, which might miss dates buried in a header or relief sought mentioned only at the end. Four targeted queries ensure the evidence covers all sections of the summary format.