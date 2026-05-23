import os
import re
import pickle
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from langchain_community.document_loaders import TextLoader

from apps.config.settings import get_settings
from apps.services.legal_splitter import LegalSectionSplitter
from apps.services import rag_engine
from rank_bm25 import BM25Okapi

_GAZETTE_NOISE = re.compile(
    r'(jftLVªh.*?\n'
    r'|xxxGIDE\w+xxx\n'
    r'|vlk\/kkj\.k\n'
    r'|izkf\/[^\n]+\n'
    r'|lañ \d+\][^\n]+\n'
    r'|No\.\s*\d+\]\s+NEW DELHI[^\n]+\n'
    r'|bl Hkkx[^\n]+\n'
    r'|Separate paging[^\n]+\n'
    r'|MINISTRY OF LAW[^\n]+\n'
    r'|New Delhi,\s*the\s*\d+[^\n]+\n'
    r'|\(Legislative Department\)\n'
    r'|THE GAZETTE OF INDIA EXTRAORDINARY[^\n]+\n'
    r'|(?:Sec\.\s*\d+\])[^\n]+\n'
    r'|\[Part II[^\n]*\n'
    r'|_{5,}(?:\r?\n|$)'
    r'|\-{5,}(?:\r?\n|$))',
    re.MULTILINE
)


def clean_gazette_text(text: str) -> str:
    text = _GAZETTE_NOISE.sub('\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_law_name(filename):
    filename = filename.lower()
    if "ipc" in filename:
        return "Indian Penal Code (IPC)"
    if "bnss" in filename:
        return "Bharatiya Nagarik Suraksha Sanhita (BNSS)"
    if "bns" in filename:
        return "Bharatiya Nyaya Sanhita (BNS)"
    if "bsa" in filename:
        return "Bharatiya Sakshya Adhiniyam (BSA)"
    return "Other Legal Statute"


def tokenize_for_bm25(text: str) -> list[str]:
    return [t for t in re.split(r'\W+', text.lower()) if t]


def ingest():
    settings = get_settings()
    data_dir = settings.data_dir
    index_dir = settings.statutes_index_dir

    print(f"Scanning {data_dir} for legal data...")
    all_docs = []

    if not data_dir.is_dir():
        print(f"Error: Data directory not found: {data_dir}")
        return

    files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
    print(f"Found files: {files}")

    for filename in files:
        file_path = data_dir / filename
        law_name = get_law_name(filename)
        print(f"Loading {law_name} from {file_path}...")
        try:
            loader = TextLoader(str(file_path), encoding='utf-8')
            documents = loader.load()
            for doc in documents:
                doc.page_content = clean_gazette_text(doc.page_content)
                doc.metadata["source_file"] = filename
                doc.metadata["law_name"] = law_name
            all_docs.extend(documents)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    if not all_docs:
        print("No legal documents found to ingest.")
        return

    print(f"Splitting {len(all_docs)} documents into granular sections...")
    text_splitter = LegalSectionSplitter()
    docs = text_splitter.split_documents(all_docs)
    print(f"Split into {len(docs)} sections.")

    from collections import Counter
    counts = Counter(d.metadata.get('law_name', 'Unknown') for d in docs)
    for law, count in sorted(counts.items()):
        print(f"  {law}: {count} sections")

    print("Building BM25 index...")
    tokenized_corpus = [tokenize_for_bm25(d.page_content) for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)

    print(f"Creating FAISS index with {settings.embedding_model}...")
    vectorstore = rag_engine.build_faiss_from_documents(docs, settings)

    rag_engine.save_faiss_index(vectorstore, index_dir)
    print(f"Saved FAISS index to {index_dir}")

    bm25_path = index_dir / "bm25_index.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump({"bm25": bm25, "docs": docs}, f)
    print(f"Saved BM25 index to {bm25_path}")
    print("Ingestion complete successfully.")


if __name__ == "__main__":
    ingest()
