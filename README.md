# Legal Document Intelligence Pipeline

A pipeline that takes messy legal documents, pulls structured information out of them, retrieves relevant evidence, and generates grounded draft summaries. It also gets better over time by learning from how an operator edits the output.

---

## What It Does

Most legal document workflows involve someone manually reading through PDFs, pulling out key facts, and writing a summary from scratch. This system automates that first pass. It handles noisy or scanned inputs, stays grounded in what the document actually says, and adjusts its behavior based on corrections a reviewer makes.

The output type is a **Case Fact Summary** — a structured breakdown of parties, dates, claims, and relief sought, with evidence sources noted.

---

## Setup

### 1. Install Tesseract OCR (required for scanned documents)

- Windows: https://github.com/UB-Mannheim/tesseract/wiki — download and install
- Mac: `brew install tesseract`
- Linux: `sudo apt install tesseract-ocr`

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

Create a `.env` file in the project root:
OPENROUTER_API_KEY=your_key_here
Get a free key at https://openrouter.ai

---

## How to Run

### Full pipeline (processes all documents in sample_inputs/)
```bash
python src/pipeline.py
```

### Individual stages
```bash
python src/processor.py      # extract text and structured fields
python src/retriever.py      # test chunk retrieval
python src/generator.py      # generate a single draft
python src/editor.py         # simulate operator edit and learn patterns
```

### Expected output
- Drafts saved to `sample_outputs/` as `.txt` files
- Edit history saved to `edit_history.json`
- Learned improvement patterns saved to `learned_patterns.json`

---

# Project Structure

```text
legal-doc-pipeline/
├── README.md
├── requirements.txt
├── architecture.md
├── assumptions_and_tradeoffs.md
├── evaluation.md
├── .env                          # API key (excluded from Git)
├── edit_history.json             # Captured operator edits
├── learned_patterns.json         # Patterns extracted from edits
├── sample_inputs/
│   ├── case1.pdf                 # Financial dispute (clean PDF)
│   ├── case2_noisy.txt           # Environmental case (simulated OCR noise)
│   └── case3.pdf                 # Employment dispute (clean PDF)
├── sample_outputs/
│   ├── case1_draft.txt
│   ├── case2_noisy_draft.txt
│   └── case3_draft.txt
├── project_artifacts/
│   ├── screenshot1.png           # Metrics and generated draft
│   ├── screenshot2.png           # Retrieved evidence chunks
│   └── screenshot3.png           # Learned patterns after editing
└── src/
    ├── processor.py              # Stage 1: Document processing
    ├── retriever.py              # Stage 2: Evidence retrieval
    ├── generator.py              # Stage 3: Draft generation
    ├── editor.py                 # Stage 4: Human-in-the-loop editing
    └── pipeline.py               # End-to-end pipeline orchestration
```
## Stack

| Tool | Purpose |
|---|---|
| PyMuPDF | Native PDF text extraction |
| pytesseract | OCR fallback for scanned pages |
| sentence-transformers | Local text embeddings |
| FAISS | Vector similarity search |
| OpenRouter / GPT-4o-mini | Draft generation |
| python-dotenv | API key management |
