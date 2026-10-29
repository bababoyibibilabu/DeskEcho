import os
import re
import json
import time
import uuid
import datetime
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from config import Config

INSTRUCTION_EVAL_PROMPT = """你是一个常驻企业桌面会议系统 DeskEcho 的首席软件架构师与全栈研发工程师。
当前操作员正处于【敏捷高频自进化模式】，通过语音对讲向你下达了【软件改进/交互优化/功能建议指令】。

【操作员原始语音指令】：
“{raw_instruction}”

任务目标：
请以极高专业度的技术视角评估该建议，拆解实现路径，并返回严格的 JSON 对象。

JSON 字段要求：
{{
  "task_title": "简明需求标题（12字以内，如：增加切片列表行间距）",
  "category": "UI/UX" | "ASR语音" | "LLM大模型" | "RAG知识库" | "系统稳定性" | "其他",
  "feasibility": "可行" | "需确认" | "建议调整",
  "requirement_summary": "操作员核心诉求的技术语言归纳（1~2句话）",
  "target_modules": ["可能需要改动的核心文件，如 ui/main_window.py, core/updater.py 等"],
  "execution_plan": "1~3步干脆利落的技术实施方案",
  "spoken_ack": "由架构师角色播报给操作员的简炼确认语（30~45字以内，干脆利落，告知已立项，将在稍后自动热更新生效）",
  "clarification_prompt": "如有疑问需确认的内容（无则填无）"
}}
"""

FALLBACK_TEMPLATES = {
  "UI/UX": "收到交互优化建议，已为您立项归档。工程师稍后将为您更新客户端界面。",
  "DEFAULT": "收到改进建议，已为您立项为敏捷工单。后台工程师稍后将为您自动编译更新。"
}

