import hashlib
import sqlite3
from dataclasses import dataclass
from struct import pack
from typing import Any

from config import get_config
from logging_config import logger


DEFAULT_SOURCE = "internal-rules"
EMBEDDING_DIMENSION = 384
_embeddings: Any | None = None


@dataclass
class RagResult:
    content: str
    source: str = DEFAULT_SOURCE
    rule_id: str | None = None
    title: str | None = None
    distance: float | None = None
    content_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source or DEFAULT_SOURCE,
            "rule_id": self.rule_id,
            "title": self.title,
            "distance": self.distance,
            "content_hash": self.content_hash,
        }


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info("Loading embedding model all-MiniLM-L6-v2")
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings


def serialize_f32(vector: list[float]) -> bytes:
    return pack("%sf" % len(vector), *vector)


def content_hash(text_content: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text_content.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _load_sqlite_vec(db: sqlite3.Connection) -> None:
    import sqlite_vec

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)


def _column_names(db: sqlite3.Connection, table_name: str) -> set[str]:
    return {row[1] for row in db.execute(f"PRAGMA table_info({table_name})")}


def _ensure_metadata_columns(db: sqlite3.Connection) -> None:
    columns = _column_names(db, "code_chunks")
    for name, ddl in {
        "source": "ALTER TABLE code_chunks ADD COLUMN source TEXT DEFAULT 'internal-rules'",
        "rule_id": "ALTER TABLE code_chunks ADD COLUMN rule_id TEXT",
        "title": "ALTER TABLE code_chunks ADD COLUMN title TEXT",
        "content_hash": "ALTER TABLE code_chunks ADD COLUMN content_hash TEXT",
    }.items():
        if name not in columns:
            db.execute(ddl)
    db.execute(
        """
        UPDATE code_chunks
        SET content_hash = lower(hex(randomblob(16)))
        WHERE content_hash IS NULL AND content IS NULL
        """
    )
    rows = db.execute(
        "SELECT id, content FROM code_chunks WHERE content_hash IS NULL AND content IS NOT NULL"
    ).fetchall()
    for row_id, content in rows:
        db.execute(
            "UPDATE code_chunks SET content_hash = ? WHERE id = ?",
            (content_hash(content), row_id),
        )
    db.execute("CREATE INDEX IF NOT EXISTS idx_code_chunks_content_hash ON code_chunks(content_hash)")


def init_rag_db(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or get_config().rag_db_path
    db = sqlite3.connect(path)
    _load_sqlite_vec(db)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS code_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT DEFAULT 'internal-rules',
            rule_id TEXT,
            title TEXT,
            content_hash TEXT
        )
        """
    )
    _ensure_metadata_columns(db)
    db.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(embedding float[{EMBEDDING_DIMENSION}])"
    )
    db.commit()
    return db


def ingest_knowledge(
    db: sqlite3.Connection,
    text_content: str,
    source: str = DEFAULT_SOURCE,
    rule_id: str | None = None,
    title: str | None = None,
    skip_duplicates: bool = True,
) -> int:
    digest = content_hash(text_content)
    if skip_duplicates:
        existing = db.execute(
            "SELECT id FROM code_chunks WHERE content_hash = ? LIMIT 1", (digest,)
        ).fetchone()
        if existing:
            return int(existing[0])

    vector = get_embeddings().embed_query(text_content)
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO code_chunks (content, source, rule_id, title, content_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        (text_content, source, rule_id, title, digest),
    )
    chunk_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
        (chunk_id, serialize_f32(vector)),
    )
    db.commit()
    return int(chunk_id)


def search_similar_knowledge(
    db: sqlite3.Connection,
    query: str,
    top_k: int = 3,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    k = limit or top_k
    if not query.strip():
        return []

    try:
        query_vector = get_embeddings().embed_query(query)
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    code_chunks.content,
                    COALESCE(code_chunks.source, ?) AS source,
                    code_chunks.rule_id,
                    code_chunks.title,
                    code_chunks.content_hash,
                    vec_chunks.distance
                FROM vec_chunks
                LEFT JOIN code_chunks ON code_chunks.id = vec_chunks.rowid
                WHERE vec_chunks.embedding MATCH ? AND k = ?
                """,
                (DEFAULT_SOURCE, serialize_f32(query_vector), k),
            )
        except sqlite3.OperationalError:
            cursor.execute(
                """
                SELECT
                    code_chunks.content,
                    COALESCE(code_chunks.source, ?) AS source,
                    code_chunks.rule_id,
                    code_chunks.title,
                    code_chunks.content_hash,
                    NULL AS distance
                FROM vec_chunks
                LEFT JOIN code_chunks ON code_chunks.id = vec_chunks.rowid
                WHERE vec_chunks.embedding MATCH ? AND k = ?
                """,
                (DEFAULT_SOURCE, serialize_f32(query_vector), k),
            )

        rows = cursor.fetchall()
        results = [
            RagResult(
                content=row[0],
                source=row[1] or DEFAULT_SOURCE,
                rule_id=row[2],
                title=row[3],
                content_hash=row[4],
                distance=row[5],
            ).as_dict()
            for row in rows
            if row[0]
        ]
        logger.info("RAG retrieval hit_count=%s top_k=%s", len(results), k)
        return results
    except Exception as exc:
        logger.exception("RAG retrieval failed: %s", exc)
        return []


def seed_default_knowledge(db: sqlite3.Connection) -> None:
    existing = db.execute("SELECT COUNT(*) FROM code_chunks").fetchone()[0]
    if existing:
        logger.info("RAG database already contains %s chunks; skip seed", existing)
        return

    docs = [
        {
            "rule_id": "SECRET-001",
            "title": "Secret Handling Rule",
            "content": "Internal rule: database passwords, tokens, and API keys must not be hard-coded. Read them from environment variables or a secret manager.",
        },
        {
            "rule_id": "SQL-001",
            "title": "SQL Injection Rule",
            "content": "Internal rule: SQL statements must use parameterized queries. Do not concatenate user input into SQL strings.",
        },
        {
            "rule_id": "LOG-001",
            "title": "Sensitive Logging Rule",
            "content": "Internal rule: logs must not include secrets, raw credentials, or full connection strings.",
        },
    ]
    for doc in docs:
        ingest_knowledge(
            db,
            doc["content"],
            source=DEFAULT_SOURCE,
            rule_id=doc["rule_id"],
            title=doc["title"],
        )
    logger.info("Seeded %s default RAG rules", len(docs))


if __name__ == "__main__":
    database = init_rag_db()
    seed_default_knowledge(database)
    results = search_similar_knowledge(database, "hard-coded database password", top_k=3)
    print("SQLite-Vec RAG database is ready.")
    for item in results:
        title = item.get("title") or item.get("rule_id") or "Untitled"
        print(f"- {item.get('source', DEFAULT_SOURCE)}: {title}")
