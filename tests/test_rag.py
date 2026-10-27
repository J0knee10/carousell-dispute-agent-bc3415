from dispute_agent.evaluation.retrieval import evaluate_retrieval
from dispute_agent.rag.chunker import find_clause_id, load_clauses
from dispute_agent.rag.lexical import tokenize


def test_clauses_are_unique_and_sourced():
    clauses = load_clauses()
    ids = [c.clause_id for c in clauses]
    assert len(ids) == len(set(ids))
    assert len(clauses) >= 30
    for c in clauses:
        assert c.url.startswith("https://support.carousell.com/")
        assert c.text
        assert not c.text.rstrip().endswith((".png", ".jpg"))


def test_key_rules_are_findable():
    for doc, phrase in [
        ("buyer_protection_refund_policy", "light pink"),
        ("buyer_protection_refund_policy", "whichever occurs first"),
        ("what_is_buyer_protection", "Item Not Received: Covered only"),
        ("dispute_process_overview", "fail to respond within the 24-hour"),
    ]:
        assert find_clause_id(doc, phrase), phrase


def test_tokenizer_stems_plurals():
    assert tokenize("missing parts") == tokenize("missing part")


def test_hybrid_retrieval_beats_single_methods(store):
    res = evaluate_retrieval(k=5)
    hybrid = res["modes"]["hybrid"]
    assert hybrid["hit@5"] >= 0.9
    assert hybrid["mrr"] >= max(res["modes"]["dense"]["mrr"], res["modes"]["lexical"]["mrr"])


def test_retrieve_returns_citable_clauses(store):
    found = store.retrieve("buyer received a different colour than listed", k=3)
    assert len(found) == 3
    assert all(c.clause_id and c.url for c in found)