class InstructionHandler:
    """
    DeskEcho 敏捷自进化指令模式拦截与处理器
    通过特定前缀（如“改进一下/提个需求”）分流，实现操作员口语化建议的秒级立项、持久化存档与专属角色交互
    """
    # 触发词正则列表
    TRIGGER_PATTERN = re.compile(
        r'^\s*(?:请|能不能|帮我|麻烦)?\s*(改进一下|优化一下|提个需求|提个建议|改一下|加个功能|修改一下|软件改进|客户端改进|迭代一下)[\s,，:：]*(.*)',
        re.IGNORECASE | re.DOTALL
    )

    def __init__(self):
        self.enabled = Config.ENABLE_DEV_INSTRUCTION_MODE
        self.api_key = Config.OPENAI_API_KEY or Config.DASHSCOPE_API_KEY
        self.base_url = Config.OPENAI_BASE_URL
        self.model = Config.LLM_MODEL
        self.client = None
        self._lock = threading.Lock()
        self.queue_file = Config.DATA_DIR / "iteration_queue.json"

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except Exception as e:
                print(f"[InstructionHandler] 初始化 OpenAI Client 失败: {e}")

    def is_instruction(self, text: str) -> bool:
        """检查输入文本是否命中改进指令触发词"""
        if not self.enabled or not text:
            return False
        clean = text.strip()
        return bool(self.TRIGGER_PATTERN.match(clean))

    def parse_instruction(self, text: str) -> Tuple[str, str]:
        """解析指令前缀与具体内容，返回: (trigger_word, instruction_content)"""
        m = self.TRIGGER_PATTERN.match(text.strip())
        if m:
            return m.group(1), m.group(2).strip()
        return "", text.strip()

    def handle_instruction(self, query: str) -> Dict[str, Any]:
        """
        核心处理入口：
        1. 意图提炼与技术可行性评估 (LLM)
        2. 结构化敏捷任务工单落盘入库 (iteration_queue.json)
        3. 生成极具科技感的专属 Markdown 卡片与干脆利落的架构师 TTS 播报
        """
        trigger_word, raw_instruction = self.parse_instruction(query)
        if not raw_instruction:
            # 操作员只说了“改进一下”，未说具体内容
            spoken_ack = "已进入敏捷改进模式。请说出您期望优化的界面细节或功能需求。"
            answer_md = (
                "> **敏捷自进化指令模式已就绪**\n>\n"
                "> **状态提示**：检测到指令触发词，但未采集到具体内容。\n\n"
                "### 使用说明\n"
                "请长按【右 Alt】直接说出您的建议，例如：\n"
                "- “*改进一下：把或许没用列表项的高度增加一些*”\n"
                "- “*优化一下：首页搜索框的圆角调整得更加柔和*”\n"
                "- “*提个需求：希望在对讲结束后自动保持在当前切片*”\n"
            )
            return {
                "answer": answer_md,
                "spoken_text": spoken_ack,
                "response_mode": "INSTRUCTION",
                "is_instruction": True,
                "focal_topic": "敏捷指令引导",
                "is_followup": False
            }

        eval_res = self._evaluate_with_llm(raw_instruction)
        task_id = f"REQ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        task_record = {
            "id": task_id,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trigger_word": trigger_word,
            "raw_instruction": raw_instruction,
            "task_title": eval_res.get("task_title", "未命名改进建议"),
            "category": eval_res.get("category", "UI/UX"),
            "feasibility": eval_res.get("feasibility", "可行"),
            "requirement_summary": eval_res.get("requirement_summary", raw_instruction),
            "target_modules": eval_res.get("target_modules", []),
            "execution_plan": eval_res.get("execution_plan", "待评估"),
            "spoken_ack": eval_res.get("spoken_ack", "已为您立项。"),
            "clarification_prompt": eval_res.get("clarification_prompt", ""),
            "status": "PENDING"
        }

        # 任务持久化入库
        self._append_to_queue(task_record)

        # 规范化执行方案排版 (兼容 list 与 str)
        exec_plan = task_record["execution_plan"]
        if isinstance(exec_plan, list):
            exec_plan_str = "\n".join(f"- {step}" for step in exec_plan)
        else:
            exec_plan_str = str(exec_plan)

        # 组装视觉卡片 (标准 Markdown 语法，由 StreamTextDisplay 统一渲染琥珀金极客样式)
        modules_str = ", ".join(f"`{m}`" for m in task_record["target_modules"]) if task_record["target_modules"] else "`UI/核心模块`"
        clarify_section = ""
        if task_record["clarification_prompt"] and task_record["clarification_prompt"] != "无":
            clarify_section = f"\n> **方案沟通提示**：{task_record['clarification_prompt']}\n"

        markdown_card = f"""> **敏捷自进化工单**：编号 {task_id}

> **架构师响应**：{task_record['spoken_ack']}
{clarify_section}
### 需求要点与实施拆解
- **需求议题**：**{task_record['task_title']}**
- **归属分类**：`{task_record['category']}`（评估结果：**{task_record['feasibility']}**）
- **诉求归纳**：{task_record['requirement_summary']}
- **技术方案**：
{exec_plan_str}
- **预期模块**：{modules_str}
- **任务状态**：`PENDING` (已入库等待后台 Autonomous Loop 自动调度更新)

---
> **自动流转**：后台智能体验证通过并发版后，本客户端将收到推送并自动重启生效。
"""

        print(f"[InstructionHandler] 新需求工单已生成: {task_id} | 标题: {task_record['task_title']}")

        return {
            "answer": markdown_card,
            "spoken_text": task_record["spoken_ack"],
            "response_mode": "INSTRUCTION",
            "is_instruction": True,
            "task_id": task_id,
            "focal_topic": task_record["task_title"],
            "is_followup": False
        }

    def _evaluate_with_llm(self, raw_instruction: str) -> Dict[str, Any]:
        """调用大模型评估需求并输出结构化方案"""
        if self.client:
            try:
                prompt = INSTRUCTION_EVAL_PROMPT.format(raw_instruction=raw_instruction)
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional software architect. Return pure JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    timeout=15
                )
                text = resp.choices[0].message.content.strip()
                # 去除 markdown 代码块
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n", "", text)
                    text = re.sub(r"\n```$", "", text)
                data = json.loads(text)
                return data
            except Exception as e:
                print(f"[InstructionHandler] 大模型需求解析异常，使用本地兜底: {e}")

        # 本地兜底方案
        clean_snip = raw_instruction[:25].strip()
        return {
            "task_title": f"优化：{clean_snip}",
            "category": "UI/UX",
            "feasibility": "可行",
            "requirement_summary": f"操作员建议：{raw_instruction}",
            "target_modules": ["ui/main_window.py"],
            "execution_plan": "1. 确认操作员反馈的界面或功能点\n2. 调整对应组件渲染与交互逻辑\n3. 笔记本真机验证并推送发版",
            "spoken_ack": f"收到改进建议，已为您立项：{clean_snip}。工程师稍后将自动为您更新生效。",
            "clarification_prompt": "无"
        }

    def _append_to_queue(self, task: Dict[str, Any]):
        """线程安全地追加任务到 iteration_queue.json"""
        with self._lock:
            try:
                tasks = []
                if self.queue_file.exists():
                    try:
                        tasks = json.loads(self.queue_file.read_text(encoding="utf-8"))
                        if not isinstance(tasks, list):
                            tasks = []
                    except Exception:
                        tasks = []

                tasks.append(task)
                self.queue_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[InstructionHandler] 写入工单队列失败: {e}")
