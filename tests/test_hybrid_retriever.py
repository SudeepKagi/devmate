import pytest
from devmate.context.retrievers.hybrid_chroma import tokenize_code, BM25Index


def test_tokenize_code():
    code = "def calculate_total_cost(inputTokens, outputTokens):"
    tokens = tokenize_code(code)
    assert "calculate" in tokens
    assert "total" in tokens
    assert "cost" in tokens
    assert "input" in tokens
    assert "tokens" in tokens
    assert "output" in tokens


def test_bm25_index_scoring():
    docs = [
        "class ModelRouter: routes between light and strong LLM models based on task complexity",
        "def sandboxed_execution: isolates bash and python commands inside container or path jail",
        "def calculate_cost: pricing calculation based on official provider tokens",
    ]
    doc_ids = ["doc_router", "doc_sandbox", "doc_cost"]
    bm25 = BM25Index(docs, doc_ids)

    # Search for router
    results = bm25.search("dynamic model routing between llm models")
    assert len(results) > 0
    assert results[0][0] == "doc_router"
    assert results[0][2] == 1  # Rank 1

    # Search for sandboxing
    results_sb = bm25.search("security containment path jail execution")
    assert len(results_sb) > 0
    assert results_sb[0][0] == "doc_sandbox"


def test_bm25_empty_query():
    docs = ["hello world"]
    doc_ids = ["1"]
    bm25 = BM25Index(docs, doc_ids)
    assert bm25.search("") == []
