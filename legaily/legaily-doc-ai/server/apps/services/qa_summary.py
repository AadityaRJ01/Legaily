import cohere

from apps.config.settings import get_settings
from apps.services import rag_engine

# Summary is helpful but must not override specific PDF lines in Q&A
_SUMMARY_CAP = 3500


def _brief_summary(summary_text: str) -> str:
    s = (summary_text or "").strip()
    if not s:
        return ""
    if len(s) > _SUMMARY_CAP:
        s = s[:_SUMMARY_CAP] + "\n[... summary truncated for Q&A; use PDF passages below ...]"
    return f"=== BRIEF SUMMARY (background only — prefer PDF passages for specific questions) ===\n{s}\n\n"


def _build_context(
    full_text: str,
    summary_text: str,
    question: str,
    co: cohere.ClientV2,
    settings,
) -> tuple[str, str]:
    full_text = (full_text or "").strip()
    summary_text = (summary_text or "").strip()

    if not full_text and not summary_text:
        return "", "empty"

    # Medium docs: full PDF + short summary — any line answerable
    if full_text and len(full_text) + len(summary_text) <= settings.qa_full_context_limit:
        parts = [_brief_summary(summary_text)] if summary_text else []
        parts.append("=== FULL PDF TEXT ===\n" + full_text)
        return "".join(parts), "full-pdf"

    # Large docs (any case file): hybrid search on THIS pdf's text
    if full_text:
        retrieved = rag_engine.retrieve_for_document(
            full_text, question, co, settings
        )
        header = _brief_summary(summary_text)
        return (
            header
            + "=== PDF CONTENT FOR YOUR QUESTION (read carefully) ===\n"
            + retrieved,
            "keyword + faiss-rerank",
        )

    return _brief_summary(summary_text) or summary_text, "summary-only"


def _trim_history(history: list[dict] | None) -> list[dict]:
    """Few prior turns — avoids repeating old wrong 'Respondent: ...' answers."""
    if not history:
        return []
    cleaned = []
    for h in history:
        if h.get("role") == "assistant" and "ready to answer" in (
            h.get("content") or ""
        ).lower():
            continue
        cleaned.append(h)
    return cleaned[-4:]


def qa_over_summary(
    summary_text: str,
    question: str,
    history: list[dict] | None = None,
    full_text: str | None = None,
) -> str:
    """
    Open Q&A for ANY uploaded PDF — any question, any line, any document.
    No keyword→fixed-answer mapping.
    """
    settings = get_settings()
    summary_text = (summary_text or "").strip()
    full_text = (full_text or "").strip()
    question = (question or "").strip()

    if not summary_text and not full_text:
        return "Upload a PDF and click Summarize first."
    if not question:
        return "Please enter a question."
    if not settings.cohere_api_key:
        return "Legal AI Assistant is not configured (missing COHERE_API_KEY)."

    if not full_text:
        return (
            "PDF text was not loaded. Please click Summarize again on this file, "
            "then ask your question."
        )

    try:
        co = cohere.ClientV2(api_key=settings.cohere_api_key)
        context, strategy = _build_context(
            full_text, summary_text, question, co, settings
        )

        system_prompt = f"""You answer questions about ONE uploaded legal document.

Retrieval method: {strategy}

STRICT RULES:
1. Read the user's LATEST question word by word. Answer ONLY that — not a different topic.
2. NEVER copy a generic line from the summary (e.g. do not reply "**Respondent:** ..." unless they asked who is the main respondent in the caption).
3. If they ask what a term means (e.g. SEML, NCLAT, CoC), find that exact word in the PDF passages and explain what it means IN THIS CASE.
4. If they ask about "second respondent", "paragraph 5", a section, or any detail — use the PDF passages, not the short summary alone.
5. Use quotes from the PDF when possible. If not found, say clearly it was not found in this document.
6. This works for any case file the user uploads — do not assume a fixed case or party names.

DOCUMENT CONTENT:
{context}
"""

        messages = [{"role": "system", "content": system_prompt}]
        for h in _trim_history(history):
            role = "assistant" if h.get("role") == "assistant" else "user"
            content = (h.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        response = co.chat(
            model=settings.cohere_chat_model,
            messages=messages,
            temperature=settings.qa_temperature,
        )

        if (
            response.message
            and getattr(response.message, "content", None)
            and len(response.message.content) > 0
        ):
            first = response.message.content[0]
            return getattr(first, "text", str(first))
        return "No response could be generated."

    except Exception as e:
        return f"Error in QA pipeline: {str(e)}"
