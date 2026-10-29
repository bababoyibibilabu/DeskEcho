from typing import List, Dict, Any, Optional

# 企业实体与组织架构知识库 (根据企业实际真实组织架构与团队成员配置)
COMPANY_INFO = {
    "name": "未来智能 / 巨升科技",
    "aliases": ["公司", "咱们公司", "团队", "研发部", "巨升机器人"],
    "projects": [
        "AI 桌面智能助手 (DeskEcho)",
        "企业级常驻会议记忆中台",
        "K12 互动学习平板与陪伴机器人",
        "多模态工作流与自适应知识库"
    ]
}

EMPLOYEES: List[Dict[str, Any]] = [
    {
        "name": "陈佳彤",
        "title": "行政人事与组织办公室负责人",
        "status": "active",
        "aliases": ["陈佳彤", "小陈", "佳彤", "陈经理", "行政人事"],
        "duties": "负责团队行政人事、日常办公保障、组织协同与团队后勤支撑，新员工入职对接",
        "tech_stack": "行政管理 / 人事组织 / 流程规范 / 日常协调",
        "current_focus": "团队行政人事规范化推进、流程无缝衔接与办公保障"
    },
    {
        "name": "吕明秋",
        "title": "算法与大模型应用专家",
        "status": "active",
        "aliases": ["吕明秋", "吕工", "老吕", "小吕"],
        "duties": "负责大模型应用落地、课程脚本AI辅助生成、自适应评估与交互逻辑调优",
        "tech_stack": "Python / 大模型工作流 / Prompt工程 / 算法工程",
        "current_focus": "智能陪学系统核心交互与AI生成工作流构建"
    },
    {
        "name": "杨年新",
        "title": "总经理 / 业务与资源统筹总负责人",
        "status": "active",
        "aliases": ["杨总", "杨年新", "杨建新", "老杨", "发言人1", "发言人7"],
        "duties": "公司整体业务推进与技术资源兜底，统筹多端产品交付、外部院校合作与商务资源",
        "tech_stack": "战略运营 / 商业推进 / 综合调度 / 资源协调",
        "current_focus": "推进“奋斗一百天”核心目标、东北师大/吉大合作项目与场地规划落地"
    },
    {
        "name": "陈思豪",
        "title": "系统后端与接口开发主管",
        "status": "active",
        "aliases": ["陈思豪", "陈哥", "思豪", "陈工"],
        "duties": "负责服务端架构设计、API接口定义与高可用微服务搭建，主导前后端并行高效交付",
        "tech_stack": "Python / 后端架构 / RESTful API / 数据库 / 微服务",
        "current_focus": "先行出具API接口体系与数据处理流程梳理"
    },
    {
        "name": "程远",
        "title": "技术总监 / 架构与研发协调",
        "status": "active",
        "aliases": ["程远", "成远", "成哥", "程哥", "发言人3"],
        "duties": "统筹技术研发全局协调、跨端架构设计、软硬件技术方案打通与开发节奏把控",
        "tech_stack": "系统架构 / 技术协调 / 软硬协同 / 跨平台交付",
        "current_focus": "整体技术方案架构协调、安卓端与机器人端协同落地"
    },
    {
        "name": "荣硕",
        "title": "硬件与嵌入式测试工程师",
        "status": "active",
        "aliases": ["荣硕", "小荣", "荣工", "荣"],
        "duties": "负责硬件白板/平板、麦克风拾音、天机900板卡调试、硬件交互与声音测试",
        "tech_stack": "硬件调试 / 嵌入式开发 / 拾音设备 / 系统部署",
        "current_focus": "天机900双麦克风调试与硬件白板测试环境搭建"
    },
    {
        "name": "张文嘉",
        "title": "商业运营与合作拓展主管",
        "status": "active",
        "aliases": ["张文嘉", "张文佳", "文嘉", "小张"],
        "duties": "负责合作院校（东北师大、吉大等）项目落地推进、承办代表对接与商业合作拓展",
        "tech_stack": "商务拓展 / 项目承办 / 商务运营 / 院校合作",
        "current_focus": "东北师大校区部等关键合作项目跟进与承办落地"
    },
    {
        "name": "李洋",
        "title": "产品 UI / UE 视觉与交互专家",
        "status": "active",
        "aliases": ["李洋", "李阳", "洋哥", "UI", "设计", "美编"],
        "duties": "负责产品 UI / UE 视觉与全链路交互设计、页面定稿、视觉规范与动效打磨",
        "tech_stack": "UI/UE 设计 / 视觉传达 / 动效交互 / 原型设计",
        "current_focus": "学习平板与机器人端多端视觉定稿与交互规范输出"
    },
    {
        "name": "郎琦",
        "title": "安卓端核心研发工程师",
        "status": "active",
        "aliases": ["郎琦", "郎琪", "小郎", "安卓郎", "安卓开发"],
        "duties": "负责安卓端机器人/平板应用架构、数据库表结构设计与客户端交互功能落地",
        "tech_stack": "Android / Kotlin / Java / SQLite / 客户端通信",
        "current_focus": "安卓数据库设计与核心页面功能开发"
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
                conclusion = line.replace("【关键结论】", "").replace("【结论】", "").replace("2. 决策与结论（Key Decisions）：", "").replace("3. 待办事项（Action Items）：", "").strip()

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
