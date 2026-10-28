import re
import json
import time
from typing import Dict, Any, List, Optional
from config import Config
from core.entity_dict import EMPLOYEES, COMPANY_INFO

REWRITE_SYSTEM_PROMPT = """你是一个专业的企业语音对讲意图解析与查询改写引擎（Query Rewriter & Normalizer）。
你所服务的公司业务涵盖：AI智能助手 (DeskEcho)、企业级常驻会议记忆中台、自适应知识图谱、智能终端交互。

任务目标：
将用户在办公室用快捷键对讲时录入的【口语化、倒装、口癖多、使用简称或同音别名】的提问，改写为适合在会议知识库中检索的高信息密度【书面规范化检索式】和【核心实体关键词】。

规则：
1. 【去噪规范化】：去除“哎那个”、“咋整的”、“自个儿搞”、“提了一嘴”等口头禅，理顺倒装句。
2. 【提取核心检索句与实体】：去除虚词，提取高信息密度检索词。

请严格输出 JSON 格式（不要包含任何 markdown 代码块外部文本）：
{
  "search_query": "规范化后的精炼书面检索句",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "target_entity": "提问涉及的人员姓名或项目名（无则填无）",
  "time_intent": "今天/昨天/站会/无",
  "focal_topic": "提问的核心主题或算法名词"
}
"""

MULTI_TURN_REWRITE_SYSTEM_PROMPT = """你是一个专业的企业语音对讲意图解析与多轮追问改写引擎。
你所服务的公司业务涵盖：AI智能助手 (DeskEcho)、企业常驻会议记忆中台、自适应知识图谱。

任务目标：
用户正在进行【多轮对讲交互】。你需要结合【前序对话脉络】，对用户的最新输入进行深度指代消解与检索式重塑。

规则：
1. 【判定追问类型与动作 (action_type)】：
   - DEEPEN (深化释义与举例)：用户表示“没太懂”、“详细解释”、“为什么是这个数字/模型”、“能举个例子吗”、“细说一下”，或者询问具体公式/算法/论据。
   - PIVOT (顺藤摸瓜引申属性)：用户顺着上文实体追问新维度，如“那这个谁负责”、“上次会上批了多少钱”、“什么时候交付上线”、“李工怎么说的”。
   - NEW (独立新话题)：用户提问与上文毫无关联（例如上文在聊掌握度算法，最新突然问“下午几点开会”）。
2. 【指代消解与全量补全】：
   - 提取上文的关键实体、项目或算法名词，将最新提问补齐为一个【具备独立完整语义、可直接用于向量数据库检索的高质量书面句】。
   - 严禁将代词（“他/这个/那件事/那个东西”）保留在 search_query 中，必须替换为具体真实名称。
3. 【输出规范】：
   请严格输出纯 JSON 格式：
   {
     "is_followup": true/false,
     "action_type": "DEEPEN" | "PIVOT" | "NEW",
     "search_query": "补全代词与上下文后的独立检索句",
     "keywords": ["关键词1", "关键词2", "关键词3"],
     "target_entity": "涉及的人名或项目名（无则填无）",
     "time_intent": "今天/昨天/站会/无",
     "focal_topic": "当前聚焦的核心议题或项目名",
     "clarification_guide": "若属于 DEEPEN，给大模型回答生成器的简要指导（例如：用通俗比喻解释算法原理并展开会议原话细节）"
   }
"""

