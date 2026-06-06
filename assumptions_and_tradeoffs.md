# Assumptions and Tradeoffs

## Assumptions

**Documents are in English.**
The OCR configuration, regex patterns for dates and party names, and all prompts are written for English. A multilingual version would need language detection and language-specific patterns.

**Legal documents follow loose structural conventions.**
The structured extraction relies on patterns like "Plaintiff:", "Case No:", and date formats. Documents that don't follow any convention (e.g. purely narrative text with no labels) will extract fewer structured fields but will still produce a draft — the LLM handles the messy cases better than regex does.

**Operator edits are improvements.**
The learning system trusts that when an operator changes something, the change is correct. In a production system you would want an edit review step before patterns get committed to the learned set, so that one bad edit doesn't degrade all future outputs.

**Sample documents are representative enough for demonstration.**
Three cases covering financial dispute, environmental violation, and employment dispute show the pipeline generalises across document types and handles both clean and noisy inputs.

---

## Tradeoffs

**Prompt injection vs. fine-tuning for the learning loop**

Prompt injection was chosen because it works immediately with zero training data, the learned patterns are fully transparent (you can open learned_patterns.json and read exactly what the system has learned), and they can be corrected by hand. Fine-tuning would eventually outperform this for subtle preferences but requires far more data and infrastructure than is practical for this scope.

**Local FAISS index vs. persistent vector database**

The FAISS index is rebuilt fresh on every run rather than saved to disk. For three small documents this takes under two seconds, so persistence would add complexity without any real benefit. At larger scale — hundreds of documents, each with many pages — you would want to persist the index and add a document ID layer so you can retrieve across a corpus rather than per-document.

**Regex extraction vs. LLM-based extraction for structured fields**

Stage 1 uses regex to pull dates, party names, and case numbers. This is fast and deterministic — the same input always gives the same output. The downside is it misses anything formatted unusually. The noisy case2 document demonstrates this: the garbled characters (0 for o, 1 for l) break the date patterns entirely, returning 0 dates even though dates are clearly present in the text. An LLM extractor would handle this better but would add latency and API cost to every document.

**Single LLM call per document vs. section-by-section generation**

One call produces the entire summary. This is simpler and cheaper. The risk is that if the retrieved chunks don't cover one section well, that section gets "Not found in document" rather than the system trying harder to find it. A multi-step approach would run a targeted retrieval and generation pass for each section independently, which would improve recall at the cost of 6-7x more API calls per document.

---

## Known Limitations

The noisy document (case2) demonstrates a real OCR limitation: character substitutions like `0` for `o` and `1` for `l` pass through extraction unchanged because they are valid characters — there is no way to know they are wrong without a reference. The draft still produces a correct summary in this case because the LLM is tolerant of these substitutions, but structured field extraction fails for dates and case numbers.

The chunk count per document is small (1 chunk each in the test run) because the sample documents are short. On real multi-page legal documents the retrieval layer would have meaningful ranking decisions to make across many more chunks.

Pattern extraction in the editor is heuristic-based. It catches common edit types reliably but would miss a reviewer who, for example, consistently reorders sections in a specific way. That kind of preference would require comparing document structure rather than line-level diffs.