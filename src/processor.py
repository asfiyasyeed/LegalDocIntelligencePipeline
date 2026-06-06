import fitz                    # this is PyMuPDF - reads PDFs
import pytesseract             # this does OCR (reads scanned images)
from PIL import Image          # handles images
import io                      # helps convert bytes to image
import re                      # for finding patterns like dates and names
import os

# If you're on Windows, tell pytesseract where Tesseract is installed
# Uncomment the line below and change the path if needed:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_from_pdf(filepath):
    """
    Try to get text from a PDF.
    First try native extraction (fast, works on real PDFs).
    If that fails or returns nothing, use OCR (for scanned images).
    """
    doc = fitz.open(filepath)
    all_pages = []
    full_text = ""

    for page_num, page in enumerate(doc):
        # Try native text extraction first
        native_text = page.get_text()

        if len(native_text.strip()) > 50:
            # Native text worked — use it
            page_text = native_text
            method_used = "native"
        else:
            # Page looks like a scanned image — use OCR
            print(f"  Page {page_num + 1}: native text too short, using OCR...")
            try:
                # Convert the PDF page to an image
                pix = page.get_pixmap(dpi=200)  # higher DPI = better OCR
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                
                # Run OCR on the image
                page_text = pytesseract.image_to_string(img)
                method_used = "ocr"
            except Exception as e:
                print(f"  OCR failed on page {page_num + 1}: {e}")
                page_text = ""
                method_used = "failed"

        all_pages.append({
            "page_number": page_num + 1,
            "text": page_text,
            "method": method_used
        })
        full_text += f"\n--- Page {page_num + 1} ---\n" + page_text

    doc.close()
    return full_text, all_pages


def extract_text_from_txt(filepath):
    """
    For .txt files (like our noisy case2 file), just read directly.
    """
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    pages = [{"page_number": 1, "text": text, "method": "txt"}]
    return text, pages


def extract_dates(text):
    """
    Find all dates in the text using regex patterns.
    Handles formats like: March 14, 2023 / 14/03/2023 / 2023-03-14
    """
    patterns = [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\bFY\s*\d{4}-\d{2,4}\b',
    ]
    dates = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(found)
    return list(set(dates))  # remove duplicates


def extract_parties(text):
    """
    Find Plaintiff and Defendant names.
    Looks for lines like "Plaintiff: John Smith"
    """
    parties = []
    patterns = [
        r'Plaintiff[:\s]+([^\n,]+)',
        r'Defendant[:\s]+([^\n,]+)',
        r'Petitioner[:\s]+([^\n,]+)',
        r'Respondent[:\s]+([^\n,]+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            cleaned = match.strip()
            if cleaned and len(cleaned) > 2:
                parties.append(cleaned)
    return parties


def extract_case_number(text):
    """
    Find case numbers like CIV-2023-00451
    """
    pattern = r'\b[A-Z]{2,5}[-/]\d{4}[-/]\d{3,6}\b'
    matches = re.findall(pattern, text)
    return matches[0] if matches else "Not found"


def calculate_confidence(pages):
    """
    Estimate how clean the extraction was.
    If most pages used native extraction, confidence is high.
    """
    if not pages:
        return 0.0
    native_count = sum(1 for p in pages if p["method"] == "native")
    return round(native_count / len(pages), 2)


def process_document(filepath):
    """
    MAIN FUNCTION — call this with any file path.
    Returns a structured dict with all extracted information.
    """
    print(f"\nProcessing: {filepath}")
    
    # Check file exists
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    # Choose extraction method based on file type
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == ".pdf":
        full_text, pages = extract_text_from_pdf(filepath)
    elif ext in [".txt", ".text"]:
        full_text, pages = extract_text_from_txt(filepath)
    else:
        return {"error": f"Unsupported file type: {ext}"}

    # Extract structured fields
    dates = extract_dates(full_text)
    parties = extract_parties(full_text)
    case_number = extract_case_number(full_text)
    confidence = calculate_confidence(pages)

    # Build the output dict
    result = {
        "filepath": filepath,
        "raw_text": full_text,
        "pages": pages,
        "structured": {
            "case_number": case_number,
            "parties": parties,
            "dates": dates,
        },
        "confidence": confidence,
        "total_pages": len(pages),
        "total_chars": len(full_text),
    }

    print(f"  Done. Pages: {len(pages)}, Confidence: {confidence}, Dates found: {len(dates)}")
    return result


# Test it directly if you run this file
if __name__ == "__main__":
    result = process_document("sample_inputs/case1.pdf")
    print("\n=== EXTRACTED TEXT (first 500 chars) ===")
    print(result["raw_text"][:500])
    print("\n=== STRUCTURED FIELDS ===")
    print("Case Number:", result["structured"]["case_number"])
    print("Parties:", result["structured"]["parties"])
    print("Dates:", result["structured"]["dates"])