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
        "current_focus": "2026年度AI创新专项预算批复，要求严把采购招标关"
    },
    {
        "name": "李志成",
        "title": "核心算法团队负责人",
        "status": "active",
        "aliases": ["李工", "算法李", "志成"],
        "duties": "负责自适应学习系统、知识追踪模型（BKT）与算法工程落地",
        "tech_stack": "Python / PyTorch / BKT / 深度学习",
        "current_focus": "自适应学习知识点掌握度动态追踪算法与0.85阈值研发"
    },
    {
        "name": "王程",
        "title": "产品总监 / 架构协调",
        "status": "active",
        "aliases": ["王总", "程哥", "产品王"],
        "duties": "负责 DeskEcho 客户端体验、上线排期与跨部门研发试点推进",
        "tech_stack": "产品规划 / 敏捷交付 / 系统架构",
        "current_focus": "DeskEcho 11月15日全员内测与研发部先行试点落地"
    },
    {
        "name": "陈佳",
        "title": "供应链与采购总监",
        "status": "active",
        "aliases": ["陈总监", "佳姐", "陈经理"],
        "duties": "负责硬件设备采购、算力集群设备招标及供应链把关",
        "tech_stack": "采购供应链 / 招投标 / 成本控制",
        "current_focus": "2026年度AI专项GPU算力集群设备采购招标严格把关"
    },
    {
        "name": "赵文",
        "title": "人力资源与组织发展总监",
        "status": "active",
        "aliases": ["赵总监", "文姐", "赵主管"],
        "duties": "统筹全公司职级晋升、薪酬绩效考核及组织人才发展",
        "tech_stack": "HRBP / 绩效激励体系 / 组织发展",
        "current_focus": "年终P5-P8职级晋升答辩组织与S/A/B档绩效考核宣贯"
    },
    {
        "name": "周工",
        "title": "系统架构师 / 运维容灾专家",
        "status": "active",
        "aliases": ["老周", "周工", "架构师"],
        "duties": "负责公司高可用服务器架构、双活灾备网络及专线容灾系统",
        "tech_stack": "高可用架构 / BGP多线容灾 / 故障应急",
        "current_focus": "华东客户双活灾备光纤中断复盘与BGP多线冗余改造"
    },
    {
        "name": "刘晓",
        "title": "市场公关与商业合作经理",
        "status": "active",
        "aliases": ["刘经理", "刘总", "市场公关"],
        "duties": "负责全球科技峰会参展布展、特装展位搭建及媒体公关合作",
        "tech_stack": "公关传播 / 展会统筹 / 商务合作",
        "current_focus": "2026 Q4全球AI峰会特装展台搭建与王总主题演讲安排"
    },
    {
        "name": "林浩",
        "title": "质量监控与数据埋点工程师",
        "status": "active",
        "aliases": ["林经理", "小林", "质量监控"],
        "duties": "负责客户端稳定性监控、核心用户行为埋点收集与故障告警",
        "tech_stack": "数据埋点 / APM 监控 / 日志分析",
        "current_focus": "DeskEcho 研发部首期试点数据监控与全链路埋点分析"
    },
    {
        "name": "李华",
        "title": "产品 UI / UE 视觉与交互专家",
        "status": "active",
        "aliases": ["华哥", "李设计师", "UI", "设计"],
        "duties": "负责产品全链路视觉系统、Alma 美学黑曜石科技风格沉淀",
        "tech_stack": "UI/UE 设计 / 动效交互 / 视觉传达",
        "current_focus": "桌面回响三色渐变极光微交互与通讯录动态卡片体验"
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
