import sqlite3
import sqlite_vec
from struct import pack
from langchain_huggingface import HuggingFaceEmbeddings

print("⏳ 正在加载本地向量模型 (首次运行会下载约 80MB，请耐心等待)...")
# 初始化本地免费的向量模型 (输出 384 维度的向量)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def serialize_f32(vector):
    """将 Python 列表转换为 SQLite-Vec 需要的底层二进制格式"""
    return pack("%sf" % len(vector), *vector)

def init_rag_db(db_path="reviewbot_memory.db"):
    """初始化 SQLite 数据库并加载 Vec 扩展"""
    db = sqlite3.connect(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    
    # 创建两张表：一张存原文，一张存向量
    db.execute("CREATE TABLE IF NOT EXISTS code_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)")
    # 注意：这里的 384 必须和模型的输出维度一致
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(embedding float[384])")
    db.commit()
    return db

def ingest_knowledge(db, text_content):
    """将文档/代码片段向量化并存入数据库"""
    # 1. 将文本转为向量
    vector = embeddings.embed_query(text_content)
    
    # 2. 存入数据库
    cursor = db.cursor()
    cursor.execute("INSERT INTO code_chunks (content) VALUES (?)", (text_content,))
    chunk_id = cursor.lastrowid # 获取刚刚插入的文本 ID
    
    # 3. 将向量和文本 ID 绑定存入虚拟表
    cursor.execute(
        "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)", 
        (chunk_id, serialize_f32(vector))
    )
    db.commit()

def search_similar_knowledge(db, query, limit=1):
    """根据问题检索最相关的背景知识"""
    query_vector = embeddings.embed_query(query)
    cursor = db.cursor()
    
    # 修复报错：使用 sqlite-vec 官方原生支持的 `k = ?` 语法，而不是 ORDER BY ... LIMIT
    cursor.execute('''
        SELECT code_chunks.content 
        FROM vec_chunks 
        LEFT JOIN code_chunks ON code_chunks.id = vec_chunks.rowid
        WHERE vec_chunks.embedding MATCH ? AND k = ?
    ''', (serialize_f32(query_vector), limit))
    
    results = cursor.fetchall()
    return [row[0] for row in results]

# ==========================================
# 本地模块测试
# ==========================================
if __name__ == "__main__":
    db = init_rag_db()
    print("📦 SQLite-Vec 数据库初始化完成！\n")
    
    # 模拟我们把项目里的一些“内部规定”存入了数据库
    test_docs = [
        "内部开发规范：所有的数据库密码严禁硬编码在代码中，必须从环境变量 DB_PASS 中读取。",
        "架构设计说明：我们的前端页面统一部署在 8080 端口，API 服务在 8000 端口。"
    ]
    
    for doc in test_docs:
        ingest_knowledge(db, doc)
        print(f"写入知识: {doc}")
        
    print("\n🔍 测试检索功能...")
    # 测试能否根据语义找回规定
    retrieved = search_similar_knowledge(db, "代码里写了密码怎么办？")
    print(f"检索到的最相关知识: {retrieved[0]}")