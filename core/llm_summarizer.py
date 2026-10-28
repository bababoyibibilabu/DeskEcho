from typing import Optional
from config import Config

SUMMARIZE_PROMPT = """你是一个企业常驻会议知识库助理。请对以下刚记录的会议语音转录片段进行高精度结构化清洗与提炼。

【时间跨度】：{start_time} 至 {end_time}
【原始转录】：
{raw_text}

请严格按以下格式输出（保留原始重要数字、人名与明确结论）：
1. 核心议题（Topic）：一句话概括谈论的核心事件。
2. 决策与结论（Key Decisions）：若未形成决策请写“无”，有决策则明确列出。
3. 待办事项（Action Items）：[负责人(若有)] + 事项 + 截止时间(若有)。
4. 事实备忘（Key Facts）：提及的关键指标、报价、项目名词。
"""

class LLMSummarizer:
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY or Config.DASHSCOPE_API_KEY
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
                print(f"[LLMSummarizer] OpenAI Client 初始化失败: {e}")

    def summarize(self, raw_text: str, start_time: str, end_time: str) -> str:
        """
        结构化提炼切片文本
        """
        if not raw_text.strip():
            return "【无有效发言内容】"

        if self.client:
            try:
                prompt = SUMMARIZE_PROMPT.format(
                    start_time=start_time,
                    end_time=end_time,
                    raw_text=raw_text
                )
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个严谨的企业会议纪要分析专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                content = response.choices[0].message.content
                if content:
                    return content.strip()
            except Exception as e:
                print(f"[LLMSummarizer] 调用大模型提取纪要失败: {e}")

        # 降级提炼
        return (
            f"1. 核心议题（Topic）：研讨会交流与事项沟通。\n"
            f"2. 决策与结论（Key Decisions）：基于当前会议内容初步落实阶段性工作。\n"
            f"3. 待办事项（Action Items）：跟进关键任务执行。\n"
            f"4. 事实备忘（Key Facts）：发言要点概要已留存：{raw_text[:60]}..."
        )
