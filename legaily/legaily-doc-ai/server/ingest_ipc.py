import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from apps.config.settings import get_settings
from apps.services import rag_engine


def ingest():
    settings = get_settings()
    data_dir = settings.data_dir
    index_dir = settings.ipc_index_dir

    print(f"Scanning {data_dir} for legal data...")
    all_docs = []

    if not data_dir.is_dir():
        print(f"Data directory not found: {data_dir}")
        return

    files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
    for filename in files:
        file_path = data_dir / filename
        print(f"Loading data from {file_path}...")
        loader = TextLoader(str(file_path), encoding='utf-8')
        documents = loader.load()
        for doc in documents:
            doc.metadata["source_file"] = filename
        all_docs.extend(documents)

    if not all_docs:
        print("No .txt files found to ingest.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.ingest_chunk_size,
        chunk_overlap=settings.ingest_chunk_overlap,
    )
    docs = splitter.split_documents(all_docs)
    print(f"Split into {len(docs)} chunks.")

    vectorstore = rag_engine.build_faiss_from_documents(docs, settings)
    rag_engine.save_faiss_index(vectorstore, index_dir)
    print(f"Saved index to {index_dir}")


if __name__ == "__main__":
    ingest()
