import datetime
import re
import time
from typing import Dict, Any, List, Optional, Callable
from config import Config
from core.knowledge_engine import MeetingStore
from core.entity_dict import get_entity_context_prompt
from core.query_rewriter import QueryRewriter
from core.session_manager import SessionManager, ConversationTurn
from core.instruction_handler import InstructionHandler

QA_SYSTEM_PROMPT = """你是一个常驻企业桌面会议记忆助理 DeskEcho。
你所服务的企业组织是【未来智能】。
以下是公司核心成员真实组织架构档案与职责背景（请以此作为权威人员基准，自动对齐会议录音中的常见同音字或口语简称）：

{entity_context}

--------------------
回答原则：
1. 【音视分离架构】：
   - 用户主要是通过语音对讲（耳朵听 + 眼睛看屏幕）。
   - **TTS 语音播报必须极其精炼、干脆利落**！原则上只说 1~2 句话（35~50字以内），直奔答案人名、时间或核心决议，杜绝长篇大论和念诵时间戳；遇到复杂逻辑仅做最简短的核心概括。
   - **屏幕视觉展示必须详实严密**，包含具体时间段、表格、会议原始对话佐证，供用户抬眼查阅。
2. 【多轮追问与释义深化支持】：
   - 若用户表示“没太懂/详细解释下/举个例子/为什么”：
     * 语音结论播报使用**生活化、通俗生动的比喻**，一语点破本质；
     * 屏幕详细说明展开技术原语、具体会议讨论争论细节及量化指标，绝不重复上一轮的表面套话。
3. 【切片相关性核对与双轨自适应输出】：
   请仔细核对下方的【参考会议记忆片段】是否与【用户提问】真正相关：
   
   ▶ 轨道 A：【会议有记录】（参考片段中确实讨论了该议题）：
     - 严格基于内部会议记录与组织档案回答，绝不捏造；
     - 输出结构：
       > **结论播报**：[用1~2句极简、口语化的自然句子直接给出结论]
       
       ### 详细说明与溯源依据
       [在此展开详细的背景、具体会议时间点（如 2026-10-28 14:00）、发言人、各切片佐证与逻辑推导]

   ▶ 轨道 B：【会议无记录 / 外部通用问题】（参考片段中完全未涉及用户所问主题，如询问全网常识、外部知名公司、日常科技知识、通用概念等）：
     - 自动触发全网通用知识拓展，切勿生硬拒绝，而是礼貌说明会议无记录并给出客观科普；
     - 输出结构：
       > **结论播报**：会议暂无记录。全网常识显示：[用1句话直接给出通用常识核心要点]

       > **全网通用知识解答**：过往内部会议中未检索到相关讨论，以下内容基于通用 AI 知识推导，非企业内部决策依据。

       ### 详细说明与科普
       [在此条理清晰地展开 2~3 个维度的通用科普介绍，使用 Markdown 排版，重点加粗]
"""

QA_USER_PROMPT = """{dialogue_context}【参考会议记忆片段】：
{context}

【用户提问】：
{query}

{strategy_hint}请仔细核对上述会议记忆片段与组织架构背景，给出带极简播报与详尽溯源的解答：
"""

GENERAL_FALLBACK_SYSTEM_PROMPT = """你是一个常驻企业桌面会议记忆助理 DeskEcho。
当前用户提出的问题在企业过往的会议记忆知识库中【完全未检索到任何讨论记录】。
系统现已触发【全网通用常识拓展模式（General Knowledge Fallback）】。

回答原则：
1. 【音视分离架构】：
   - **TTS 语音播报（结论播报）**：必须开门见山声明“会议暂无记录”，然后用 1~2 句话直接给出通用常识核心要点（35~50字），供语音播放。
     示例：“会议暂无记录。全网常识显示：谷歌是一家全球领先的科技巨头，核心业务涵盖搜索引擎、Android 系统与云计算。”
   - **屏幕视觉展示**：包含一段标准紫色卡片声明，随后条理分明地展开详细知识、背景科普或操作指引。
2. 【严格输出格式规范】：
   必须严格按照以下格式输出：

> **结论播报**：会议暂无记录。[紧接着用1句话概括全网通识核心答案]

> **全网通用知识解答**：过往内部会议中未检索到相关讨论，以下内容基于通用 AI 知识推导，非企业内部决策依据。

### 详细说明与科普
[在此条理清晰地展开 2~3 个维度的详细介绍，使用 Markdown 排版，重点加粗]
"""

