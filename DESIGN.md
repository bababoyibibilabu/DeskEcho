---
name: DeskEcho
description: Enterprise Ambient AI Knowledge Base & Push-to-Talk Desktop Assistant
colors:
  primary-deep: "#0E347A"
  primary: "#0284C7"
  primary-light: "#26B0E4"
  success: "#16A34A"
  success-glow: "#8AC657"
  warning: "#D97706"
  warning-glow: "#FBBF24"
  danger: "#DC2626"
  bg-light: "#F8FAFC"
  surface-light: "#FFFFFF"
  border-light: "#E2E8F0"
  text-primary-light: "#0F172A"
  text-secondary-light: "#475569"
  text-muted-light: "#64748B"
  bg-dark: "#0B0D13"
  surface-dark: "#11141D"
  border-dark: "rgba(255, 255, 255, 0.08)"
  text-primary-dark: "#FFFFFF"
  text-secondary-dark: "#CBD5E1"
  text-muted-dark: "#94A3B8"
typography:
  display:
    fontFamily: "-apple-system, 'Segoe UI Variable Display', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.3
  heading:
    fontFamily: "-apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: 1.4
  body:
    fontFamily: "-apple-system, 'Segoe UI Variable Text', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.55
  caption:
    fontFamily: "-apple-system, 'Segoe UI Variable Text', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.4
  code:
    fontFamily: "'Cascadia Code', Consolas, Monaco, monospace"
    fontSize: "11.5px"
    fontWeight: 400
    lineHeight: 1.45
rounded:
  xs: "3px"
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: "7px 18px"
  button-secondary-light:
    backgroundColor: "{colors.surface-light}"
    textColor: "{colors.text-secondary-light}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
---

## Overview
DeskEcho 是一款常驻桌面的专业级 AI 语音与知识库生产力工具。设计语言遵循 **Operate** 模式规范：追求极高的信息扫描率与操作直觉，消除一切虚浮的模板化装饰（AI Slop）。品牌通过精炼的字阶、呼吸感的间距、克制有度的微动效以及通透的双主题对比度体现专业沉淀。

## Colors
系统采用高保真双主题色彩体系（Light & Dark），符合 WCAG AA（对比度 ≥ 4.5:1）严苛规范：

### Light Theme (日间通透规范)
- **Base Background**: `#F8FAFC`（柔和低刺激浅冷灰底座，避免纯白刺眼）
- **Surface / Card**: `#FFFFFF`（主体内容卡片背景）
- **Border / Divider**: `#E2E8F0`（1px 微细中性边界）
- **Text Primary**: `#0F172A`（Slate-900，深沉清晰的主体字）
- **Text Secondary**: `#475569`（Slate-600，次级正文）
- **Text Muted**: `#64748B`（Slate-500，元数据与时间戳）
- **Accent Primary**: `#0284C7`（天青蓝，核心操作与焦点）
- **Accent Success**: `#16A34A`（绿意，麦克风倾听与成功状态）
- **Accent Amber**: `#D97706`（琥珀橙，倾听暂停与提示）

### Dark Theme (夜间深空规范)
- **Base Background**: `#0B0D13`（深邃微蓝暗夜底座）
- **Surface / Card**: `#11141D`（次级工作卡片）
- **Border / Divider**: `rgba(255, 255, 255, 0.08)`（通透微光细线）
- **Text Primary**: `#FFFFFF`（高可读纯白）
- **Text Secondary**: `#CBD5E1`（Slate-300，舒适次级白）
- **Text Muted**: `#94A3B8`（Slate-400，低频元数据）
- **Accent Primary**: `#26B0E4` / `#38BDF8`（发光天青蓝）
- **Accent Success**: `#8AC657`（荧光绿，暗色底座高对比度）
- **Accent Amber**: `#FBBF24`（柔和暖黄，暂停态指示）

## Typography
- **Font Stack**: `-apple-system, "Segoe UI", "Microsoft YaHei", sans-serif`
- **Text Measure**: 正文控制在单行 60–75 字符（`65ch`），提供舒适阅读节奏。
- **Hierarchy Scale**:
  - `Title`: 15px–16px, Weight 800 (DeskEcho 品牌名、页面大标)
  - `Section Heading`: 13.5px–14px, Weight 700 (卡片标题、议题标题)
  - `Body / Answer`: 12.5px–13px, Weight 400–600 (知识解答正文，Line Height 1.55)
  - `Caption / Meta`: 11px, Weight 500 (时间戳、研判理由、状态提示)

## Layout
- **侧边栏 (Sidebar)**：固定宽度 240px，包含品牌主标、即时检索与会话抽屉、倾听状态胶囊及底部状态。
- **主工作区 (Content Area)**：自适应全宽，内容卡片内边距 16px–20px，垂直栅格间距 12px–16px。
- **双栏切片检查器 (Splitter)**：左侧 320px 列表，右侧自适应详情卡，无多余外框嵌套。

## Elevation & Depth
- **单层级海拔原则 (Elevation Once)**：每个区域仅使用边框（1px 微线）或柔和阴影，严禁“1px 边框 + 巨大弥散投影”的幽灵卡片组合。
- **光晕机制**：麦克风呼吸胶囊的脉冲光晕（Pulse Halo）专属于硬件活跃状态指示，禁止在普通卡片上使用无偏移的大面积伪彩光晕。
- **Border Beam 边框流光**：仅在知识溯源解答正在流式打字输出与 TTS 播放时激活流动，输出结束立即定格静止。

## Shapes
- **Corner Radius**:
  - `Small Controls / Pills`: 6px–8px (按钮、输入框、标签胶囊)
  - `Main Cards`: 10px–12px (核心工作面板、设置卡片)
  - `No Extreme Rounding`: 严禁在大卡片上使用超过 16px 的圆角，避免界面显得松散稚拙。

## Components
- **Buttons**:
  - `Primary Action`: 实底品牌色 `#0284C7`，白字，Hover 加深；
  - `Secondary Action`: 微底中性边框，无过饱和色块；
  - `Icon Buttons`: 纯净透明底，Hover 显露微弱背景。
- **Input & Selects**:
  - 高度 34px，内边距 6px 12px，Focus 时赋予清晰的 1.5px 品牌色环，无模糊发散。
- **Icons**:
  - 100% 采用 Google Material Symbols 矢量渲染，严禁使用任何系统静态 Emoji。

## Do's and Don'ts

### Do's
1. **真实内容主导**：所有卡片均填充真实业务数据与会议问题，杜绝占位模板废话。
2. **通透克制**：在日间与夜间模式中均维持高可读性，背景色低饱和度。
3. **状态完整**：每个交互控件均具备完整的 Default、Hover、Active、Focus、Disabled 与 Empty 状态。

### Don'ts (Banned Anti-Patterns)
1. **严禁粗侧边彩色线条 (No Thick `border-left`)**：彻底禁止在引用框、卡片或列表项左侧使用 `border-left: 3px/4px solid ...`，此为典型 AI 模板化痕迹。改用 1px 精致全线框或微弱底色包裹。
2. **严禁嵌套卡片 (No Nested Cards)**：卡片内部不再套小卡片，使用留白与字号阶梯做层级划分。
3. **严禁文字渐变 (No Gradient Text)**：所有文本的强调一律通过字号与字重表达，杜绝彩色渐变字。
4. **严禁眉标 (No Eyebrow Kickers)**：禁止在主标题上方额外堆砌大写灰字眉标（如 “WORKSPACE” 或 “SYSTEM ENGINE”），由主标题直接表达。
5. **严禁静态系统 Emoji**：严禁用 Emoji 充当业务图标。
