import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


def build_prompt(retrieved_chunks, learned_patterns=None):
    evidence_text = ""
    for chunk in retrieved_chunks:
        evidence_text += f"\n[EXCERPT {chunk['rank']}]\n"
        evidence_text += chunk["text"] + "\n"

    learned_section = ""
    if learned_patterns:
        learned_section = "\nLEARNED PATTERNS:\n"
        for p in learned_patterns:
            learned_section += f"- {p}\n"

    return f"""
You are a legal document analyst.

Use ONLY the excerpts below.

DOCUMENT:
{evidence_text}

{learned_section}

TASK:
Generate a Case Fact Summary.

FORMAT:
CASE FACT SUMMARY
=================
CASE NUMBER:
PARTIES:
KEY DATES:
CORE FACTS:
CLAIMS:
RELIEF SOUGHT:
EVIDENCE SOURCES:
"""


def generate_draft(retrieved_chunks, learned_patterns=None):
    prompt = build_prompt(retrieved_chunks, learned_patterns)

    print("  Calling LLM (OpenRouter)...")

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise legal document analyzer."},
                {"role": "user", "content": prompt}
            ]
        )

        draft_text = response.choices[0].message.content

    except Exception as e:
        draft_text = f"Draft generation failed: {e}"

    return {
        "draft": draft_text,
        "input_tokens": len(prompt.split()),
        "output_tokens": len(draft_text.split()),
        "model": "gpt-4o-mini",
        "chunks_used": [c["chunk_id"] for c in retrieved_chunks],
    }