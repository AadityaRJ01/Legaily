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
    ipc_file = settings.ipc_law_file
    index_dir = settings.ipc_sample_index_dir
    sample_txt = settings.server_root / "ipc_sample.txt"

    print(f"Loading sample from {ipc_file}...")
    with open(ipc_file, "r", encoding="utf-8") as f:
        content = "".join([next(f) for _ in range(2000)])

    with open(sample_txt, "w", encoding="utf-8") as f:
        f.write(content)

    loader = TextLoader(str(sample_txt), encoding="utf-8")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.split_documents(documents)
    print(f"Split into {len(docs)} chunks.")

    vectorstore = rag_engine.build_faiss_from_documents(docs, settings)
    rag_engine.save_faiss_index(vectorstore, index_dir)
    print(f"Saved index to {index_dir}")


if __name__ == "__main__":
    ingest()