class QueryRewriter:
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.base_url = Config.OPENAI_BASE_URL
        self.model = Config.LLM_MODEL
        self.client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except Exception as e:
                print(f"[QueryRewriter] 初始化 OpenAI Client 失败: {e}")

    def rewrite_and_normalize(self, raw_query: str, history: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        多轮与单轮双层重塑流水线：
        1. 本地快速实体识别与词典增强 (0ms 基础兜底)
        2. 大模型上下文感知深度意图蒸馏与查询重写
        """
        has_history = bool(history and len(history) > 0)
        tier1_res = self._local_fast_normalize(raw_query, history=history)

        if not self.client:
            return tier1_res

        try:
            start_t = time.time()
            if has_history:
                # 构造前序对话历史摘要
                history_lines = []
                for idx, turn in enumerate(history[-2:], 1):
                    q = getattr(turn, "user_query", "")
                    a = getattr(turn, "spoken_summary", "") or getattr(turn, "detailed_markdown", "")[:120]
                    topic = getattr(turn, "focal_topic", "")
                    topic_str = f" [核心主题: {topic}]" if topic else ""
                    history_lines.append(f"- 轮次 {idx}{topic_str}：提问“{q}” ➔ 结论要点“{a}”")
                history_context_str = "\n".join(history_lines)

                prompt_user = (
                    f"【前序对话脉络】：\n{history_context_str}\n\n"
                    f"【用户最新对讲输入】：\n“{raw_query}”"
                )
                system_prompt = MULTI_TURN_REWRITE_SYSTEM_PROMPT
            else:
                prompt_user = f"用户口语对讲提问：“{raw_query}”"
                system_prompt = REWRITE_SYSTEM_PROMPT

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_user}
                ],
                temperature=0.1,
                max_tokens=220
            )
            cost = time.time() - start_t
            content = response.choices[0].message.content.strip()

            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            parsed = json.loads(content)
            merged_keywords = list(dict.fromkeys(parsed.get("keywords", []) + tier1_res["keywords"]))

            result = {
                "original_query": raw_query,
                "is_followup": parsed.get("is_followup", has_history),
                "action_type": parsed.get("action_type", "DEEPEN" if has_history else "NEW"),
                "search_query": parsed.get("search_query", tier1_res["search_query"]),
                "keywords": merged_keywords,
                "target_entity": parsed.get("target_entity", tier1_res["target_entity"]),
                "time_intent": parsed.get("time_intent", tier1_res["time_intent"]),
                "focal_topic": parsed.get("focal_topic", tier1_res.get("focal_topic", "")),
                "clarification_guide": parsed.get("clarification_guide", ""),
                "cost_time": cost
            }
            action_tag = f" [{result['action_type']}]" if has_history else ""
            print(f"[QueryRewriter]{action_tag} 改写完成 ({cost:.2f}s): “{raw_query}” ➔ “{result['search_query']}” | 话题: {result['focal_topic']} | 关键词: {result['keywords'][:5]}")
            return result
        except Exception as e:
            print(f"[QueryRewriter] 大模型重写异常，平滑降级到本地规则: {e}")
            return tier1_res

    def _local_fast_normalize(self, raw_query: str, history: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        本地极速规范化与前序上下文继承 (0ms 兜底保障)
        """
        keywords = set()
        matched_entity = "无"
        time_intent = "无"
        focal_topic = ""
        action_type = "NEW"
        is_followup = False

        # 检测是否包含追问/深化关键词
        followup_signals = ["没懂", "没太懂", "不懂", "详细", "细说", "解释", "例子", "为什么", "谁负责", "啥意思", "怎么说", "然后再呢"]
        if history and any(sig in raw_query for sig in followup_signals):
            is_followup = True
            action_type = "DEEPEN"
            last_turn = history[-1]
            last_topic = getattr(last_turn, "focal_topic", "") or getattr(last_turn, "user_query", "")
            focal_topic = last_topic
            search_query = f"详细解释说明 {last_topic} {raw_query}"
            keywords.add(last_topic)
        else:
            search_query = raw_query

        # 实体识别
        for emp in EMPLOYEES:
            if emp["name"] in raw_query:
                matched_entity = emp["name"]
                keywords.add(emp["name"])
                keywords.add(emp["title"])
                break
            for a in emp["aliases"]:
                if a in raw_query:
                    matched_entity = emp["name"]
                    keywords.add(emp["name"])
                    break

        if any(w in raw_query for w in ["今天", "刚才", "现在"]):
            time_intent = "今天"
        elif any(w in raw_query for w in ["昨天", "上次", "之前"]):
            time_intent = "昨天"

        # 补充通用分词
        tokens = re.findall(r'[\u4e00-\u9fa5]{2,6}|[a-zA-Z0-9_]{2,}', raw_query)
        for t in tokens:
            if len(t) >= 2 and t not in ["怎么", "什么", "这个", "那个", "那个谁", "解释", "一下"]:
                keywords.add(t)

        return {
            "original_query": raw_query,
            "is_followup": is_followup,
            "action_type": action_type,
            "search_query": search_query,
            "keywords": list(keywords)[:6],
            "target_entity": matched_entity,
            "time_intent": time_intent,
            "focal_topic": focal_topic or matched_entity,
            "clarification_guide": "通俗生动类比，展开会议具体讨论论据" if is_followup else "",
            "cost_time": 0.0
        }
