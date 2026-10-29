from typing import List, Dict, Any, Optional

# 企业实体与组织架构知识库 (企业实际组织架构)
COMPANY_INFO = {
    "name": "未来智能",
    "aliases": ["公司", "咱们公司", "团队", "研发部"],
    "projects": [
        "AI 桌面智能助手 (DeskEcho)",
        "企业级常驻会议记忆中台",
        "多模态工作流与自适应知识库",
        "智能硬件交互与端侧大模型"
    ]
}

EMPLOYEES: List[Dict[str, Any]] = [
    {
        "name": "张明",
        "title": "董事长 / 战略决策层",
        "status": "active",
        "aliases": ["张总", "董事长", "老板"],
        "duties": "公司董事长，统筹公司全局方向、长期发展战略与关键资本规划",
        "tech_stack": "战略规划 / 资本运作 / 商业决策",
        "current_focus": "公司中长期战略规划与重大业务决策"
    },
    {
        "name": "李建国",
        "title": "总经理 / 业务总监",
        "status": "active",
        "aliases": ["李总", "建国总", "总经理", "发言人1"],
        "duties": "公司日常运营与业务推进总负责人，统筹多端产品交付及跨部门战略协同",
        "tech_stack": "运营管理 / 跨部门协作 / 业务推进",
        "current_focus": "产品落地交付、运营保障与团队协作"
    },
    {
        "name": "王程",
        "title": "产品总监 / 架构协调",
        "status": "active",
        "aliases": ["王总", "程哥", "产品王"],
        "duties": "产品总监，负责桌面助手与知识库产品功能规划、技术协调及业务模式落地",
        "tech_stack": "Python / 系统架构 / 产品规划",
        "current_focus": "DeskEcho 核心交互设计、端侧体验调优与技术对接"
    },
    {
        "name": "陈佳",
        "title": "行政人事与组织文化负责人",
        "status": "active",
        "aliases": ["佳姐", "陈经理", "行政", "人事", "陈佳彤"],
        "duties": "负责团队行政人事、日常办公保障、组织文化建设及流程规范",
        "tech_stack": "行政人事 / 流程管理 / 团队文化",
        "current_focus": "日常运营保障与跨团队高效沟通"
    },
    {
        "name": "李华",
        "title": "产品 UI / UE 视觉与交互专家",
        "status": "active",
        "aliases": ["华哥", "李设计师", "UI", "UE", "设计"],
        "duties": "负责产品 UI / UE 视觉与交互设计、设计规范沉淀及用户体验全链路把控",
        "tech_stack": "UI/UE 设计 / 视觉传达 / 交互原型",
        "current_focus": "Alma 风格黑曜石美学界面与动效体验优化"
    },
    {
        "name": "赵文",
        "title": "数据工程师 / 结构化处理主管",
        "status": "active",
        "aliases": ["文姐", "赵主管", "数据分析"],
        "duties": "负责非结构化会议语音与文档的格式解析、向量化管线及知识图谱构建",
        "tech_stack": "ETL 数据工程 / 知识抽取 / 自动化管线",
        "current_focus": "会议数据清洗、切片优化与知识对齐"
    },
    {
        "name": "郎工",
        "title": "全栈技术专家 / AI工作流开发",
        "status": "active",
        "aliases": ["小郎", "郎老师", "全栈"],
        "duties": "负责全栈技术支撑、AI 算法工程化落地、音视频处理与系统集成",
        "tech_stack": "Python / C++ / WebSockets / AI工程化",
        "current_focus": "多模态语音管道、低延迟 ASR/TTS 调优与端侧部署"
    },
    {
        "name": "周工",
        "title": "系统架构师 / 后端服务专家",
        "status": "active",
        "aliases": ["老周", "周工", "架构师"],
        "duties": "负责高可用云端与局域网服务架构、分布式缓存与安全认证设计",
        "tech_stack": "微服务架构 / 向量数据库 / 容器化",
        "current_focus": "向量检索性能调优与本地数据存储安全"
    },
    {
        "name": "刘工",
        "title": "客户端与系统层开发工程师",
        "status": "active",
        "aliases": ["小刘", "刘工", "客户端"],
        "duties": "负责 Windows 原生客户端调优、系统热键拦截、音频硬件流适配与托盘守护",
        "tech_stack": "PyQt6 / Windows API / 音频底层驱动",
        "current_focus": "全局无冲突热键拦截与开机自启稳定性保障"
    }
]

