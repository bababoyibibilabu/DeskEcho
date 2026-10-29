# DeskEcho (桌面回响)

## Purpose & Positioning
DeskEcho 是由**美好智能**打造的常驻型企业桌面 AI 知识库与即时对讲助手。它面向管理层、产研负责人与知识工作者，在后台常驻静默倾听会议与办公沟通，自动进行高质量结构化切片清洗；并通过单键（免 Fn 的【右 Alt】）毫秒级对讲交互，随时为用户唤醒、溯源并语音播报企业的历史决议、分工待办与关键事实。

## Mode
- **Primary Surface Mode**: `Operate`
  - 用户的首要诉求是“高效完成检索、查看纪要与配置引擎”任务；
  - 界面遵循高度可扫描性（Scanability）、严谨一致性（Consistency）与桌面原生直觉（Native Expectations）；
  - 视觉设计杜绝无意义的模板化装饰（AI Slop），品牌气质融入精准的细节、字重阶梯与克制灵动的交互动效中。

## Core Jobs to be Done (JTBD)
1. **对讲与即时检索 (Page 0)**：长按【右 Alt】直接语音对讲，自动意图改写并进行本地向量+全文二层 RAG 检索，结合音视分离极简 TTS 语音播报。
2. **会议记忆切片库 (Page 1)**：分级管理正式会议资产与“或许没用”次要切片（寒暄/试音），支持切片全文阅读、结构化四象限提取与安全清理。
3. **企业通讯录与协作画像 (Page 2)**：自动沉淀企业组织架构、员工岗位、最近主导会议与跨域协作画像。
4. **系统设置与引擎配置中心 (Page 3)**：集中配置 LLM API 密钥与端点、ASR 语音凭据、多角色 TTS 播报音色（云希/晓晓/云扬/云健，含即时试听）与对讲热键，预留企业生态扩展插槽。
5. **版本发版与自动更新 (Page 4)**：无缝检查 GitHub Releases，一键下载并原子替换单一 Windows EXE 运行文件。

## Platform & Constraints
- **Platform**: Windows Desktop (Windows 10/11 x64)
- **Framework**: PyQt6 (Native Qt C++ bindings with modern QSS & custom QPainter widgets)
- **Audio Stack**: PyAudio 16kHz Mono + WebRTC VAD + 火山流式 ASR 2.0 / 阿里 DashScope + Edge-TTS
- **Theme**: Light & Dark 自适应双主题，高对比度防眩光，0 静态 Emoji，全量矢量 Google Material Symbols。
