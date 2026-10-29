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
        "name": "吕明秋",
        "title": "董事长",
        "status": "active",
        "aliases": ["吕明秋", "吕总", "董事长", "老板", "明秋"],
        "duties": "公司董事长与战略决策委员会负责人。统筹公司中长期战略规划、商业定位、重大投融资与业务决策，把关核心研发资源方向与品牌标识定位",
        "tech_stack": "企业战略决策 / 商业发展 / 资本统筹 / 核心定位规划",
        "current_focus": "公司中长期战略规划把关、品牌Logo定位与关键业务方向审核"
    },
    {
        "name": "杨年新",
        "title": "总经理 / 业务与资源统筹总负责人",
        "status": "active",
        "aliases": ["杨总", "杨年新", "杨建新", "老杨", "发言人7", "发言人1"],
        "duties": "公司总经理，全面把控业务推进进度与软硬件技术资源兜底，推进“奋斗一百天”攻坚战，统筹东北师大与吉大等外部合作及展会参展落地",
        "tech_stack": "战略运营 / 商业推进 / 综合调度 / 资源协调 / 跨端协同",
        "current_focus": "推进“奋斗一百天”核心攻坚目标、东北师大/吉大合作项目与场地落地"
    },
    {
        "name": "程远",
        "title": "产品经理 (深耕教培行业 / 技术研发)",
        "status": "active",
        "aliases": ["程远", "成远", "成哥", "程哥", "发言人3", "教培", "BKT", "掌握度"],
        "duties": "深耕教培行业产品设计与全栈技术开发，负责K12互动学习闭环、自适应抽题评测体系、BKT知识追踪与掌握度画像算法、软硬件协同架构与功能定义",
        "tech_stack": "教培产品规划 / 知识图谱 / 自适应学习(BKT) / 全栈研发 / 软硬件协同",
        "current_focus": "K12自适应学习闭环设计、知识图谱推导、掌握度画像算法与多端功能落地"
    },
    {
        "name": "陈思豪",
        "title": "机器人后端开发",
        "status": "active",
        "aliases": ["陈思豪", "陈哥", "思豪", "陈工", "机器人后端", "后端接口"],
        "duties": "负责机器人服务端与核心后端开发、RESTful API 规范制定、前后端并行交付数据管道搭建、多端数据同步与微服务开发",
        "tech_stack": "机器人后端 / Python / API架构 / 数据管道 / 微服务",
        "current_focus": "机器人后端接口体系规范化、数据管道打通与多端接口联调交付"
    },
    {
        "name": "荣硕",
        "title": "机器人安卓开发 / 语音交互工程师",
        "status": "active",
        "aliases": ["荣硕", "小荣", "荣工", "荣", "语音交互", "打断", "麦克风", "拾音"],
        "duties": "负责机器人端安卓应用开发与系统适配，主导高音量下语音唤醒与打断 (Barge-in)、回声消除 (AEC)、麦克风拾音链路调试与硬件板卡联调",
        "tech_stack": "机器人安卓 / 语音交互 / 降噪与回声消除(AEC) / 拾音设备调试 / 硬件板卡",
        "current_focus": "机器人音频链路测试、回声消除与高音量唤醒打断方案调优、板卡与白板硬件连接调试"
    },
    {
        "name": "张文嘉",
        "title": "行政主管 / 题库与教研数据整理",
        "status": "active",
        "aliases": ["张文嘉", "张文佳", "文嘉", "小张", "题库", "错题", "映射表"],
        "duties": "负责团队综合行政事务、校企合作日常对接与承办代表工作，主导K12题库精细化梳理、教材版本与知识点映射表构建、错题归因体系整理",
        "tech_stack": "行政管理 / 题库整理 / 教研知识树 / 错题归类 / 院校合作对接",
        "current_focus": "K12题库精细化梳理、各区域教材与知识点映射表构建、错题归因与行政保障"
    },
    {
        "name": "郎琦",
        "title": "安卓开发工程师 / 全栈与AI技术支持",
        "status": "active",
        "aliases": ["郎琦", "郎琪", "小郎", "安卓", "全栈", "AI技术", "数据表", "抓取"],
        "duties": "负责安卓客户端核心应用开发、多表复杂数据库设计与持久化存储，同时提供全栈系统支持与AI模型调用脚本/数据抓取技术支持",
        "tech_stack": "Android开发 / 全栈研发 / SQLite多表架构 / AI技术支持 / Python数据脚本",
        "current_focus": "安卓端数据库架构实现 (多表关联与性能调优)、AI题目审核辅助与技术调用支撑"
    },
    {
        "name": "李洋",
        "title": "产品 UI / UE 视觉与交互专家",
        "status": "active",
        "aliases": ["李洋", "李阳", "洋哥", "UI", "视觉", "界面", "设计", "美编"],
        "duties": "负责产品全链路视觉与UI/UE交互设计，主导平板端与机器人端视觉规范、页面定稿、开屏学情录入交互、企业VI与品牌标识设计",
        "tech_stack": "UI/UE设计 / 视觉传达 / 交互原型 / 动效设计 / 品牌VI",
        "current_focus": "学习平板与机器人端多端视觉定稿、开屏形象体互动与企业VI标识设计打磨"
    },
    {
        "name": "陈佳彤",
        "title": "行政人事与组织办公室负责人",
        "status": "active",
        "aliases": ["陈佳彤", "小陈", "佳彤", "陈经理", "行政人事", "办公室", "考勤", "入职"],
        "duties": "全面主持行政人事办公室日常运转，负责团队考勤与后勤保障、新员工入职对接、跨部门协同盯办、推进工作进度表与组织保障",
        "tech_stack": "行政人事 / 组织协同 / 进度盯办 / 后勤保障 / 流程规范",
        "current_focus": "团队行政人事规范化推进、新同事入职对接、跟进项目日常进度表与无缝业务链接"
    }
]

