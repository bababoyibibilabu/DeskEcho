import sqlite3
import datetime
import jieba
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from config import Config

class MeetingStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Config.DATA_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化 ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=str(self.db_path / "chroma"))
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.chroma_client.get_or_create_collection(
            name="meeting_memories",
            embedding_function=self.emb_fn
        )
        
        # 初始化 SQLite
        self.sqlite_path = self.db_path / "records.db"
        self.conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_sqlite()

    def _init_sqlite(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS meeting_slices (
                    id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    raw_text TEXT,
                    summary TEXT,
                    audio_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def insert_record(self, slice_id: str, start_time: str, end_time: str, raw_text: str, summary: str, audio_path: str = ""):
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO meeting_slices (id, start_time, end_time, raw_text, summary, audio_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (slice_id, start_time, end_time, raw_text, summary, audio_path)
            )

        content_to_embed = f"【时间段】: {start_time} 至 {end_time}\n【结构化纪要】:\n{summary}\n【原始对话】:\n{raw_text}"
        self.collection.upsert(
            documents=[content_to_embed],
            metadatas=[{
                "slice_id": slice_id,
                "start_time": start_time,
                "end_time": end_time
            }],
            ids=[slice_id]
        )
        print(f"[MeetingStore] 记录 {slice_id} 已成功存入 SQLite 与 ChromaDB 知识库")

    def query_vector(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        try:
            count = self.collection.count()
            if count == 0:
                return []
            
            n = min(n_results, count)
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n
            )
            
            docs = []
            if results and results.get("documents") and results["documents"]:
                for i in range(len(results["documents"][0])):
                    doc = results["documents"][0][i]
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    slice_id = results["ids"][0][i] if results.get("ids") else ""
                    docs.append({
                        "slice_id": slice_id,
                        "content": doc,
                        "metadata": meta
                    })
            return docs
        except Exception as e:
            print(f"[MeetingStore] 向量检索失败: {e}")
            return []

    def query_keyword(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        基于 jieba 中文精准分词与权重评分的关键词检索
        解决英文向量模型对中文人名、数字、专有名词召回率不足的问题
        """
        stop_words = {"什么", "怎么", "如何", "负责", "工作", "关于", "对于", "哪方", "方面", "大家", "如果", "是不是", "可以", "请问", "会议", "多少", "大概", "哪些", "提到", "出来"}
        words = [w for w in jieba.cut_for_search(query_text) if len(w) >= 2 and w not in stop_words]

        if not words:
            return []

        # 构造加权评分 SQL (命中多个专有词得分更高，优先排在前面)
        score_cases = []
        where_conditions = []
        params = []

        for w in words[:5]:
            score_cases.append("(CASE WHEN raw_text LIKE ? OR summary LIKE ? THEN 3 ELSE 0 END)")
            where_conditions.append("(raw_text LIKE ? OR summary LIKE ?)")
            params.extend([f"%{w}%", f"%{w}%"])

        sql = f"""
        SELECT *, ({' + '.join(score_cases)}) AS match_score
        FROM meeting_slices
        WHERE {' OR '.join(where_conditions)}
        ORDER BY match_score DESC, start_time DESC
        LIMIT ?
        """
        params.append(limit)

        try:
            cursor = self.conn.cursor()
            # 传递两遍 params 给 score_cases 与 where_conditions
            total_params = params[:-1] + params
            cursor.execute(sql, total_params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[MeetingStore] 关键词加权检索异常: {e}")
            return []

    def get_total_count(self) -> int:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM meeting_slices")
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def query_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM meeting_slices ORDER BY start_time DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def query_by_time_range(self, start_date_str: str, end_date_str: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM meeting_slices WHERE start_time >= ? AND start_time <= ? ORDER BY start_time ASC",
            (start_date_str, end_date_str)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
