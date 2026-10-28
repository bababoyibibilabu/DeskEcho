import datetime
import re
from typing import Dict, Any, List, Optional, Callable
from config import Config
from core.knowledge_engine import MeetingStore
from core.entity_dict import get_entity_context_prompt
from core.query_rewriter import QueryRewriter

QA_SYSTEM_PROMPT = """你是一个常驻企业桌面会议记忆助理 DeskEcho。
你所服务的企业组织是【美好智能】。
以下是公司核心成员真实组织架构档案与职责背景（请以此作为权威人员基准，自动对齐会议录音中的常见同音字或口语简称）：

{entity_context}

--------------------
回答原则：
1. 【音视分离架构】：
   - 用户主要是通过语音对讲（耳朵听 + 眼睛看屏幕）。
   - **TTS 语音播报必须极其精炼、干脆利落**！原则上只说 1~2 句话（30~50字以内），直奔答案人名、时间或核心决议，杜绝长篇大论和念诵时间戳；遇到复杂逻辑仅做最简短的核心概括。
   - **屏幕视觉展示必须详实严密**，包含具体时间段、表格、会议原始对话佐证，供用户抬眼查阅。
2. 【严格输出格式规范】：
   请严格按照以下两段式结构输出：

> 🎙️ **结论播报**：[用1~2句极简、口语化的自然句子直接给出结论，专供耳机/喇叭语音播报，不要带时间戳和冗余客套话]

### 详细说明与溯源依据
[在此展开详细的背景、具体会议时间点（如 2026-10-25 09:30）、各切片佐证与逻辑推导，供屏幕阅读]

3. 【实事求是】：若会议与组织档案均无依据，结论播报直接说：“过往会议记录中暂未找到相关信息”，绝不捏造。
"""

QA_USER_PROMPT = """【参考会议记忆片段】：
{context}

【用户提问】：
{query}

请基于上述会议记忆片段与组织架构背景，给出带极简播报与详尽溯源的解答：
"""

class RAGEngine:
    def __init__(self, meeting_store: MeetingStore):
        self.store = meeting_store
        self.api_key = Config.OPENAI_API_KEY or Config.DASHSCOPE_API_KEY
        self.base_url = Config.OPENAI_BASE_URL
        self.model = Config.LLM_MODEL
        self.client = None
        self.rewriter = QueryRewriter()
        self.entity_context = get_entity_context_prompt()
        
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except Exception as e:
                print(f"[RAGEngine] 初始化 OpenAI Client 失败: {e}")

    def answer_query(self, query: str, on_progress: Optional[Callable[[str, str], None]] = None) -> Dict[str, Any]:
        """
        基于 Query Rewriting 与音视分离架构（极简语音播报 + 详尽屏幕溯源）
        """
        # 1. 口语语义改写与意图规范化
        if on_progress:
            on_progress("意图语义解析", "🧠 正在解析口语意图，去除口癖并对齐企业组织架构实体...")

        rewrite_result = self.rewriter.rewrite_and_normalize(query)
        search_query = rewrite_result["search_query"]
        expanded_keywords = rewrite_result["keywords"]
        target_entity = rewrite_result.get("target_entity", "无")
        time_intent = rewrite_result.get("time_intent", "无")

        entity_hint = f"（定位实体：{target_entity}）" if target_entity != "无" else ""
        if on_progress:
            on_progress("检索会议记忆", f"🔍 正在检索【{search_query[:25]}】{entity_hint}...")

        # 2. 向量语义检索
        vector_results = self.store.query_vector(search_query, n_results=6)
        
        # 3. SQLite 精准关键词加权检索
        combined_text = f"{query} {' '.join(expanded_keywords[:4])}"
        keyword_results = self.store.query_keyword(combined_text, limit=6)

        # 4. 时间意图过滤或补充
        recent_records = []
        lower_q = query.lower()
        if time_intent in ("今天", "昨天", "站会") or any(w in lower_q for w in ["今天", "刚才", "最近", "上次", "昨天", "上一场", "站会"]):
            recent_records = self.store.query_recent(limit=3)

        # 5. 上下文组合与去重
        context_parts = []
        seen_ids = set()

        for rec in keyword_results:
            sid = rec.get("id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                part = f"【时间段】: {rec['start_time']} 至 {rec['end_time']}\n【结构化纪要】:\n{rec['summary']}\n【原始对话】:\n{rec['raw_text']}"
                context_parts.append(part)

        for item in vector_results:
            sid = item.get("slice_id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                context_parts.append(item["content"])

        for rec in recent_records:
            sid = rec.get("id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                part = f"【时间段】: {rec['start_time']} 至 {rec['end_time']}\n【结构化纪要】:\n{rec['summary']}\n【原始对话】:\n{rec['raw_text']}"
                context_parts.append(part)

        if not context_parts:
            default_reject = "过往会议记录中暂未找到相关信息。"
            return {
                "answer": f"> 🎙️ **结论播报**：{default_reject}\n\n### 详细说明与溯源依据\n当前会议知识库中未检索到与此相关的讨论片段。",
                "spoken_text": default_reject,
                "sources": []
            }

        matched_count = len(seen_ids)
        if on_progress:
            on_progress("提炼溯源结论", f"📚 已定位到 {matched_count} 处相关会议记录，正在由 DeepSeek 生成解答...")

        context_str = "\n\n--------------------\n\n".join(context_parts)

        # 6. LLM 深度生成带音视分离格式的解答
        if self.client:
            try:
                sys_prompt = QA_SYSTEM_PROMPT.format(entity_context=self.entity_context)
                user_prompt = QA_USER_PROMPT.format(context=context_str, query=query)

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                answer = response.choices[0].message.content.strip()
                
                # 提取专门供 TTS 朗读的极简播报文本
                spoken_text = self._extract_spoken_text(answer)

                return {
                    "answer": answer,
                    "spoken_text": spoken_text,
                    "sources": list(seen_ids),
                    "rewrite_info": rewrite_result
                }
            except Exception as e:
                print(f"[RAGEngine] LLM 生成回答失败: {e}")

        # 降级展示
        first_doc = context_parts[0] if context_parts else ""
        fallback_ans = f"> 🎙️ **结论播报**：已为您匹配到相关会议片段，请查看屏幕卡片。\n\n### 详细说明与溯源依据\n{first_doc[:300]}..."
        return {
            "answer": fallback_ans,
            "spoken_text": "已为您匹配到相关会议片段，请查看屏幕卡片。",
            "sources": list(seen_ids),
            "rewrite_info": rewrite_result
        }

    def _extract_spoken_text(self, markdown_answer: str) -> str:
        """
        从大模型输出中智能提取专门用于 TTS 极简朗读的结论句子
        """
        # 1. 优先提取 > 🎙️ **结论播报**：后面的内容
        match = re.search(r'>\s*🎙️?\s*\**结论播报\**[：:]\s*(.+?)(?:\n\n|\n#|$)', markdown_answer, re.DOTALL)
        if match:
            spoken = match.group(1).strip()
            # 移除 markdown 链接与多余星号
            spoken = re.sub(r'[\*#_`~>|-]', '', spoken).strip()
            return spoken

        # 2. 备选：提取第一段且不超过 60 字
        first_paragraph = markdown_answer.split("\n\n")[0].strip()
        first_paragraph = re.sub(r'[\*#_`~>|-]', '', first_paragraph).strip()
        if len(first_paragraph) <= 80:
            return first_paragraph

        # 3. 截取前 60 字
        return first_paragraph[:60] + "，详细佐证请查看屏幕。"