def extract_action_summary(emp_name: str, aliases: List[str], slices: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """从历史会议切片中提取该人员的关键决策、主导事项或发言结论"""
    keywords = [emp_name] + aliases
    actions = []
    for s in slices:
        summary_text = s.get("summary", "")
        raw_text = s.get("raw_text", "")
        start_time = s.get("start_time", "")
        date_str = start_time[:16] if len(start_time) >= 16 else start_time

        topic = ""
        conclusion = ""
        for line in summary_text.split("\n"):
            line = line.strip()
            if "【核心议题】" in line or "【议题】" in line or "1. 核心议题" in line:
                topic = line.replace("【核心议题】", "").replace("【议题】", "").replace("1. 核心议题（Topic）：", "").strip()
            if any(k in line for k in keywords):
                conclusion = line.replace("【关键结论】", "").replace("【结论】", "").replace("2. 决策与结论（Key Decisions）：", "").strip()

        if not conclusion:
            for sent in raw_text.split("。"):
                sent = sent.strip()
                if any(k in sent for k in keywords) and len(sent) > 5:
                    conclusion = sent
                    break

        if not topic:
            topic = summary_text.split("\n")[0][:25] if summary_text else "常规业务研讨"
        if not conclusion:
            conclusion = summary_text[:50] if summary_text else "参与会议决策并给出指导意见"

        actions.append({
            "time": date_str,
            "topic": topic,
            "highlight": conclusion
        })
    return actions

def get_dynamic_employee_profile(store, emp: Dict[str, Any]) -> Dict[str, Any]:
    """动态获取员工画像，汇聚会议参与度与关键主导事项"""
    names = [emp["name"]] + emp.get("aliases", [])
    slices = store.query_slices_by_entity_names(names, limit=6) if store else []
    
    actions = extract_action_summary(emp["name"], emp.get("aliases", []), slices)
    
    if actions:
        latest_act = actions[0]
        core_highlight = f"{latest_act['highlight']}"
    else:
        core_highlight = emp.get("current_focus", emp.get("duties", ""))
        
    return {
        "emp": emp,
        "meeting_count": len(slices),
        "latest_active": slices[0].get("start_time", "") if slices else "",
        "core_highlight": core_highlight,
        "actions": actions
    }

def get_entity_context_prompt() -> str:
    """
    生成用于大模型 Prompt 注入的企业组织实体背景信息
    """
    lines = [f"【公司名称】：{COMPANY_INFO['name']}"]
    lines.append(f"【核心业务】：{', '.join(COMPANY_INFO['projects'])}")
    lines.append("【组织架构与团队成员档案】：")
    for emp in EMPLOYEES:
        aliases_str = f"（语音常见别名/误读：{', '.join(emp['aliases'])}）" if emp.get('aliases') else ""
        status_tag = "【状态：已离职，历史贡献档案留存】" if emp.get("status") == "departed" else "【状态：在职】"
        lines.append(
            f"- {emp['name']}{aliases_str}：{emp['title']} {status_tag}。职责：{emp['duties']}。技术栈/特长：{emp['tech_stack']}。"
        )
    return "\n".join(lines)

def query_entity_by_keyword(keyword: str) -> List[Dict[str, Any]]:
    """
    根据人名、别名、职位、技术栈等关键词反查员工
    """
    kw = keyword.lower()
    matched = []
    for emp in EMPLOYEES:
        if (kw in emp["name"].lower() or 
            kw in emp["title"].lower() or 
            kw in emp["duties"].lower() or 
            kw in emp["tech_stack"].lower() or
            any(kw in a.lower() for a in emp.get("aliases", []))):
            matched.append(emp)
    return matched
