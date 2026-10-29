import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ConversationTurn:
    """
    单轮对话数据实体 (Session Turn Entity)
    记录原始输入、意图重写搜索句、口语结论、详尽 Markdown、命中切片 ID 及时间戳
    """
    user_query: str                          # 用户原始提问 (如: "解释下掌握度？")
    rewritten_query: str                     # 改写后的自包含检索句
    spoken_summary: str                      # 极简口语结论 (供下一轮快速定位核心要点)
    detailed_markdown: str                   # 详尽图文解答
    focal_topic: str = ""                    # 本轮核心议题/实体 (如: "知识点掌握度与BKT模型")
    slice_ids: List[str] = field(default_factory=list)  # 命中的会议切片 ID
    timestamp: float = field(default_factory=time.time)

class SessionManager:
    """
    轻量线程安全会话上下文管理器 (Conversation Session Manager)
    - 借鉴 Dify 与 LangChain 会话缓冲模型
    - 支持时间衰减 (默认 10 分钟未交互自动断开上下文)
    - 滑动窗口截断 (保留最近 K=3 轮高保真问答)
    - 支持 SQLite 会话与轮次全量持久化
    """
    def __init__(self, store=None, ttl_seconds: float = 600.0, max_turns: int = 3):
        self.store = store
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self.turns: List[ConversationTurn] = []
        self.last_active_time = 0.0
        self.current_session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.current_session_title = ""
        self.current_total_turns = 0

    def start_new_session(self) -> str:
        """主动清空当前内存上下文，开启全新的独立会话"""
        self.clear()
        self.current_session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.current_session_title = ""
        self.current_total_turns = 0
        return self.current_session_id

    def add_turn(self, turn: ConversationTurn):
        """记录新一轮对话，并持久化至 SQLite 会话存储"""
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)
        self.last_active_time = time.time()
        self.current_total_turns += 1

        # 提炼会话标题 (若尚未命名，用焦点话题或首个问题提炼)
        if not self.current_session_title:
            if turn.focal_topic and turn.focal_topic not in ("无", "通用"):
                self.current_session_title = f"{turn.focal_topic}探讨"
            else:
                self.current_session_title = turn.user_query[:20].strip()

        # 持久化到存储
        if self.store:
            try:
                self.store.create_or_update_session(
                    session_id=self.current_session_id,
                    title=self.current_session_title,
                    turn_count=self.current_total_turns
                )
                turn_id = f"turn_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
                self.store.save_chat_turn(
                    turn_id=turn_id,
                    session_id=self.current_session_id,
                    turn_index=self.current_total_turns,
                    user_query=turn.user_query,
                    rewritten_query=turn.rewritten_query,
                    spoken_summary=turn.spoken_summary,
                    detailed_markdown=turn.detailed_markdown,
                    focal_topic=turn.focal_topic,
                    slice_ids=turn.slice_ids
                )
            except Exception as e:
                print(f"[SessionManager] 持久化会话轮次失败: {e}")

    def load_session(self, session_id: str) -> List[ConversationTurn]:
        """从 SQLite 加载指定历史会话，若在 TTL 内则恢复上下文；若已超时则仅载入供回溯，不激活追问"""
        self.clear()
        self.current_session_id = session_id
        if not self.store:
            return []
        
        db_turns = self.store.get_session_turns(session_id)
        if not db_turns:
            return []

        self.current_total_turns = len(db_turns)
        sessions = self.store.get_all_sessions(limit=100)
        updated_at = ""
        for s in sessions:
            if s["id"] == session_id:
                self.current_session_title = s.get("title", "")
                updated_at = s.get("updated_at", "")
                break

        # 检查会话是否已超过 TTL (默认 600 秒)
        is_active = False
        if updated_at:
            try:
                import datetime
                clean_str = updated_at.replace("T", " ")
                if "." in clean_str:
                    dt = datetime.datetime.strptime(clean_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    dt = datetime.datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                diff_local = abs((datetime.datetime.now() - dt).total_seconds())
                diff_utc = abs((datetime.datetime.utcnow() - dt).total_seconds())
                is_active = (min(diff_local, diff_utc) <= self.ttl_seconds)
            except Exception:
                is_active = False

        loaded_turns = []
        for t in db_turns:
            ct = ConversationTurn(
                user_query=t.get("user_query", ""),
                rewritten_query=t.get("rewritten_query", ""),
                spoken_summary=t.get("spoken_summary", ""),
                detailed_markdown=t.get("detailed_markdown", ""),
                focal_topic=t.get("focal_topic", ""),
                slice_ids=t.get("slice_ids", [])
            )
            loaded_turns.append(ct)

        if is_active:
            self.turns = loaded_turns[-self.max_turns:]
            self.last_active_time = time.time()
            print(f"[SessionManager] 历史会话 {session_id} 处于有效 TTL 内，已激活 {len(self.turns)} 轮连续追问上下文。")
        else:
            self.turns = []
            self.last_active_time = 0.0
            print(f"[SessionManager] 历史会话 {session_id} 已过期 (> {self.ttl_seconds}s)，仅作为只读归档展示，不继承上下文。")
        return loaded_turns

    def get_valid_history(self) -> List[ConversationTurn]:
        """获取未超时的有效会话历史"""
        if not self.turns:
            return []
        # 超时检测 (默认 10 分钟无交互自动遗忘)
        if time.time() - self.last_active_time > self.ttl_seconds:
            self.clear()
            return []
        return list(self.turns)

    def get_last_turn(self) -> Optional[ConversationTurn]:
        """获取上一轮问答详情"""
        history = self.get_valid_history()
        return history[-1] if history else None

    def get_cached_slice_ids(self) -> List[str]:
        """合并收集历史会话已命中的切片 ID 列表"""
        history = self.get_valid_history()
        ids = []
        for turn in history:
            for sid in turn.slice_ids:
                if sid not in ids:
                    ids.append(sid)
        return ids

    def clear(self):
        """主动清空会话历史 (开启新话题)"""
        self.turns.clear()
        self.last_active_time = 0.0

    def is_active(self) -> bool:
        """检测当前是否存在有效未过期的前序上下文"""
        return len(self.get_valid_history()) > 0