GENERAL_FALLBACK_USER_PROMPT = """{dialogue_context}【用户提问】：
{query}

请基于全网通用知识为用户提供客观、详实的常识解答（请严格遵照音视分离与双引言格式）：
"""

class RAGEngine:
    def __init__(self, meeting_store: MeetingStore):
        self.store = meeting_store
        self.api_key = Config.OPENAI_API_KEY or Config.DASHSCOPE_API_KEY
        self.base_url = Config.OPENAI_BASE_URL
        self.model = Config.LLM_MODEL
        self.client = None
        self.rewriter = QueryRewriter()
        self.instruction_handler = InstructionHandler()
        self.session_manager = SessionManager(store=self.store, ttl_seconds=600.0, max_turns=3)
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

    def reset_session(self):
        """主动清空会话上下文 (开启新对话)"""
        self.session_manager.start_new_session()
        print("[RAGEngine] 会话上下文已清空，开启全新独立话题。")

    def load_session(self, session_id: str):
        """加载历史会话并激活上下文"""
        return self.session_manager.load_session(session_id)

    def answer_query(self, query: str, on_progress: Optional[Callable[[str, str], None]] = None) -> Dict[str, Any]:
        """
        基于多轮上下文感知与 Query Rewriting 的混合检索推导
        """
        # 0. 敏捷自进化指令拦截 (如以 "改进一下/提个需求" 开头，不污染会议知识库，直通工单入库)
        if self.instruction_handler.is_instruction(query):
            if on_progress:
                on_progress("评估改进指令", "检测到软件改进指令，架构师角色正在拆解方案并立项...")
            return self.instruction_handler.handle_instruction(query)

        # 1. 获取有效前序历史
        history = self.session_manager.get_valid_history()
        has_history = bool(history and len(history) > 0)

        # 2. 口语语义改写与多轮意图规范化
        if on_progress:
            if has_history:
                on_progress("上下文意图解析", f"正在结合前序 {len(history)} 轮对话消解指代与重塑检索句...")
            else:
                on_progress("意图语义解析", "正在解析口语意图，去除口癖并对齐企业组织架构实体...")

        rewrite_result = self.rewriter.rewrite_and_normalize(query, history=history)
        search_query = rewrite_result["search_query"]
        expanded_keywords = rewrite_result["keywords"]
        target_entity = rewrite_result.get("target_entity", "无")
        time_intent = rewrite_result.get("time_intent", "无")
        action_type = rewrite_result.get("action_type", "NEW")
        focal_topic = rewrite_result.get("focal_topic", "")
        clarification_guide = rewrite_result.get("clarification_guide", "")
        is_followup = rewrite_result.get("is_followup", has_history)

        entity_hint = f"（定位实体：{target_entity}）" if target_entity != "无" else ""
        topic_hint = f" [话题: {focal_topic}]" if focal_topic else ""
        if on_progress:
            on_progress("检索会议记忆", f"正在检索【{search_query[:25]}】{entity_hint}{topic_hint}...")

        # 3. 多策略切片检索
        context_parts = []
        seen_ids = set()

        # A. 如果是 DEEPEN 释义深化模式，把前序命中切片无损继承
        if action_type == "DEEPEN":
            cached_ids = self.session_manager.get_cached_slice_ids()
            if cached_ids:
                cached_records = self.store.get_records_by_ids(cached_ids)
                for rec in cached_records:
                    if rec["id"] not in seen_ids:
                        seen_ids.add(rec["id"])
                        part = f"【前序命中核心切片 - 时间段】: {rec['start_time']} 至 {rec['end_time']}\n【结构化纪要】:\n{rec['summary']}\n【原始对话】:\n{rec['raw_text']}"
                        context_parts.append(part)

        # B. 向量语义检索
        vector_results = self.store.query_vector(search_query, n_results=6)
        for item in vector_results:
            sid = item.get("slice_id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                context_parts.append(item["content"])

        # C. SQLite 关键词加权检索
        combined_text = f"{search_query} {' '.join(expanded_keywords[:4])}"
        keyword_results = self.store.query_keyword(combined_text, limit=6)
        for rec in keyword_results:
            sid = rec.get("id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                part = f"【时间段】: {rec['start_time']} 至 {rec['end_time']}\n【结构化纪要】:\n{rec['summary']}\n【原始对话】:\n{rec['raw_text']}"
                context_parts.append(part)

        # D. 时间意图检索
        recent_records = []
        lower_q = query.lower()
        if time_intent in ("今天", "昨天", "站会") or any(w in lower_q for w in ["今天", "刚才", "最近", "上次", "昨天", "上一场", "站会"]):
            recent_records = self.store.query_recent(limit=3)
            for rec in recent_records:
                sid = rec.get("id")
                if sid and sid not in seen_ids:
                    seen_ids.add(sid)
                    part = f"【时间段】: {rec['start_time']} 至 {rec['end_time']}\n【结构化纪要】:\n{rec['summary']}\n【原始对话】:\n{rec['raw_text']}"
                    context_parts.append(part)

        # 组装前序对话历史
        dialogue_context = ""
        if has_history:
            hist_parts = []
            for t_idx, turn in enumerate(history[-2:], 1):
                hist_parts.append(f"轮次 {t_idx}：\n提问：{turn.user_query}\n回答要点：{turn.spoken_summary}")
            dialogue_context = f"【前序问答交互脉络】：\n" + "\n\n".join(hist_parts) + "\n\n--------------------\n\n"

        if not context_parts:
            if on_progress:
                on_progress("全网通识拓展", "会议库未命中该议题，已自动切换至全网通用知识解答...")
            
            answer, spoken_text = self._generate_general_fallback(query, dialogue_context=dialogue_context)
            turn = ConversationTurn(
                user_query=query,
                rewritten_query=search_query,
                spoken_summary=spoken_text,
                detailed_markdown=answer,
                focal_topic=focal_topic,
                slice_ids=[]
            )
            self.session_manager.add_turn(turn)
            return {
                "answer": answer,
                "spoken_text": spoken_text,
                "sources": [],
                "is_followup": is_followup,
                "action_type": action_type,
                "focal_topic": focal_topic,
                "response_mode": "GENERAL"
            }

        matched_count = len(seen_ids)
        if on_progress:
            on_progress("提炼溯源结论", f"已定位到 {matched_count} 处相关会议记录，正在由 DeepSeek 生成解答...")

        context_str = "\n\n--------------------\n\n".join(context_parts)

        # 4. 组装多轮对话脉络与针对性引导
        dialogue_context = ""
        if has_history:
            hist_parts = []
            for t_idx, turn in enumerate(history[-2:], 1):
                hist_parts.append(f"轮次 {t_idx}：\n提问：{turn.user_query}\n回答要点：{turn.spoken_summary}")
            dialogue_context = f"【前序问答交互脉络】：\n" + "\n\n".join(hist_parts) + "\n\n--------------------\n\n"

        strategy_hint = ""
        if action_type == "DEEPEN":
            strategy_hint = "【追问生成策略】：提问者对上一轮回答表示“未完全理解/需要详细解释/举例”。请调整风格：语音播报使用通俗生动的比喻直击本质，屏幕端详细展开会议原话与具体技术细节，切忌重复上一轮的表面概括。\n\n"
        elif action_type == "PIVOT":
            strategy_hint = f"【顺藤摸瓜引申策略】：提问者顺着上文主题“{focal_topic}”追问新属性，请重点回答新增维度的结论。\n\n"

        # 5. LLM 深度生成
        answer = ""
        spoken_text = ""
        if self.client:
            try:
                sys_prompt = QA_SYSTEM_PROMPT.format(entity_context=self.entity_context)
                user_prompt = QA_USER_PROMPT.format(
                    dialogue_context=dialogue_context,
                    context=context_str,
                    query=query,
                    strategy_hint=strategy_hint
                )

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.25
                )
                answer = response.choices[0].message.content.strip()
                spoken_text = self._extract_spoken_text(answer)
            except Exception as e:
                print(f"[RAGEngine] LLM 生成回答失败: {e}")

        if not answer:
            first_doc = context_parts[0] if context_parts else ""
            answer = f"> **结论播报**：已为您匹配到相关会议片段，请查看屏幕卡片。\n\n### 详细说明与溯源依据\n{first_doc[:300]}..."
            spoken_text = "已为您匹配到相关会议片段，请查看屏幕卡片。"

        # 判定最终返回模式：MEETING 还是 GENERAL
        if "> **全网通用知识解答**" in answer or "会议暂无记录" in spoken_text:
            response_mode = "GENERAL"
        else:
            response_mode = "MEETING"

        # 6. 保存本轮会话记录
        new_turn = ConversationTurn(
            user_query=query,
            rewritten_query=search_query,
            spoken_summary=spoken_text,
            detailed_markdown=answer,
            focal_topic=focal_topic,
            slice_ids=list(seen_ids) if response_mode == "MEETING" else []
        )
        self.session_manager.add_turn(new_turn)

        return {
            "answer": answer,
            "spoken_text": spoken_text,
            "sources": list(seen_ids) if response_mode == "MEETING" else [],
            "rewrite_info": rewrite_result,
            "is_followup": is_followup,
            "action_type": action_type,
            "focal_topic": focal_topic,
            "response_mode": response_mode,
            "turn_count": len(self.session_manager.turns)
        }

    def _generate_general_fallback(self, query: str, dialogue_context: str = "") -> tuple:
        """当内部会议库 0 匹配时，直接触发大模型全网通用知识解答"""
        if not self.client:
            default_txt = "过往会议记录中暂未找到相关信息。"
            ans = f"> **结论播报**：{default_txt}\n\n> **全网通用知识解答**：过往内部会议中未检索到相关讨论，当前未配置大模型密钥，无法推导演绎。\n\n### 详细说明\n知识库未命中该议题。"
            return ans, default_txt

        try:
            sys_prompt = GENERAL_FALLBACK_SYSTEM_PROMPT
            user_prompt = GENERAL_FALLBACK_USER_PROMPT.format(
                dialogue_context=dialogue_context,
                query=query
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            answer = response.choices[0].message.content.strip()
            spoken_text = self._extract_spoken_text(answer)
            return answer, spoken_text
        except Exception as e:
            print(f"[RAGEngine] 全网通识推导异常: {e}")
            default_txt = "会议暂无记录，外部大模型推导异常。"
            ans = f"> **结论播报**：{default_txt}\n\n> **全网通用知识解答**：过往内部会议未命中此话题，通用接口访问受阻。"
            return ans, default_txt

    def _extract_spoken_text(self, markdown_answer: str) -> str:
        """从大模型输出中智能提取专门用于 TTS 极简朗读的结论句子"""
        match = re.search(r'>\s*🎙️?\s*\**结论播报\**[：:]\s*(.+?)(?:\n\n|\n#|$)', markdown_answer, re.DOTALL)
        if match:
            spoken = match.group(1).strip()
            spoken = re.sub(r'[\*#_`~>|-]', '', spoken).strip()
            return spoken

        first_paragraph = markdown_answer.split("\n\n")[0].strip()
        first_paragraph = re.sub(r'[\*#_`~>|-]', '', first_paragraph).strip()
        if len(first_paragraph) <= 80:
            return first_paragraph

        return first_paragraph[:60] + "，详细佐证请查看屏幕。"
