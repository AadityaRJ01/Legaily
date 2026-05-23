import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pdfplumber
from apps.config.settings import get_settings


def discover_pdf_jobs(data_dir):
    """Map each PDF in the data folder to a .txt output (same basename)."""
    jobs = {}
    for name in sorted(os.listdir(data_dir)):
        if name.lower().endswith(".pdf"):
            stem = os.path.splitext(name)[0]
            jobs[name] = f"{stem}.txt"
    return jobs


def parse_pdf(pdf_path, txt_path):
    print(f"Parsing {pdf_path} ...")
    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                full_text.append(text)
            if i % 10 == 0:
                print(f"  Processed {i} pages...")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))
    print(f"Saved to {txt_path}")


if __name__ == "__main__":
    settings = get_settings()
    data_dir = str(settings.data_dir)
    os.makedirs(data_dir, exist_ok=True)
    print(f"Data directory: {data_dir}")

    jobs = discover_pdf_jobs(data_dir)
    if not jobs:
        print("No PDF files found. Place statute PDFs in the data directory.")
    for pdf_name, txt_name in jobs.items():
        pdf_path = os.path.join(data_dir, pdf_name)
        txt_path = os.path.join(data_dir, txt_name)
        parse_pdf(pdf_path, txt_path)
