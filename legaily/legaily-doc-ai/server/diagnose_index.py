import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.config.settings import get_settings
from apps.services import rag_engine


def diagnose(query: str):
    settings = get_settings()
    vectorstore = rag_engine.load_faiss_index(settings.statutes_index_dir, settings)

    print(f"\nQuery: {query}")
    docs = vectorstore.similarity_search(query, k=15)
    for i, doc in enumerate(docs):
        print(f"{i+1}. Law: {doc.metadata.get('law_name')} | Section: {doc.metadata.get('section_number')}")
        print(f"   Content: {doc.page_content[:150]}...")
        print("-" * 10)


if __name__ == "__main__":
    diagnose("cheating")
