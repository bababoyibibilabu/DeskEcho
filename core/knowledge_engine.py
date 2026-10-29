import sqlite3
import datetime
import jieba
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
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
                    is_useful INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                self.conn.execute("ALTER TABLE meeting_slices ADD COLUMN is_useful INTEGER DEFAULT NULL")
            except Exception:
                pass
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    turn_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_turns (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER,
                    user_query TEXT,
                    rewritten_query TEXT,
                    spoken_summary TEXT,
                    detailed_markdown TEXT,
                    focal_topic TEXT,
                    slice_ids TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
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

    def query_slices_by_entity_names(self, names: List[str], limit: int = 8) -> List[Dict[str, Any]]:
        """根据人名或别名反查涉及该人员的历史会议切片（用于实体动态画像）"""
        if not names:
            return []
        conditions = []
        params = []
        for name in names:
            conditions.append("(raw_text LIKE ? OR summary LIKE ?)")
            params.extend([f"%{name}%", f"%{name}%"])
        
        where_clause = " OR ".join(conditions)
        sql = f"SELECT id, start_time, end_time, raw_text, summary FROM meeting_slices WHERE {where_clause} ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"[MeetingStore] 实体关联切片查询失败: {e}")
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

    def get_records_by_ids(self, slice_ids: List[str]) -> List[Dict[str, Any]]:
        """按切片 ID 列表批量拉取历史切片详情"""
        if not slice_ids:
            return []
        try:
            placeholders = ",".join(["?"] * len(slice_ids))
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM meeting_slices WHERE id IN ({placeholders})", slice_ids)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[MeetingStore] 按ID获取切片异常: {e}")
            return []

    def query_by_time_range(self, start_date_str: str, end_date_str: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM meeting_slices WHERE start_time >= ? AND start_time <= ? ORDER BY start_time ASC",
            (start_date_str, end_date_str)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # ---------------- 历史问答与多轮会话持久化 ----------------
    def create_or_update_session(self, session_id: str, title: str, turn_count: int = 1):
        """创建或更新会话元数据"""
        with self.conn:
            self.conn.execute("""
                INSERT INTO chat_sessions (id, title, turn_count, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    turn_count = excluded.turn_count,
                    updated_at = CURRENT_TIMESTAMP
            """, (session_id, title, turn_count))

    def save_chat_turn(self, turn_id: str, session_id: str, turn_index: int, user_query: str,
                       rewritten_query: str, spoken_summary: str, detailed_markdown: str,
                       focal_topic: str, slice_ids: List[str]):
        """持久化保存会话的单轮问答详情"""
        import json
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO chat_turns
                (id, session_id, turn_index, user_query, rewritten_query, spoken_summary, detailed_markdown, focal_topic, slice_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (turn_id, session_id, turn_index, user_query, rewritten_query, spoken_summary,
                  detailed_markdown, focal_topic, json.dumps(slice_ids, ensure_ascii=False)))

    def get_all_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取所有历史会话概要（按最后活跃时间倒序）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, turn_count, created_at, updated_at
            FROM chat_sessions
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_session_turns(self, session_id: str) -> List[Dict[str, Any]]:
        """拉取指定会话下的全部历史问答卡片（按轮次正序）"""
        import json
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, session_id, turn_index, user_query, rewritten_query, spoken_summary, detailed_markdown, focal_topic, slice_ids, created_at
            FROM chat_turns
            WHERE session_id = ?
            ORDER BY turn_index ASC
        """, (session_id,))
        rows = []
        for r in cursor.fetchall():
            d = dict(r)
            try:
                d["slice_ids"] = json.loads(d["slice_ids"]) if d.get("slice_ids") else []
            except Exception:
                d["slice_ids"] = []
            rows.append(d)
        return rows

    def delete_session(self, session_id: str):
        """删除指定历史会话及其关联问答卡片"""
        with self.conn:
            self.conn.execute("DELETE FROM chat_turns WHERE session_id = ?", (session_id,))
            self.conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))

    def set_slice_useful(self, slice_id: str, is_useful: bool = True) -> bool:
        """标记或恢复切片为有用资产 (1=有用, 0=次要, NULL=默认AI研判)"""
        try:
            val = 1 if is_useful else 0
            with self.conn:
                self.conn.execute("UPDATE meeting_slices SET is_useful = ? WHERE id = ?", (val, slice_id))
            return True
        except Exception as e:
            print(f"[MeetingStore] 更新切片 {slice_id} 状态失败: {e}")
            return False

    def delete_slice(self, slice_id: str) -> bool:
        """删除单个会议切片 (同步清理 SQLite 与 ChromaDB 向量集合)"""
        try:
            with self.conn:
                self.conn.execute("DELETE FROM meeting_slices WHERE id = ?", (slice_id,))
            if hasattr(self, "collection") and self.collection is not None:
                try:
                    self.collection.delete(ids=[slice_id])
                except Exception as ce:
                    print(f"[MeetingStore] ChromaDB 删除切片 {slice_id} 提示: {ce}")
            return True
        except Exception as e:
            print(f"[MeetingStore] 删除切片 {slice_id} 失败: {e}")
            return False

    def delete_slices(self, slice_ids: List[str]) -> int:
        """批量删除会议切片 (同步清理 SQLite 与 ChromaDB 向量集合)"""
        if not slice_ids:
            return 0
        deleted_count = 0
        try:
            with self.conn:
                for sid in slice_ids:
                    self.conn.execute("DELETE FROM meeting_slices WHERE id = ?", (sid,))
                    deleted_count += 1
            if hasattr(self, "collection") and self.collection is not None:
                try:
                    self.collection.delete(ids=slice_ids)
                except Exception as ce:
                    print(f"[MeetingStore] ChromaDB 批量删除切片提示: {ce}")
            return deleted_count
        except Exception as e:
            print(f"[MeetingStore] 批量删除切片失败: {e}")
            return deleted_count


def assess_slice_utility(summary: str, raw_text: str) -> Tuple[bool, str]:
    """
    AI 研判会议切片价值分级：识别闲聊、试音、暂停或缺乏实质性决议与推进的次要级切片
    返回: (is_low_utility: bool, reason: str)
    """
    s = (summary or "").strip()
    r = (raw_text or "").strip()
    
    # 1. 极短文本与明显无意义的试音碎片
    if len(r) < 60:
        return True, "转录文本过短或为偶发试音碎片"
        
    # 2. 核心议题中明确标示无议题、暂停或开场问候
    first_line = s.split("\n")[0] if s else ""
    if any(k in first_line for k in ["无实质议题", "无明确议题", "会议暂停", "仅为开场问候", "仅为打招呼", "闲聊"]):
        return True, "开场寒暄、会议暂停或无实际议题"
        
    # 3. 提取决策与待办段落
    lines = s.split("\n")
    decision_text = ""
    action_text = ""
    current_sec = None
    for line in lines:
        line_s = line.strip()
        if "2. 决策与结论" in line_s or "【关键结论】" in line_s or "【结论】" in line_s:
            current_sec = "decision"
            decision_text += line_s
        elif "3. 待办事项" in line_s or "【待办事项】" in line_s or "【待办】" in line_s:
            current_sec = "action"
            action_text += line_s
        elif "4. 事实备忘" in line_s or "【事实备忘】" in line_s or "1. 核心议题" in line_s:
            current_sec = None
        else:
            if current_sec == "decision":
                decision_text += " " + line_s
            elif current_sec == "action":
                action_text += " " + line_s
                
    no_decision = (
        not decision_text 
        or "无（" in decision_text 
        or "：无" in decision_text 
        or ": 无" in decision_text
        or "未形成明确决策" in decision_text
        or "暂无决策" in decision_text
    )
    no_action = (
        not action_text 
        or "无（" in action_text 
        or "：无" in action_text 
        or ": 无" in action_text
        or "无待办" in action_text
        or "未明确具体待办" in action_text
        or "无明确待办" in action_text
    )
    if no_decision and no_action:
        return True, "无实质性决策且无落地待办推进"
        
    if any(k in s for k in ["闲聊", "开玩笑", "寒暄", "测试音频"]):
        return True, "非正式商业沟通，偏寒暄闲聊"
        
    return False, "正常正式业务资产"
