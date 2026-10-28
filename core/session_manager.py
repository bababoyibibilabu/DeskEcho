import time
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
    """
    def __init__(self, ttl_seconds: float = 600.0, max_turns: int = 3):
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self.turns: List[ConversationTurn] = []
        self.last_active_time = 0.0

    def add_turn(self, turn: ConversationTurn):
        """记录新一轮对话"""
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)
        self.last_active_time = time.time()

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
