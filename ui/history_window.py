from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QTextBrowser, QSplitter, QPushButton, QLineEdit
)
from core.knowledge_engine import MeetingStore

class HistoryWindow(QWidget):
    """
    历史会议资产浏览窗口：查看所有沉淀的会议切片与结构化纪要
    """
    def __init__(self, meeting_store: MeetingStore):
        super().__init__()
        self.store = meeting_store
        self.setWindowTitle("DeskEcho - 历史会议记忆库")
        self.resize(800, 520)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # 顶部工具栏
        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("在会议记忆中搜索关键词...")
        self.search_input.returnPressed.connect(self._do_search)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._do_search)

        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.load_records)

        top_bar.addWidget(self.search_input, 1)
        top_bar.addWidget(search_btn)
        top_bar.addWidget(refresh_btn)
        layout.addLayout(top_bar)

        # 主内容区域 (左侧列表，右侧详细纪要)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_item_selected)
        splitter.addWidget(self.list_widget)

        self.detail_browser = QTextBrowser()
        self.detail_browser.setOpenExternalLinks(True)
        splitter.addWidget(self.detail_browser)
        splitter.setSizes([260, 540])

        layout.addWidget(splitter)
        self.records = []

    def load_records(self):
        self.records = self.store.query_recent(limit=50)
        self.list_widget.clear()
        self.detail_browser.clear()
        
        if not self.records:
            self.detail_browser.setHtml("<p style='color:gray;'>暂无历史会议记录。开启会议录音后，系统将自动切片归档并提取纪要。</p>")
            return

        for rec in self.records:
            time_display = f"{rec.get('start_time', '')}"
            summary_snippet = (rec.get('summary') or '无摘要')[:30].replace("\n", " ")
            item = QListWidgetItem(f"{time_display}\n  {summary_snippet}...")
            self.list_widget.addItem(item)
        
        self.list_widget.setCurrentRow(0)

    def _on_item_selected(self, row: int):
        if row < 0 or row >= len(self.records):
            return
        rec = self.records[row]
        html = f"""
        <div style="font-family: sans-serif; padding: 10px;">
            <h3 style="color: #2563EB; margin-bottom: 4px;">会议时间跨度</h3>
            <p><b>开始时间:</b> {rec.get('start_time')}<br>
               <b>结束时间:</b> {rec.get('end_time')}</p>
            
            <h3 style="color: #059669; margin-top: 15px; margin-bottom: 4px;">结构化提炼纪要</h3>
            <div style="background-color: #F3F4F6; padding: 10px; border-radius: 6px; white-space: pre-wrap;">
                {rec.get('summary', '')}
            </div>

            <h3 style="color: #4B5563; margin-top: 15px; margin-bottom: 4px;">原始语音转录</h3>
            <div style="background-color: #F9FAFB; padding: 10px; border: 1px solid #E5E7EB; border-radius: 6px; white-space: pre-wrap; font-size: 13px;">
                {rec.get('raw_text', '')}
            </div>
        </div>
        """
        self.detail_browser.setHtml(html)

    def _do_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            self.load_records()
            return
        results = self.store.query_vector(keyword, n_results=20)
        self.list_widget.clear()
        self.records = []
        for r in results:
            meta = r.get("metadata", {})
            self.records.append({
                "start_time": meta.get("start_time", ""),
                "end_time": meta.get("end_time", ""),
                "summary": r.get("content", ""),
                "raw_text": ""
            })
            self.list_widget.addItem(f"{meta.get('start_time', '')}\n  {r.get('content')[:35]}...")
        if self.records:
            self.list_widget.setCurrentRow(0)
