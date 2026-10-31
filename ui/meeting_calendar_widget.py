# -*- coding: utf-8 -*-
"""
DeskEcho 会议记忆库 - 月度会议日历看板 (Calendar Master View)
以月历网格形式宏观展示历史会议分布与资产热力，点击某天可下钻至该日会议详情。
"""
import calendar
import datetime
from typing import Dict, Any, Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from ui.theme_manager import ThemeManager
from ui.components.icons import get_symbol_icon, get_symbol_pixmap


class DayCard(QFrame):
    """日历中的单日卡片"""
    def __init__(
        self,
        date_str: str,
        day_num: int,
        is_current_month: bool,
        day_data: Optional[Dict[str, Any]],
        is_today: bool,
        is_light: bool,
        on_click: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.date_str = date_str
        self.day_num = day_num
        self.is_current_month = is_current_month
        self.day_data = day_data
        self.is_today = is_today
        self.is_light = is_light
        self.on_click = on_click

        self.has_records = bool(day_data and day_data.get("total_count", 0) > 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(78)

        self._init_ui()
        self._apply_style(is_hover=False)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 顶行：日期数字 + 状态徽标 (今天 / 会议条数)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        # 日期号
        self.day_num_lbl = QLabel(str(self.day_num) if self.day_num > 0 else "")
        self.day_num_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: {'700' if self.is_today or self.has_records else '500'}; "
            f"color: {'#0F172A' if self.is_light else '#F1F5F9' if self.is_current_month else '#64748B'};"
        )
        header_layout.addWidget(self.day_num_lbl)

        # 若是今天，显示 [今天] 标签
        if self.is_today:
            self.today_pill = QLabel("今天")
            self.today_pill.setStyleSheet("""
                QLabel {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    font-size: 10px;
                    font-weight: 600;
                    border-radius: 4px;
                    padding: 1px 4px;
                }
            """ if self.is_light else """
                QLabel {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    font-size: 10px;
                    font-weight: 600;
                    border-radius: 4px;
                    padding: 1px 4px;
                }
            """)
            header_layout.addWidget(self.today_pill)

        header_layout.addStretch(1)

        # 若有记录，显示记录条数小胶囊
        if self.has_records:
            total_cnt = self.day_data.get("total_count", 0)
            useful_cnt = self.day_data.get("useful_count", total_cnt)
            badge_text = f"● {useful_cnt} 条记忆"
            self.badge_lbl = QLabel(badge_text)
            if self.is_light:
                self.badge_lbl.setStyleSheet("""
                    QLabel {
                        background-color: rgba(2, 132, 199, 0.12);
                        color: #0284C7;
                        font-size: 10.5px;
                        font-weight: 600;
                        border-radius: 4px;
                        padding: 1px 6px;
                    }
                """)
            else:
                self.badge_lbl.setStyleSheet("""
                    QLabel {
                        background-color: rgba(38, 176, 228, 0.18);
                        color: #38BDF8;
                        font-size: 10.5px;
                        font-weight: 600;
                        border-radius: 4px;
                        padding: 1px 6px;
                    }
                """)
            header_layout.addWidget(self.badge_lbl)

        layout.addLayout(header_layout)

        # 中部：核心议题预览 (最多 2 行)
        if self.has_records:
            topics = self.day_data.get("topics", [])
            for t in topics[:2]:
                clean_t = t.replace("\n", " ").strip()
                if len(clean_t) > 18:
                    clean_t = clean_t[:17] + "…"
                t_lbl = QLabel(f"• {clean_t}")
                color = "#475569" if self.is_light else "#94A3B8"
                t_lbl.setStyleSheet(f"font-size: 10.5px; color: {color};")
                layout.addWidget(t_lbl)
        layout.addStretch(1)

        if self.has_records:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _apply_style(self, is_hover: bool):
        if not self.is_current_month:
            # 非当月日期（留白/淡化）
            bg = "#F8FAFC" if self.is_light else "#0B0E14"
            border = "rgba(0,0,0,0.03)" if self.is_light else "rgba(255,255,255,0.02)"
            self.setStyleSheet(f"""
                DayCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 8px;
                }}
            """)
            return

        if self.has_records:
            if self.is_light:
                bg = "#F0F9FF" if is_hover else "#FFFFFF"
                border = "#0284C7" if is_hover else "#CBD5E1"
                self.setStyleSheet(f"""
                    DayCard {{
                        background-color: {bg};
                        border: {'1.5px' if is_hover else '1px'} solid {border};
                        border-radius: 8px;
                    }}
                """)
            else:
                bg = "rgba(38, 176, 228, 0.12)" if is_hover else "#11141D"
                border = "#38BDF8" if is_hover else "rgba(255, 255, 255, 0.08)"
                self.setStyleSheet(f"""
                    DayCard {{
                        background-color: {bg};
                        border: {'1.5px' if is_hover else '1px'} solid {border};
                        border-radius: 8px;
                    }}
                """)
        else:
            # 当月无记录日期
            bg = "#FAFAFA" if self.is_light else "rgba(255,255,255,0.02)"
            border = "#E2E8F0" if self.is_light else "rgba(255, 255, 255, 0.04)"
            self.setStyleSheet(f"""
                DayCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 8px;
                }}
            """)

    def enterEvent(self, event):
        if self.has_records:
            self._apply_style(is_hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.has_records:
            self._apply_style(is_hover=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.has_records and self.on_click:
            self.on_click(self.date_str)
        super().mousePressEvent(event)


class MeetingCalendarWidget(QWidget):
    """
    月度会议日历主看板
    """
    day_selected = pyqtSignal(str) # 抛出所选日期 'YYYY-MM-DD'

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        now = datetime.datetime.now()
        self.current_year = now.year
        self.current_month = now.month
        self.overview_data: Dict[str, Dict[str, Any]] = {}

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 14)
        main_layout.setSpacing(10)

        is_light = ThemeManager.get_instance().is_light()

        # 1. 顶栏：月份切换控制器 + 本月统计徽章卡
        self.header_card = QFrame()
        self.header_card.setObjectName("cal_header_card")
        self._update_header_card_style(is_light)

        h_layout = QHBoxLayout(self.header_card)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(10)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 上个月按钮
        self.btn_prev_month = QPushButton()
        self.btn_prev_month.setFixedSize(30, 30)
        self.btn_prev_month.setIconSize(QSize(14, 14))
        self.btn_prev_month.setToolTip("上个月")
        self.btn_prev_month.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_month.clicked.connect(self._go_prev_month)
        h_layout.addWidget(self.btn_prev_month)

        # 当前月份标题
        self.lbl_month_title = QLabel(f"{self.current_year} 年 {self.current_month} 月")
        self.lbl_month_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {'#0F172A' if is_light else '#FFFFFF'};")
        h_layout.addWidget(self.lbl_month_title)

        # 下个月按钮
        self.btn_next_month = QPushButton()
        self.btn_next_month.setFixedSize(30, 30)
        self.btn_next_month.setIconSize(QSize(14, 14))
        self.btn_next_month.setToolTip("下个月")
        self.btn_next_month.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_month.clicked.connect(self._go_next_month)
        h_layout.addWidget(self.btn_next_month)

        # 回到今天按钮
        self.btn_today = QPushButton("回到今天")
        self.btn_today.setFixedHeight(30)
        self.btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_today.clicked.connect(self._go_today)
        h_layout.addWidget(self.btn_today)

        h_layout.addStretch(1)

        # 右侧：本月统计标识
        self.lbl_month_stats = QLabel("本月统计加载中...")
        self.lbl_month_stats.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {'#0284C7' if is_light else '#38BDF8'};")
        h_layout.addWidget(self.lbl_month_stats)

        main_layout.addWidget(self.header_card)

        # 2. 星期表头行 (周一 ~ 周日)
        self.weekdays_bar = QFrame()
        w_layout = QHBoxLayout(self.weekdays_bar)
        w_layout.setContentsMargins(4, 4, 4, 4)
        w_layout.setSpacing(6)
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for day_name in weekdays:
            lbl = QLabel(day_name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#64748B" if is_light else "#94A3B8"
            lbl.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {color};")
            w_layout.addWidget(lbl, 1)
        main_layout.addWidget(self.weekdays_bar)

        # 3. 日历网格容器
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(6)
        main_layout.addWidget(self.grid_container, 1)

        self._update_nav_button_styles(is_light)

    def _update_header_card_style(self, is_light: bool):
        if is_light:
            self.header_card.setStyleSheet("""
                QFrame#cal_header_card {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 10px;
                }
            """)
        else:
            self.header_card.setStyleSheet("""
                QFrame#cal_header_card {
                    background-color: #11141D;
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    border-radius: 10px;
                }
            """)

    def _update_nav_button_styles(self, is_light: bool):
        btn_style_light = """
            QPushButton {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 11.5px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(2, 132, 199, 0.08);
                border-color: #0284C7;
                color: #0284C7;
            }
        """
        btn_style_dark = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 11.5px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(38, 176, 228, 0.15);
                border-color: #38BDF8;
                color: #38BDF8;
            }
        """
        cur_style = btn_style_light if is_light else btn_style_dark
        self.btn_prev_month.setStyleSheet(cur_style)
        self.btn_next_month.setStyleSheet(cur_style)
        self.btn_today.setStyleSheet(cur_style)
        self.btn_prev_month.setIcon(get_symbol_icon("chevron_left", color="#475569" if is_light else "#CBD5E1", size=14))
        self.btn_next_month.setIcon(get_symbol_icon("chevron_right", color="#475569" if is_light else "#CBD5E1", size=14))

    def _go_prev_month(self):
        if self.current_month == 1:
            self.current_year -= 1
            self.current_month = 12
        else:
            self.current_month -= 1
        self._on_month_changed()

    def _go_next_month(self):
        if self.current_month == 12:
            self.current_year += 1
            self.current_month = 1
        else:
            self.current_month += 1
        self._on_month_changed()

    def _go_today(self):
        now = datetime.datetime.now()
        self.current_year = now.year
        self.current_month = now.month
        self._on_month_changed()

    def _on_month_changed(self):
        is_light = ThemeManager.get_instance().is_light()
        self.lbl_month_title.setText(f"{self.current_year} 年 {self.current_month} 月")
        self.lbl_month_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {'#0F172A' if is_light else '#FFFFFF'};")
        # 触发父容器拉取数据并重新渲染
        if hasattr(self, "on_month_changed_callback") and self.on_month_changed_callback:
            self.on_month_changed_callback(self.current_year, self.current_month)

    def set_month_data(self, year: int, month: int, overview_dict: Dict[str, Dict[str, Any]]):
        self.current_year = year
        self.current_month = month
        self.overview_data = overview_dict

        is_light = ThemeManager.get_instance().is_light()
        self.lbl_month_title.setText(f"{self.current_year} 年 {self.current_month} 月")
        self.lbl_month_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {'#0F172A' if is_light else '#FFFFFF'};")

        # 统计汇总
        days_with_meetings = len(overview_dict)
        total_slices = sum(v.get("total_count", 0) for v in overview_dict.values())
        useful_slices = sum(v.get("useful_count", 0) for v in overview_dict.values())

        if days_with_meetings > 0:
            self.lbl_month_stats.setText(f"📅 本月共计 {days_with_meetings} 天有会议 · 沉淀 {useful_slices} 段有效记忆")
        else:
            self.lbl_month_stats.setText("本月暂无会议记录")

        self._render_grid()

    def _render_grid(self):
        # 清除旧单元格
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        is_light = ThemeManager.get_instance().is_light()
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # 获取月份星期排布
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        for r_idx, week in enumerate(cal):
            for c_idx, day_num in enumerate(week):
                if day_num == 0:
                    # 空单元格
                    card = DayCard(
                        date_str="",
                        day_num=0,
                        is_current_month=False,
                        day_data=None,
                        is_today=False,
                        is_light=is_light,
                        on_click=None
                    )
                else:
                    date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day_num:02d}"
                    day_info = self.overview_data.get(date_str)
                    card = DayCard(
                        date_str=date_str,
                        day_num=day_num,
                        is_current_month=True,
                        day_data=day_info,
                        is_today=(date_str == today_str),
                        is_light=is_light,
                        on_click=self._handle_day_click
                    )
                self.grid_layout.addWidget(card, r_idx, c_idx)

    def _handle_day_click(self, date_str: str):
        self.day_selected.emit(date_str)

    def update_theme(self, is_light: bool):
        self._update_header_card_style(is_light)
        self._update_nav_button_styles(is_light)
        self.lbl_month_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {'#0F172A' if is_light else '#FFFFFF'};")
        self.lbl_month_stats.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {'#0284C7' if is_light else '#38BDF8'};")
        for i in range(self.weekdays_bar.layout().count()):
            w = self.weekdays_bar.layout().itemAt(i).widget()
            if isinstance(w, QLabel):
                w.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {'#64748B' if is_light else '#94A3B8'};")
        self._render_grid()