def extract_action_summary(emp_name: str, aliases: List[str], slices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    从历史会议切片中智能提取该人员的关键决策、待办落实、主导发言与事实备忘
    """
    kw = [emp_name] + aliases
    actions = []
    for s in slices:
        summary_text = s.get("summary", "")
        raw_text = s.get("raw_text", "")
        start_time = s.get("start_time", "")
        date_str = start_time[:16] if len(start_time) >= 16 else start_time

        sections: Dict[str, Any] = {"topic": "", "decisions": [], "actions": [], "facts": []}
        current_sec = None
        for line in summary_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "1. 核心议题" in line or "【核心议题】" in line or "【议题】" in line:
                current_sec = "topic"
                topic_content = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                sections["topic"] = topic_content
            elif "2. 决策与结论" in line or "【关键结论】" in line or "【结论】" in line:
                current_sec = "decisions"
            elif "3. 待办事项" in line or "【待办事项】" in line or "【待办】" in line:
                current_sec = "actions"
            elif "4. 事实备忘" in line or "【事实备忘】" in line:
                current_sec = "facts"
            else:
                if current_sec and current_sec != "topic":
                    sections[current_sec].append(line)

        relevant_actions = [a for a in sections["actions"] if any(k in a for k in kw)]
        relevant_decisions = [d for d in sections["decisions"] if any(k in d for k in kw)]
        relevant_facts = [f for f in sections["facts"] if any(k in f for k in kw)]

        points = []
        if relevant_actions:
            for act in relevant_actions[:2]:
                clean_act = act.lstrip("-*•123456789. ")
                points.append(f"📌 待办落实：{clean_act}")
        if relevant_decisions:
            for dec in relevant_decisions[:2]:
                clean_dec = dec.lstrip("-*•123456789. ")
                points.append(f"✅ 关键决策：{clean_dec}")
        if relevant_facts and not points:
            for fact in relevant_facts[:2]:
                clean_fact = fact.lstrip("-*•123456789. ")
                points.append(f"📝 事实备忘：{clean_fact}")

        spoken_quote = ""
        if not points:
            for sent in raw_text.split("\n"):
                sent = sent.strip()
                if any(k in sent for k in kw) and len(sent) > 8:
                    spoken_quote = sent[:120]
                    break
            if spoken_quote:
                points.append(f"🎙️ 现场发言：{spoken_quote}")

        if not points:
            if sections["decisions"] and sections["decisions"][0] != "无":
                first_dec = sections["decisions"][0].lstrip("-*•123456789. ")
                points.append(f"✅ 决议协同：{first_dec}")
            elif sections["topic"]:
                points.append(f"🎯 重点研讨：{sections['topic'][:60]}")
            else:
                points.append("🤝 参与研讨并输出指导意见")

        topic = sections["topic"]
        if not topic:
            topic = s.get("id", "").split("_slice_")[0].replace("_", " ")

        highlight = points[0] if points else "参与会议决策并跟进落实"
        actions.append({
            "slice_id": s.get("id", ""),
            "time": date_str,
            "topic": topic,
            "highlight": highlight,
            "points": points
        })
    return actions

def get_dynamic_employee_profile(store, emp: Dict[str, Any]) -> Dict[str, Any]:
    """动态获取员工画像，汇聚会议参与度与关键主导事项"""
    names = [emp["name"]] + emp.get("aliases", [])
    slices = store.query_slices_by_entity_names(names, limit=8) if store else []

    actions = extract_action_summary(emp["name"], emp.get("aliases", []), slices)

    if actions:
        latest_act = actions[0]
        pts = latest_act.get("points", [])
        if pts:
            core_highlight = f"【{latest_act.get('topic', '近期会议')}】{pts[0]}"
        else:
            core_highlight = f"【{latest_act.get('topic', '近期会议')}】{latest_act.get('highlight', '')}"
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
