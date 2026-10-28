import re
import json
import time
from typing import Dict, Any, List, Optional
from config import Config
from core.entity_dict import EMPLOYEES, COMPANY_INFO

REWRITE_SYSTEM_PROMPT = """你是一个专业的企业语音对讲意图解析与查询改写引擎（Query Rewriter & Normalizer）。
你所服务的公司是【美好智能】（核心项目包括：巨升机器人、K12学习平板、英语AI课/RAZ绘本翻拍、自适应知识图谱）。

任务目标：
将用户在办公室用快捷键对讲时录入的【口语化、倒装、口癖多、使用简称或同音别名】的提问，改写为适合在会议知识库中检索的高信息密度【书面规范化检索式】和【核心实体关键词】。

规则：
1. 【去噪规范化】：去除“哎那个”、“咋整的”、“自个儿搞”、“提了一嘴”等口头禅，理顺倒装句。
2. 【企业实体映射】：
   - “老成 / 成哥 / 远哥 / 成远” -> 真实姓名“程远”（产品经理，技术协调，Python，教培）
   - “李阳” -> 真实姓名“李洋”（产品UI/UE，设计，logo）
   - “张文佳” -> 真实姓名“张文嘉”（行政文员，课程结构化）
   - “郎琪 / 春骚” -> 真实姓名“郎琦”（Android开发，全栈，AI落地，工作流）
   - “董事长 / 老板 / 吕总” -> 真实姓名“吕明秋”（董事长，战略上市）
   - “杨总 / 杨建新” -> 真实姓名“杨年新”（总经理，业务高管）
   - “思豪” -> 真实姓名“陈思豪”（机器人后端）
   - “荣硕” -> 真实姓名“荣硕”（机器人Android原生）
   - “佳彤” -> 真实姓名“陈佳彤”（行政人事办公室）
3. 【业务术语扩展】：
   - “英语课/绘本/自个儿编” -> 补充“英语AI课, 翻拍, 纸质绘本, RAZ”
   - “图截得不行/不干净” -> 补充“AI截图, 边缘无关内容, 题目审核积压”
   - “多出来的本子/多出来的” -> 补充“25本, 28本, 日站会”

请严格输出 JSON 格式（不要包含任何 markdown 代码块外部文本）：
{{
  "search_query": "规范化后的精炼书面检索句",
  "keywords": ["关键词1", "关键词2", "关键词3", "关键词4"],
  "target_entity": "提问涉及的人员姓名或项目名（无则填无）",
  "time_intent": "今天/昨天/站会/无"
}}
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

    def rewrite_and_normalize(self, raw_query: str) -> Dict[str, Any]:
        """
        双层流水线：
        1. 本地快速实体识别与词典增强 (0ms 基础兜底)
        2. 大模型深度意图蒸馏与查询改写 (DeepSeek 高阶语义重塑)
        """
        # 基础本地规则抽取 (Tier 1)
        tier1_res = self._local_fast_normalize(raw_query)

        # 若未配置大模型或网络不可用，直接返回 Tier 1 结果
        if not self.client:
            return tier1_res

        # 大模型深度改写 (Tier 2)
        try:
            start_t = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"用户口语对讲提问：“{raw_query}”"}
                ],
                temperature=0.1,
                max_tokens=150
            )
            cost = time.time() - start_t
            content = response.choices[0].message.content.strip()

            # 清理可能的 markdown 代码块标记
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            parsed = json.loads(content)
            
            # 合并 Tier 1 与 Tier 2 关键词（去重）
            merged_keywords = list(dict.fromkeys(parsed.get("keywords", []) + tier1_res["keywords"]))

            result = {
                "original_query": raw_query,
                "search_query": parsed.get("search_query", tier1_res["search_query"]),
                "keywords": merged_keywords,
                "target_entity": parsed.get("target_entity", tier1_res["target_entity"]),
                "time_intent": parsed.get("time_intent", tier1_res["time_intent"]),
                "cost_time": cost
            }
            print(f"[QueryRewriter] 改写完成 ({cost:.2f}s): “{raw_query}” -> “{result['search_query']}” | 实体: {result['target_entity']} | 关键词: {result['keywords'][:5]}")
            return result
        except Exception as e:
            print(f"[QueryRewriter] 大模型改写异常，平滑降级到本地规则: {e}")
            return tier1_res

    def _local_fast_normalize(self, raw_query: str) -> Dict[str, Any]:
        """
        基于本地组织实体字典的极速正则规范化 (0ms 兜底保障)
        """
        keywords = set()
        matched_entity = "无"
        time_intent = "无"

        lower_q = raw_query.lower()

        # 1. 人员与职务映射
        for emp in EMPLOYEES:
            if emp["name"] in raw_query:
                matched_entity = emp["name"]
                keywords.add(emp["name"])
                keywords.add(emp["title"])
                break
            for a in emp["aliases"]:
                if a in raw_query and len(a) >= 2:
                    matched_entity = emp["name"]
                    keywords.add(emp["name"])
                    keywords.add(emp["title"])
                    break

        # 2. 常见业务同义词
        synonyms = {
            "老成": ["程远", "Python", "技术协调", "产品经理"],
            "成哥": ["程远", "Python", "技术协调"],
            "远哥": ["程远", "产品经理"],
            "董事长": ["吕明秋", "战略决策"],
            "吕总": ["吕明秋", "董事长"],
            "杨总": ["杨年新", "总经理", "兜底"],
            "李阳": ["李洋", "UI设计", "Logo方案"],
            "海报": ["李洋", "UI/UE设计", "视觉设计", "Logo方案"],
            "设计": ["李洋", "UI/UE", "Logo方案"],
            "文佳": ["张文嘉", "课程结构化"],
            "文嘉": ["张文嘉", "课程结构化"],
            "结构化": ["张文嘉", "课程内容梳理"],
            "思豪": ["陈思豪", "机器人后端"],
            "春骚": ["陈思豪", "郎琦", "后端开发"],
            "荣硕": ["荣硕", "机器人Android原生"],
            "郎琪": ["郎琦", "全栈开发", "AI落地", "工作流"],
            "郎奇": ["郎琦", "全栈开发", "AI落地", "工作流"],
            "ai工作流": ["郎琦", "工作流支持"],
            "自个儿编": ["英语AI课", "翻拍", "RAZ"],
            "绘本": ["英语AI课", "绘本翻拍", "RAZ"],
            "翻拍": ["英语AI课", "海外教材翻拍"],
            "图截得": ["AI截图不干净", "边缘内容", "题目审核积压"],
            "多出来的": ["25本", "28本", "日站会"],
            "站会": ["项目日站会", "各模块进度", "卡点同步"]
        }

        for k, v in synonyms.items():
            if k in lower_q:
                for word in v:
                    keywords.add(word)

        if "昨天" in raw_query:
            time_intent = "昨天"
        elif "今天" in raw_query or "刚才" in raw_query:
            time_intent = "今天"
        elif "站会" in raw_query:
            time_intent = "站会"

        cleaned_query = re.sub(r'[哎那个就咋整的自个儿搞搞来着一嘴嘛呢吧呀啊]', '', raw_query).strip()
        search_query = f"{cleaned_query} {' '.join(list(keywords)[:3])}".strip()

        return {
            "original_query": raw_query,
            "search_query": search_query or raw_query,
            "keywords": list(keywords),
            "target_entity": matched_entity,
            "time_intent": time_intent,
            "cost_time": 0.0
        }
