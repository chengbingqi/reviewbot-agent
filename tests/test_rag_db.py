import sqlite3

import rag_db


class FakeEmbeddings:
    def embed_query(self, text):
        return [0.1] * rag_db.EMBEDDING_DIMENSION


def test_serialize_f32_dimension():
    data = rag_db.serialize_f32([0.0] * rag_db.EMBEDDING_DIMENSION)
    assert len(data) == rag_db.EMBEDDING_DIMENSION * 4


def test_search_empty_query_returns_empty_list():
    db = sqlite3.connect(":memory:")
    assert rag_db.search_similar_knowledge(db, "   ") == []


def test_ingest_knowledge_adds_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(rag_db, "_embeddings", FakeEmbeddings())
    db = rag_db.init_rag_db(str(tmp_path / "rag.db"))
    chunk_id = rag_db.ingest_knowledge(
        db,
        "Do not hard-code secrets.",
        source="test-source",
        rule_id="SEC-1",
        title="Secret Rule",
    )
    row = db.execute(
        "SELECT content, source, rule_id, title FROM code_chunks WHERE id = ?",
        (chunk_id,),
    ).fetchone()
    assert row == ("Do not hard-code secrets.", "test-source", "SEC-1", "Secret Rule")
