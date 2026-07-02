import sys
import os
import re
import json

# Compatibility wrapper between PyQt5 and PySide6
try:
    from PyQt5.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal as Signal, pyqtSlot as Slot
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
        QLineEdit, QPushButton, QPlainTextEdit, QFrame, QComboBox,
        QCheckBox, QGraphicsDropShadowEffect, QSpinBox, QProgressBar,
        QDialog, QTabWidget, QScrollArea
    )
    from PyQt5.QtGui import QColor, QPalette
    USING_PYSIDE = False
except ImportError:
    from PySide6.QtCore import Qt, QPoint, QTimer, QThread, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
        QLineEdit, QPushButton, QPlainTextEdit, QFrame, QComboBox,
        QCheckBox, QGraphicsDropShadowEffect, QSpinBox, QProgressBar,
        QDialog, QTabWidget, QScrollArea
    )
    from PySide6.QtGui import QColor, QPalette
    USING_PYSIDE = True

# Import custom OOP components
from config_manager import load_config, save_config
from chrome_automation import ChromeAutomation
from gemini_client import GeminiClient
from gui_workers import (
    SpeedControllerWorker, AutoLearnWorker, 
    AIScanWorker, AISolveWorker, AISolveAllWorker, format_time,
    PromptGenWorker, WebClickWorker
)

class FloatingSpeedApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.drag_position = QPoint()
        self.automation = ChromeAutomation(self.config["debug_port"])
        self.client = GeminiClient(api_keys=self.config.get("api_keys", []))
        
        # State variables for details and progress tracking
        self.current_q_text = ""
        self.current_solution = ""
        self.current_q_num = 1
        self.total_q_count = 1
        self.current_options_list = []
        self.solved_answers_all = {}
        self.scanned_prompt_text = ""
        
        self.prompt_gen_worker = None
        self.web_click_worker = None
        self.solve_all_worker = None
        self.worker = None
        self.auto_worker = None
        
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1260, 820)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QWidget(self)
        self.container.setObjectName("Container")
        
        self.container.setStyleSheet("""
            QWidget#Container {
                background-color: #ffffff;
                border: 2px solid #0ea5e9;
                border-radius: 16px;
            }
            QFrame.Card {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QFrame.Card:hover {
                border: 1px solid #bae6fd;
                background-color: #f0f9ff;
            }
            QLabel {
                color: #0f172a;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: bold;
            }
            QLabel#TitleLabel {
                color: #0369a1;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLabel.SectionTitle {
                color: #0ea5e9;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                color: #0f172a;
                padding: 6px 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9.5px;
            }
            QLineEdit:focus {
                border: 1px solid #0ea5e9;
                background-color: #ffffff;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                color: #0f172a;
                padding: 4px 8px;
                font-size: 9.5px;
            }
            QSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                color: #0f172a;
                padding: 3px 6px;
                font-size: 9.5px;
            }
            QCheckBox {
                color: #334155;
                font-size: 9.5px;
                font-weight: normal;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0ea5e9, stop:1 #0284c7);
                border: none;
                border-radius: 6px;
                color: white;
                font-family: 'Inter', sans-serif;
                font-size: 9.5px;
                font-weight: bold;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #0ea5e9);
            }
            QPushButton#LaunchBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ea580c, stop:1 #c2410c);
            }
            QPushButton#LaunchBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f97316, stop:1 #ea580c);
            }
            QPushButton#CloseBtn {
                background: transparent;
                color: #ef4444;
                font-size: 13px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton#CloseBtn:hover {
                background-color: rgba(239, 68, 68, 0.1);
            }
            QPushButton#MinBtn {
                background: transparent;
                color: #f59e0b;
                font-size: 13px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton#MinBtn:hover {
                background-color: rgba(245, 158, 11, 0.1);
            }
            QPlainTextEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                color: #0f172a;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5px;
                padding: 6px;
            }
            QFrame#Separator {
                background-color: #cbd5e1;
                max-height: 1px;
            }
            QFrame#VertSeparator {
                background-color: #cbd5e1;
                max-width: 1px;
            }
            QProgressBar {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                text-align: center;
                color: #0f172a;
                font-family: 'Inter', sans-serif;
                font-size: 10px;
                font-weight: bold;
                height: 16px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #0ea5e9);
                border-radius: 5px;
            }
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # --- Custom Title Bar ---
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(15, 10, 15, 5)

        title_icon = QLabel("🪐", self.container)
        title_icon.setStyleSheet("font-size: 15px;")
        title_bar.addWidget(title_icon)

        title_lbl = QLabel("LMS STUDY AUTOMATION CONSOLE PRO", self.container)
        title_lbl.setObjectName("TitleLabel")
        title_bar.addWidget(title_lbl)

        title_bar.addStretch()

        # Column Toggle Buttons
        self.toggle_col1_btn = QPushButton("🌐 Chrome", self.container)
        self.toggle_col1_btn.setObjectName("ToggleCol1Btn")
        self.toggle_col1_btn.setCheckable(True)
        self.toggle_col1_btn.setChecked(True)
        
        self.toggle_col2_btn = QPushButton("📹 Video", self.container)
        self.toggle_col2_btn.setObjectName("ToggleCol2Btn")
        self.toggle_col2_btn.setCheckable(True)
        self.toggle_col2_btn.setChecked(True)
        
        self.toggle_col3_btn = QPushButton("📝 Trắc nghiệm", self.container)
        self.toggle_col3_btn.setObjectName("ToggleCol3Btn")
        self.toggle_col3_btn.setCheckable(True)
        self.toggle_col3_btn.setChecked(True)
        
        btn_toggle_style = """
            QPushButton#ToggleCol1Btn, QPushButton#ToggleCol2Btn, QPushButton#ToggleCol3Btn {
                background: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                font-family: 'Inter', sans-serif;
                font-size: 11px;
                padding: 3px 8px;
                font-weight: bold;
            }
            QPushButton#ToggleCol1Btn:checked, QPushButton#ToggleCol2Btn:checked, QPushButton#ToggleCol3Btn:checked {
                background: #e0f2fe;
                color: #0369a1;
                border: 1px solid #7dd3fc;
            }
            QPushButton#ToggleCol1Btn:hover, QPushButton#ToggleCol2Btn:hover, QPushButton#ToggleCol3Btn:hover {
                background: #e2e8f0;
            }
        """
        self.toggle_col1_btn.setStyleSheet(btn_toggle_style)
        self.toggle_col2_btn.setStyleSheet(btn_toggle_style)
        self.toggle_col3_btn.setStyleSheet(btn_toggle_style)
        
        self.toggle_col1_btn.clicked.connect(self.update_columns_visibility)
        self.toggle_col2_btn.clicked.connect(self.update_columns_visibility)
        self.toggle_col3_btn.clicked.connect(self.update_columns_visibility)
        
        title_bar.addWidget(self.toggle_col1_btn)
        title_bar.addWidget(self.toggle_col2_btn)
        title_bar.addWidget(self.toggle_col3_btn)
        title_bar.addSpacing(10)

        self.min_btn = QPushButton("➖", self.container)
        self.min_btn.setObjectName("MinBtn")
        self.min_btn.setFixedSize(24, 24)
        self.min_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(self.min_btn)

        self.close_btn = QPushButton("❌", self.container)
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close)
        title_bar.addWidget(self.close_btn)

        container_layout.addLayout(title_bar)

        # Thin separator line
        sep = QFrame(self.container)
        sep.setObjectName("Separator")
        container_layout.addWidget(sep)

        # --- Workspace Layout (Horizontal Split) ---
        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(10, 5, 10, 10)
        workspace_layout.setSpacing(12)

        # =========================================================================
        # COLUMN 1: KẾT NỐI TRÌNH DUYỆT (BROWSER CONNECTION) - WIDTH ~360px
        # =========================================================================
        col1_panel = QWidget(self.container)
        self.col1_panel = col1_panel
        col1_panel.setFixedWidth(380)
        col1_layout = QVBoxLayout(col1_panel)
        col1_layout.setContentsMargins(10, 10, 10, 10)
        col1_layout.setSpacing(8)

        # CARD 1: CẤU HÌNH TRÌNH DUYỆT (BROWSER CARD)
        card_browser = QFrame(col1_panel)
        card_browser.setProperty("class", "Card")
        card_browser_layout = QVBoxLayout(card_browser)
        card_browser_layout.setContentsMargins(10, 8, 10, 8)
        card_browser_layout.setSpacing(6)

        lbl1 = QLabel("1. KẾT NỐI TRÌNH DUYỆT & LINK", card_browser)
        lbl1.setProperty("class", "SectionTitle")
        card_browser_layout.addWidget(lbl1)

        self.launch_btn = QPushButton("🌐 MỞ CHROME CHẾ ĐỘ DEBUG", card_browser)
        self.launch_btn.setObjectName("LaunchBtn")
        self.launch_btn.clicked.connect(self.launch_chrome_debug)
        card_browser_layout.addWidget(self.launch_btn)

        # URL Input & Get Active Link row
        url_row_layout = QHBoxLayout()
        url_row_layout.setSpacing(4)

        self.url_input = QLineEdit(card_browser)
        self.url_input.setPlaceholderText("Dán link bài học để nhận diện tab...")
        self.url_input.setText(self.config["last_url"])
        self.url_input.setCursorPosition(0)
        self.url_input.textChanged.connect(self.save_url)
        self.url_input.editingFinished.connect(lambda: self.url_input.setCursorPosition(0))
        url_row_layout.addWidget(self.url_input, stretch=3)

        self.get_url_btn = QPushButton("🔗 LẤY LINK ĐANG MỞ", card_browser)
        self.get_url_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.get_url_btn.clicked.connect(self.fetch_active_tab_url)
        url_row_layout.addWidget(self.get_url_btn, stretch=1)

        card_browser_layout.addLayout(url_row_layout)

        col1_layout.addWidget(card_browser)

        # Connection console section
        lbl_conn_log = QLabel("🗂️ NHẬT KÝ KẾT NỐI HỆ THỐNG:", col1_panel)
        lbl_conn_log.setStyleSheet("color: #0369a1; font-weight: bold;")
        col1_layout.addWidget(lbl_conn_log)

        self.connection_console = QPlainTextEdit(col1_panel)
        self.connection_console.setReadOnly(True)
        self.connection_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #0369a1;
                border: 1px solid #bae6fd;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9.5px;
            }
        """)
        col1_layout.addWidget(self.connection_console)

        workspace_layout.addWidget(col1_panel, stretch=33)

        # Separator 1
        v_sep1 = QFrame(self.container)
        self.v_sep1 = v_sep1
        v_sep1.setObjectName("VertSeparator")
        workspace_layout.addWidget(v_sep1)

        # =========================================================================
        # COLUMN 2: CẤU HÌNH & TỰ ĐỘNG HỌC VIDEO - WIDTH ~360px
        # =========================================================================
        col2_panel = QWidget(self.container)
        self.col2_panel = col2_panel
        col2_panel.setFixedWidth(380)
        col2_layout = QVBoxLayout(col2_panel)
        col2_layout.setContentsMargins(10, 10, 10, 10)
        col2_layout.setSpacing(8)

        # CARD 2: CẤU HÌNH PHÁT (CONFIG CARD)
        card_config = QFrame(col2_panel)
        card_config.setProperty("class", "Card")
        card_config_layout = QVBoxLayout(card_config)
        card_config_layout.setContentsMargins(10, 8, 10, 8)
        card_config_layout.setSpacing(6)

        lbl2 = QLabel("2. CẤU HÌNH PHÁT VIDEO", card_config)
        lbl2.setProperty("class", "SectionTitle")
        card_config_layout.addWidget(lbl2)

        config_row1 = QHBoxLayout()
        config_row1.addWidget(QLabel("Tốc độ phát:", card_config))
        self.speed_combo = QComboBox(card_config)
        self.speed_combo.addItems(["2.0", "3.0", "4.0", "5.0", "8.0", "16.0"])
        idx = self.speed_combo.findText(self.config["speed"])
        if idx >= 0:
            self.speed_combo.setCurrentIndex(idx)
        else:
            self.speed_combo.setCurrentText(self.config["speed"])
        self.speed_combo.currentTextChanged.connect(self.save_speed)
        config_row1.addWidget(self.speed_combo)

        self.mute_cb = QCheckBox("🔇 Tắt tiếng", card_config)
        self.mute_cb.setChecked(self.config["mute_video"])
        self.mute_cb.stateChanged.connect(self.save_mute)
        config_row1.addWidget(self.mute_cb)
        card_config_layout.addLayout(config_row1)

        config_row2 = QHBoxLayout()
        config_row2.addWidget(QLabel("Giây còn lại chặng cuối:", card_config))
        self.seconds_spin = QSpinBox(card_config)
        self.seconds_spin.setRange(2, 600)
        self.seconds_spin.setValue(self.config["remaining_seconds"])
        self.seconds_spin.valueChanged.connect(self.save_seconds)
        self.seconds_spin.setFixedWidth(70)
        config_row2.addWidget(self.seconds_spin)
        card_config_layout.addLayout(config_row2)

        col2_layout.addWidget(card_config)

        # CARD 3: ĐIỀU KHIỂN THỦ CÔNG
        card_manual = QFrame(col2_panel)
        card_manual.setProperty("class", "Card")
        card_manual_layout = QVBoxLayout(card_manual)
        card_manual_layout.setContentsMargins(10, 8, 10, 8)
        card_manual_layout.setSpacing(6)

        lbl3 = QLabel("3. ĐIỀU KHIỂN THỦ CÔNG", card_manual)
        lbl3.setProperty("class", "SectionTitle")
        card_manual_layout.addWidget(lbl3)

        manual_btn_layout = QHBoxLayout()
        self.action_btn = QPushButton("⚡ CHỈ TĂNG TỐC", card_manual)
        self.action_btn.clicked.connect(self.start_speed_only)
        manual_btn_layout.addWidget(self.action_btn)

        self.skip_btn = QPushButton("⏩ TUA SÁT CUỐI", card_manual)
        self.skip_btn.setObjectName("SkipBtn")
        self.skip_btn.clicked.connect(self.start_skip_only)
        manual_btn_layout.addWidget(self.skip_btn)
        card_manual_layout.addLayout(manual_btn_layout)

        col2_layout.addWidget(card_manual)

        # CARD 4: TỰ ĐỘNG HỌC
        card_auto = QFrame(col2_panel)
        card_auto.setProperty("class", "Card")
        card_auto_layout = QVBoxLayout(card_auto)
        card_auto_layout.setContentsMargins(10, 8, 10, 8)
        card_auto_layout.setSpacing(6)

        lbl4 = QLabel("4. TỰ ĐỘNG HỌC TOÀN BỘ (AUTO-LEARN)", card_auto)
        lbl4.setProperty("class", "SectionTitle")
        card_auto_layout.addWidget(lbl4)

        row_layout = QHBoxLayout()
        self.auto_skip_cb = QCheckBox("⏩ Tự động tua video", card_auto)
        self.auto_skip_cb.setChecked(self.config["auto_skip_video"])
        self.auto_skip_cb.stateChanged.connect(self.save_auto_skip)
        row_layout.addWidget(self.auto_skip_cb)
        
        row_layout.addWidget(QLabel("Trạng thái:", card_auto))
        self.auto_status_lbl = QLabel("TẮT", card_auto)
        self.auto_status_lbl.setStyleSheet("color: #71717a; font-weight: bold;")
        row_layout.addWidget(self.auto_status_lbl)
        row_layout.addStretch()
        card_auto_layout.addLayout(row_layout)

        self.auto_btn = QPushButton("▶ KÍCH HOẠT TỰ ĐỘNG HỌC", card_auto)
        self.auto_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        self.auto_btn.clicked.connect(self.toggle_auto_learn)
        card_auto_layout.addWidget(self.auto_btn)

        col2_layout.addWidget(card_auto)

        # Progress bar
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar(col2_panel)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.time_lbl = QLabel("00:00 / 00:00", col2_panel)
        self.time_lbl.setFixedWidth(85)
        self.time_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        progress_layout.addWidget(self.time_lbl)
        col2_layout.addLayout(progress_layout)

        # Video console section
        lbl_vid_log = QLabel("🗂️ NHẬT KÝ TIẾN TRÌNH VIDEO:", col2_panel)
        lbl_vid_log.setStyleSheet("color: #0d9488; font-weight: bold;")
        col2_layout.addWidget(lbl_vid_log)

        self.video_console = QPlainTextEdit(col2_panel)
        self.video_console.setReadOnly(True)
        self.video_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #0d9488;
                border: 1px solid #ccfbf1;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9.5px;
            }
        """)
        col2_layout.addWidget(self.video_console)

        workspace_layout.addWidget(col2_panel, stretch=34)

        # Separator 2
        v_sep2 = QFrame(self.container)
        self.v_sep2 = v_sep2
        v_sep2.setObjectName("VertSeparator")
        workspace_layout.addWidget(v_sep2)

        # =========================================================================
        # COLUMN 3: TRỢ LÝ GIẢI BÀI AI (AI QUIZ ASSISTANT) - WIDTH ~390px
        # =========================================================================
        col3_panel = QWidget(self.container)
        self.col3_panel = col3_panel
        col3_panel.setFixedWidth(410)
        col3_layout = QVBoxLayout(col3_panel)
        col3_layout.setContentsMargins(10, 10, 10, 10)
        col3_layout.setSpacing(8)

        ai_header_layout = QHBoxLayout()
        lbl_ai = QLabel("🤖 TRỢ LÝ TRẮC NGHIỆM", col3_panel)
        lbl_ai.setProperty("class", "SectionTitle")
        ai_header_layout.addWidget(lbl_ai)

        self.ai_settings_btn = QPushButton("⚙️ API", col3_panel)
        self.ai_settings_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                border: 1px solid #cbd5e1;
            }
            QPushButton:hover {
                background: #cbd5e1;
                color: #0ea5e9;
            }
        """)
        self.ai_settings_btn.setFixedWidth(55)
        self.ai_settings_btn.clicked.connect(self.open_api_settings)
        ai_header_layout.addWidget(self.ai_settings_btn)

        self.ai_minimize_btn = QPushButton("👁️", col3_panel)
        self.ai_minimize_btn.setToolTip("Thu nhỏ siêu gọn")
        self.ai_minimize_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
                border: 1px solid #cbd5e1;
            }
            QPushButton:hover {
                background: #cbd5e1;
                color: #0ea5e9;
            }
        """)
        self.ai_minimize_btn.setFixedWidth(28)
        self.ai_minimize_btn.clicked.connect(self.toggle_compact_mode)
        ai_header_layout.addWidget(self.ai_minimize_btn)
        
        col3_layout.addLayout(ai_header_layout)

        # Giao diện Quiz layout
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 4, 0, 4)
        mode_lbl = QLabel("Giao diện Quiz:", col3_panel)
        mode_lbl.setStyleSheet("font-weight: bold; color: #475569; font-size: 11px;")
        mode_layout.addWidget(mode_lbl)
        
        self.quiz_mode_cb = QComboBox(col3_panel)
        self.quiz_mode_cb.addItem("Tự động nhận diện", "auto")
        self.quiz_mode_cb.addItem("1 câu / trang", "single")
        self.quiz_mode_cb.addItem("Nhiều câu / trang", "multi")
        self.quiz_mode_cb.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px 6px;
                color: #0f172a;
                font-weight: bold;
                font-size: 11px;
                min-width: 140px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        idx_quiz_mode = self.quiz_mode_cb.findData(self.config.get("quiz_mode", "auto"))
        if idx_quiz_mode >= 0:
            self.quiz_mode_cb.setCurrentIndex(idx_quiz_mode)
        self.quiz_mode_cb.currentIndexChanged.connect(self.save_quiz_mode)
        mode_layout.addWidget(self.quiz_mode_cb)
        mode_layout.addStretch()
        
        col3_layout.addLayout(mode_layout)

        # --- TAB WIDGET ---
        self.ai_tab_widget = QTabWidget(col3_panel)
        self.ai_tab_widget.setUsesScrollButtons(False)
        self.ai_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cbd5e1;
                background: #ffffff;
                border-radius: 6px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: #f1f5f9;
                color: #64748b;
                border: 1px solid #cbd5e1;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #0ea5e9;
                border-bottom: 1px solid #ffffff;
            }
            QTabBar::tab:hover {
                background: #e2e8f0;
                color: #0f172a;
            }
        """)

        # --- TAB 1: WEB MODE (PRIORITIZED & CUSTOMIZED) ---
        tab_web = QWidget()
        tab_web_layout = QVBoxLayout(tab_web)
        tab_web_layout.setContentsMargins(6, 6, 6, 6)
        tab_web_layout.setSpacing(6)

        # 1. Info / Guide Card
        card_web_guide = QFrame(tab_web)
        card_web_guide.setProperty("class", "Card")
        card_web_guide_layout = QVBoxLayout(card_web_guide)
        card_web_guide_layout.setContentsMargins(10, 8, 10, 8)
        card_web_guide_layout.setSpacing(4)

        guide_lbl = QLabel(
            "💡 HƯỚNG DẪN DÙNG WEB AI MIỄN PHÍ:\n"
            "1. Chọn số câu cần quét rồi bấm 'BẮT ĐẦU QUÉT'.\n"
            "2. Bấm 'SAO CHÉP PROMPT AI' (nút sẽ hiện sáng khi quét xong).\n"
            "3. Dán (Ctrl+V) vào ChatGPT / Gemini Web.\n"
            "4. Sao chép đoạn mã JSON đáp án AI trả về.\n"
            "5. Dán JSON vào ô dưới và bấm 'BẮT ĐẦU AUTO-CLICK'.",
            card_web_guide
        )
        guide_lbl.setStyleSheet("color: #475569; font-size: 10.5px; line-height: 1.4;")
        guide_lbl.setWordWrap(True)
        card_web_guide_layout.addWidget(guide_lbl)
        tab_web_layout.addWidget(card_web_guide)

        # Quét câu hỏi config row
        scan_cfg_layout = QHBoxLayout()
        scan_cfg_layout.addWidget(QLabel("Số câu quét:", tab_web))
        self.web_scan_limit_spin = QSpinBox(tab_web)
        self.web_scan_limit_spin.setRange(0, 100)
        self.web_scan_limit_spin.setValue(0)  # 0 means all
        self.web_scan_limit_spin.setSpecialValueText("Tất cả")
        self.web_scan_limit_spin.setSuffix(" câu")
        scan_cfg_layout.addWidget(self.web_scan_limit_spin)
        tab_web_layout.addLayout(scan_cfg_layout)

        # 2. Prompt generator buttons
        scan_btns_layout = QHBoxLayout()
        self.web_scan_btn = QPushButton("🔍 BẮT ĐẦU QUÉT", tab_web)
        self.web_scan_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0ea5e9, stop:1 #0284c7);
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #0ea5e9);
            }
        """)
        self.web_scan_btn.clicked.connect(self.trigger_web_copy_prompt)
        scan_btns_layout.addWidget(self.web_scan_btn)

        self.web_copy_prompt_btn = QPushButton("📋 SAO CHÉP PROMPT AI", tab_web)
        self.web_copy_prompt_btn.setEnabled(False)  # Disabled until scan finished
        self.web_copy_prompt_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #6d28d9);
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a78bfa, stop:1 #8b5cf6);
            }
            QPushButton:disabled {
                background: #cbd5e1;
                color: #94a3b8;
            }
        """)
        self.web_copy_prompt_btn.clicked.connect(self.copy_scanned_prompt_clipboard)
        scan_btns_layout.addWidget(self.web_copy_prompt_btn)
        tab_web_layout.addLayout(scan_btns_layout)

        # 3. JSON input area
        tab_web_layout.addWidget(QLabel("DÁN JSON ĐÁP ÁN TỪ AI WEB VÀO ĐÂY:", tab_web))
        self.web_json_input = QPlainTextEdit(tab_web)
        self.web_json_input.setPlaceholderText('Ví dụ:\n{\n  "1": "A",\n  "2": "C",\n  "3": "B"\n}')
        self.web_json_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                font-family: 'Consolas', monospace;
                font-size: 9.5px;
            }
        """)
        tab_web_layout.addWidget(self.web_json_input)

        # 4. Action buttons
        web_actions = QHBoxLayout()
        self.web_start_click_btn = QPushButton("⚡ BẮT ĐẦU AUTO-CLICK", tab_web)
        self.web_start_click_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #047857);
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        self.web_start_click_btn.clicked.connect(self.trigger_web_auto_click)
        web_actions.addWidget(self.web_start_click_btn)

        self.web_stop_click_btn = QPushButton("🛑 DỪNG AUTO-CLICK", tab_web)
        self.web_stop_click_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #b91c1c);
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f87171, stop:1 #ef4444);
            }
        """)
        self.web_stop_click_btn.clicked.connect(self.stop_web_auto_click)
        self.web_stop_click_btn.setVisible(False)
        web_actions.addWidget(self.web_stop_click_btn)

        tab_web_layout.addLayout(web_actions)

        self.ai_tab_widget.addTab(tab_web, "📋 GIẢI WEB AI")

        # --- TAB 2: API MODE (WITH KEY REQUIREMENT WARNING) ---
        tab_api = QWidget()
        tab_api_layout = QVBoxLayout(tab_api)
        tab_api_layout.setContentsMargins(6, 6, 6, 6)
        tab_api_layout.setSpacing(6)

        # Warning card
        warning_card = QFrame(tab_api)
        warning_card.setStyleSheet("""
            QFrame {
                background-color: #fffbeb;
                border: 1px solid #fef3c7;
                border-radius: 8px;
            }
            QLabel {
                color: #b45309;
                font-size: 10px;
                font-weight: normal;
                line-height: 1.3;
            }
        """)
        warning_card_layout = QVBoxLayout(warning_card)
        warning_card_layout.setContentsMargins(8, 6, 8, 6)
        warning_lbl = QLabel(
            "⚠️ LƯU Ý CHẾ ĐỘ API: Hãy đảm bảo đã nhập API Key trước khi chạy.\n"
            "Khuyến nghị nên dùng chế độ 'GIẢI WEB AI (MIỄN PHÍ)' vì an toàn, không tốn quota và hoàn toàn miễn phí!",
            warning_card
        )
        warning_lbl.setWordWrap(True)
        warning_card_layout.addWidget(warning_lbl)
        tab_api_layout.addWidget(warning_card)

        # CARD AI CONFIG: Cấu hình quét
        card_ai_config = QFrame(tab_api)
        card_ai_config.setProperty("class", "Card")
        card_ai_config_layout = QVBoxLayout(card_ai_config)
        card_ai_config_layout.setContentsMargins(10, 6, 10, 6)
        card_ai_config_layout.setSpacing(4)

        self.ai_auto_fill_cb = QCheckBox("✍️ Tự động chọn đáp án đúng (Auto-click)", card_ai_config)
        self.ai_auto_fill_cb.setChecked(self.config["ai_auto_fill"])
        self.ai_auto_fill_cb.stateChanged.connect(self.save_ai_auto_fill)
        card_ai_config_layout.addWidget(self.ai_auto_fill_cb)

        self.ai_skip_img_cb = QCheckBox("🖼️ Bỏ qua câu hỏi có hình ảnh / sơ đồ", card_ai_config)
        self.ai_skip_img_cb.setChecked(self.config["ai_skip_img"])
        self.ai_skip_img_cb.stateChanged.connect(self.save_ai_skip_img)
        card_ai_config_layout.addWidget(self.ai_skip_img_cb)

        tab_api_layout.addWidget(card_ai_config)

        # CARD AI QUESTIONS: Câu hỏi quét được
        self.card_ai_q = QFrame(tab_api)
        self.card_ai_q.setProperty("class", "Card")
        self.card_ai_q_layout = QVBoxLayout(self.card_ai_q)
        self.card_ai_q_layout.setContentsMargins(10, 6, 10, 6)
        self.card_ai_q_layout.setSpacing(4)

        self.card_ai_q_layout.addWidget(QLabel("NỘI DUNG CÂU HỎI NHẬN DIỆN ĐƯỢC:", self.card_ai_q))
        self.ai_question_text = QPlainTextEdit(self.card_ai_q)
        self.ai_question_text.setReadOnly(False)
        self.ai_question_text.setPlaceholderText("Nội dung câu hỏi quét được sẽ hiển thị tại đây...")
        self.ai_question_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #0ea5e9;
                border: 1px solid #bae6fd;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9.5px;
            }
        """)
        self.card_ai_q_layout.addWidget(self.ai_question_text)
        tab_api_layout.addWidget(self.card_ai_q, stretch=1)

        # CARD AI SUGGESTION: Đáp án gợi ý & Giải thích
        card_ai_ans = QFrame(tab_api)
        card_ai_ans.setProperty("class", "Card")
        card_ai_ans_layout = QVBoxLayout(card_ai_ans)
        card_ai_ans_layout.setContentsMargins(10, 6, 10, 6)
        card_ai_ans_layout.setSpacing(4)

        card_ai_ans_layout.addWidget(QLabel("AI PHÂN TÍCH & ĐỀ XUẤT ĐÁP ÁN:", card_ai_ans))
        self.ai_analysis_text = QPlainTextEdit(card_ai_ans)
        self.ai_analysis_text.setReadOnly(True)
        self.ai_analysis_text.setPlaceholderText("Gợi ý đáp án và giải thích từ AI...")
        self.ai_analysis_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #10b981;
                border: 1px solid #a7f3d0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9.5px;
            }
        """)
        card_ai_ans_layout.addWidget(self.ai_analysis_text)
        tab_api_layout.addWidget(card_ai_ans, stretch=1)

        # AI Action Buttons Layout
        ai_actions_layout = QVBoxLayout()
        ai_actions_layout.setSpacing(4)

        # Row 1: Scan button, Solve button, and QSpinBox for Target Question
        ai_row1_layout = QHBoxLayout()
        self.ai_scan_btn = QPushButton("🔍 QUÉT CÂU HỎI", tab_api)
        self.ai_scan_btn.clicked.connect(self.trigger_ai_scan)
        ai_row1_layout.addWidget(self.ai_scan_btn)

        self.ai_solve_btn = QPushButton("🧠 GIẢI CÂU NÀY", tab_api)
        self.ai_solve_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #6d28d9);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a78bfa, stop:1 #8b5cf6);
            }
        """)
        self.ai_solve_btn.clicked.connect(self.trigger_ai_solve)
        ai_row1_layout.addWidget(self.ai_solve_btn)

        ai_row1_layout.addWidget(QLabel("Câu:", tab_api))
        self.ai_target_q_spin = QSpinBox(tab_api)
        self.ai_target_q_spin.setRange(1, 100)
        self.ai_target_q_spin.setValue(self.config["ai_target_question"])
        self.ai_target_q_spin.setFixedWidth(50)
        self.ai_target_q_spin.valueChanged.connect(self.save_ai_target_question)
        ai_row1_layout.addWidget(self.ai_target_q_spin)
        ai_actions_layout.addLayout(ai_row1_layout)

        # Row 2: Solve all & Stop
        ai_row2_layout = QHBoxLayout()
        self.ai_solve_all_btn = QPushButton("🏆 GIẢI TỪ ĐẦU ĐẾN CUỐI", tab_api)
        self.ai_solve_all_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #047857);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        self.ai_solve_all_btn.clicked.connect(self.trigger_ai_solve_all)
        ai_row2_layout.addWidget(self.ai_solve_all_btn)

        self.ai_stop_solve_btn = QPushButton("🛑 DỪNG GIẢI", tab_api)
        self.ai_stop_solve_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #b91c1c);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f87171, stop:1 #ef4444);
            }
        """)
        self.ai_stop_solve_btn.setEnabled(False)
        self.ai_stop_solve_btn.setVisible(False)
        self.ai_stop_solve_btn.clicked.connect(self.stop_ai_solve_all)
        ai_row2_layout.addWidget(self.ai_stop_solve_btn)

        self.ai_view_answers_btn = QPushButton("📋 ĐÁP ÁN", tab_api)
        self.ai_view_answers_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #3730a3);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #4f46e5);
            }
        """)
        self.ai_view_answers_btn.setFixedWidth(95)
        self.ai_view_answers_btn.setEnabled(False)
        self.ai_view_answers_btn.clicked.connect(self.show_solved_answers_list)
        ai_row2_layout.addWidget(self.ai_view_answers_btn)

        ai_actions_layout.addLayout(ai_row2_layout)
        tab_api_layout.addLayout(ai_actions_layout)

        self.ai_tab_widget.addTab(tab_api, "⚡ GIẢI API AI")
        col3_layout.addWidget(self.ai_tab_widget, stretch=3)

        # Connect tab changes for warning notification
        self.ai_tab_widget.currentChanged.connect(self.handle_tab_changed)

        # Quiz console section
        lbl_quiz_log = QLabel("🗂️ NHẬT KÝ TRẮC NGHIỆM AI:", col3_panel)
        lbl_quiz_log.setStyleSheet("color: #7c3aed; font-weight: bold;")
        col3_layout.addWidget(lbl_quiz_log)

        self.quiz_console = QPlainTextEdit(col3_panel)
        self.quiz_console.setReadOnly(True)
        self.quiz_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #7c3aed;
                border: 1px solid #f3e8ff;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9.5px;
            }
        """)
        col3_layout.addWidget(self.quiz_console, stretch=1)

        workspace_layout.addWidget(col3_panel, stretch=33)

        container_layout.addLayout(workspace_layout)

        # --- COMPACT CONTAINER (MINIMIZED VIEW) ---
        self.compact_container = QWidget(self)
        self.compact_container.setObjectName("CompactContainer")
        self.compact_container.setStyleSheet("""
            QWidget#CompactContainer {
                background-color: #ffffff;
                border: 2px solid #0ea5e9;
                border-radius: 12px;
            }
        """)
        self.compact_container.hide()

        compact_layout = QHBoxLayout(self.compact_container)
        compact_layout.setContentsMargins(8, 4, 8, 4)
        compact_layout.setSpacing(6)

        self.compact_restore_btn = QPushButton("👁️", self.compact_container)
        self.compact_restore_btn.setToolTip("Mở lại bảng điều khiển đầy đủ")
        self.compact_restore_btn.setFixedSize(22, 22)
        self.compact_restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0f2fe;
                border: 1px solid #bae6fd;
                color: #0284c7;
                border-radius: 5px;
                padding: 2px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #bae6fd;
                color: #ffffff;
            }
        """)
        self.compact_restore_btn.clicked.connect(self.toggle_compact_mode)
        compact_layout.addWidget(self.compact_restore_btn)

        self.compact_dot_lbl = QLabel("🟢", self.compact_container)
        self.compact_dot_lbl.setFixedWidth(18)
        self.compact_dot_lbl.setAlignment(Qt.AlignCenter)
        compact_layout.addWidget(self.compact_dot_lbl)

        self.compact_status_lbl = QLabel("Hệ thống sẵn sàng...", self.compact_container)
        self.compact_status_lbl.setStyleSheet("""
            QLabel {
                color: #0ea5e9;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        compact_layout.addWidget(self.compact_status_lbl)
        compact_layout.addStretch()

        self.compact_close_btn = QPushButton("❌", self.compact_container)
        self.compact_close_btn.setFixedSize(20, 20)
        self.compact_close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ef4444;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.1);
                border-radius: 4px;
            }
        """)
        self.compact_close_btn.clicked.connect(self.close)
        compact_layout.addWidget(self.compact_close_btn)

        self.compact_timer = QTimer(self)
        self.compact_timer.timeout.connect(self.animate_compact_mode)
        self.compact_dots = 0

        main_layout.addWidget(self.compact_container)
        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
        
        self.prompt_gen_worker = None
        self.web_click_worker = None
        self.log_in_console("[*] Hệ thống OOP đã được nạp. Sẵn sàng xử lý thực tế.")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def save_url(self):
        self.config["last_url"] = self.url_input.text().strip()
        save_config(self.config)

    def save_speed(self, text):
        self.config["speed"] = text
        save_config(self.config)

    def save_mute(self, state):
        self.config["mute_video"] = bool(state)
        save_config(self.config)

    def save_seconds(self, val):
        self.config["remaining_seconds"] = val
        save_config(self.config)

    def save_auto_skip(self, state):
        self.config["auto_skip_video"] = bool(state)
        save_config(self.config)

    def save_ai_auto_fill(self, state):
        self.config["ai_auto_fill"] = bool(state)
        save_config(self.config)

    def save_ai_skip_img(self, state):
        self.config["ai_skip_img"] = bool(state)
        save_config(self.config)

    def save_ai_target_question(self, val):
        self.config["ai_target_question"] = val
        save_config(self.config)

    def save_quiz_mode(self, index):
        self.config["quiz_mode"] = self.quiz_mode_cb.currentData()
        save_config(self.config)

    def launch_chrome_debug(self):
        port = self.config["debug_port"]
        self.log_in_console(f"[*] Đang mở Chrome Debug (Port: {port})...", "yellow", category="connection")
        self.log_in_console(f"    Sử dụng Profile riêng biệt để không xung đột Chrome cũ.", "gray", category="connection")
        
        user_home = os.path.expanduser("~")
        profile_path = os.path.join(user_home, ".config", "chrome-debug-profile")
        os.makedirs(profile_path, exist_ok=True)
        
        import subprocess
        cmd = f'google-chrome --remote-debugging-port={port} --user-data-dir="{profile_path}" --no-first-run --remote-allow-origins=*'
        try:
            subprocess.Popen(cmd, shell=True)
            self.log_in_console("[✔] Đã mở trình duyệt Chrome mới thành công!", "lightgreen", category="connection")
            self.log_in_console("[💡] Hãy đăng nhập LMS trên cửa sổ Chrome mới này và dán link.", "white", category="connection")
        except Exception as e:
            self.log_in_console(f"[❌] Lỗi khởi chạy Chrome: {str(e)}", "red", category="connection")

    def fetch_active_tab_url(self):
        self.log_in_console("[*] Đang nhận diện tab đang mở hoạt động từ Chrome...", "yellow", category="connection")
        try:
            tab = self.automation.get_active_tab()
            if tab:
                url = tab.get("url", "")
                title = tab.get("title", "")
                self.url_input.setText(url)
                self.url_input.setCursorPosition(0)
                self.log_in_console(f"[✔] Đã nhận diện tab: '{title[:30]}...'", "lightgreen", category="connection")
                self.log_in_console(f"    - URL: {url}", "gray", category="connection")
            else:
                self.log_in_console("[!] Không tìm thấy tab nào đang hoạt động trong Chrome debug.", "yellow", category="connection")
        except Exception as e:
            self.log_in_console(f"[❌] Lỗi nhận diện tab: {str(e)}", "red", category="connection")

    def trigger_ai_scan(self):
        target_url = self.url_input.text().strip()
        if not target_url:
            self.log_in_console("[!] Lỗi: Hãy nhập link LMS ở cột bên trái để nhận diện tab!", "red", category="quiz")
            return
        
        target_num = self.ai_target_q_spin.value()
        self.log_in_console(f"[*] Đang kết nối Chrome để quét riêng câu số {target_num}...", "cyan", category="quiz")
        
        self.ai_scan_worker = AIScanWorker(self.config["debug_port"], target_url, target_num, self.config.get("quiz_mode", "auto"))
        self.ai_scan_worker.finished_signal.connect(self.handle_ai_scan_finished)
        self.ai_scan_worker.start()

    def update_ai_display_views(self):
        self.ai_question_text.setPlainText(self.current_q_text)
        
        analysis_show = f"== ĐÁP ÁN ĐỀ XUẤT: {self.current_solution} ==\n\n"
        analysis_show += "CHI TIẾT ĐÁP ÁN CÁC LỰA CHỌN:\n"
        for opt in self.current_options_list:
            analysis_show += f"- {opt.get('letter')}. {opt.get('text')}\n"
        
        self.ai_analysis_text.setPlainText(analysis_show)

    def handle_ai_scan_finished(self, scan_result, error):
        if error:
            self.log_in_console(f"[❌ QUÉT THẤT BẠI] {error}", "red", category="quiz")
            return

        if not scan_result.get("success"):
            self.log_in_console(f"[❌ QUÉT THẤT BẠI] {scan_result.get('error')}", "red", category="quiz")
            return

        q_text = scan_result.get("questionText", "")
        options = scan_result.get("options", [])
        
        self.total_q_count = scan_result.get("totalQuestions", 1)
        self.ai_target_q_spin.setRange(1, self.total_q_count)
        
        self.current_q_text = q_text
        self.current_options_list = []
        for opt in options:
            letter = chr(65 + opt["index"])
            self.current_options_list.append({
                "index": opt["index"],
                "letter": letter,
                "text": opt["text"]
            })
        
        self.current_solution = ""
        self.update_ai_display_views()
        self.log_in_console(f"[✔] Đã trích xuất xong câu số {self.ai_target_q_spin.value()} từ Chrome!", "lightgreen", category="quiz")

    def trigger_ai_solve(self):
        target_num = self.ai_target_q_spin.value()
        
        if not self.current_q_text.strip():
            self.log_in_console(f"[*] Ô nội dung trống. Tự động quét câu {target_num} trước...", "cyan", category="quiz")
            target_url = self.url_input.text().strip()
            if not target_url:
                self.log_in_console("[!] Lỗi: Hãy nhập link LMS ở cột bên trái để nhận diện tab!", "red", category="quiz")
                return
            
            self.ai_scan_worker = AIScanWorker(self.config["debug_port"], target_url, target_num, self.config.get("quiz_mode", "auto"))
            
            def on_auto_scan_done(scan_res, err):
                if err or not scan_res.get("success"):
                    self.log_in_console(f"[❌] Tự động quét thất bại: {err or scan_res.get('error')}", "red", category="quiz")
                    return
                self.handle_ai_scan_finished(scan_res, None)
                self.run_gemini_solver(target_num)
                
            self.ai_scan_worker.finished_signal.connect(on_auto_scan_done)
            self.ai_scan_worker.start()
        else:
            self.run_gemini_solver(target_num)

    def run_gemini_solver(self, target_num):
        if not self.client.api_keys:
            self.log_in_console("[❌] Lỗi: Chưa cấu hình API Key!", "red", category="quiz")
            self.log_in_console("    Hãy bấm nút Cài đặt API (⚙️ API) hoặc dán key vào file keyAI.md.", "yellow", category="quiz")
            return

        self.log_in_console(f"[[*] Đang gửi dữ liệu Câu {target_num} lên AI...", "yellow", category="quiz")
        
        self.ai_solve_worker = AISolveWorker(
            self.client, target_num, self.current_q_text, self.current_options_list
        )
        self.ai_solve_worker.finished_signal.connect(self.handle_ai_solve_finished)
        self.ai_solve_worker.start()

    def handle_ai_solve_finished(self, ans_letter, reason, error):
        if error:
            self.log_in_console(f"[❌ API LỖI] {error}", "red", category="quiz")
            return

        self.current_solution = ans_letter
        self.update_ai_display_views()
        
        self.log_in_console(f"[🏆 AI] Đã giải xong câu hỏi!", "lightgreen", category="quiz")
        self.log_in_console(f"    - Đáp án đề xuất: {ans_letter}", "lightgreen", category="quiz")
        self.log_in_console(f"    - Lý do: {reason}", "gray", category="quiz")
        
        # Save to cache list
        self.solved_answers_all[str(self.ai_target_q_spin.value())] = ans_letter
        self.ai_view_answers_btn.setEnabled(True)

        # Check autofill
        if self.ai_auto_fill_cb.isChecked() and ans_letter:
            target_url = self.url_input.text().strip()
            target_num = self.ai_target_q_spin.value()
            
            tab = self.automation.find_matching_tab(target_url)
            if tab:
                opt_idx = ord(ans_letter) - 65
                click_res = self.automation.click_option(tab, target_num, opt_idx)
                if click_res.get("success"):
                    self.log_in_console(f"[✔] Đã tự động chọn đáp án [{ans_letter}] cho Câu {target_num} trên Chrome.", "lightgreen", category="quiz")
                else:
                    self.log_in_console(f"[!] Không thể chọn đáp án: {click_res.get('error')}", "yellow", category="quiz")

    def trigger_ai_solve_all(self):
        target_url = self.url_input.text().strip()
        if not target_url:
            self.log_in_console("[!] Lỗi: Hãy nhập link LMS ở cột bên trái để nhận diện tab!", "red", category="quiz")
            return

        if not self.client.api_keys:
            self.log_in_console("[❌] Lỗi: Chưa cấu hình API Key!", "red", category="quiz")
            self.log_in_console("    Hãy bấm nút Cài đặt API (⚙️ API) hoặc dán key vào file keyAI.md.", "yellow", category="quiz")
            return

        self.ai_solve_all_btn.setEnabled(False)
        self.ai_solve_all_btn.setVisible(False)
        self.ai_stop_solve_btn.setEnabled(True)
        self.ai_stop_solve_btn.setVisible(True)

        self.solve_all_worker = AISolveAllWorker(
            self.config["debug_port"], target_url, self.client.get_all_keys(),
            self.ai_auto_fill_cb.isChecked(), self.ai_skip_img_cb.isChecked(),
            self.config.get("quiz_mode", "auto")
        )
        self.solve_all_worker.log_signal.connect(self.handle_log_quiz)
        self.solve_all_worker.update_signal.connect(self.handle_solve_all_update)
        self.solve_all_worker.finished_signal.connect(self.handle_solve_all_finished)
        self.solve_all_worker.start()

    def stop_ai_solve_all(self):
        if self.solve_all_worker and self.solve_all_worker.isRunning():
            self.log_in_console("[*] Đang dừng tiến trình giải đề theo yêu cầu...", "yellow", category="quiz")
            self.solve_all_worker.running = False
            self.solve_all_worker.wait()

    def handle_solve_all_update(self, q_num, ans_letter):
        self.solved_answers_all[str(q_num)] = ans_letter
        self.ai_view_answers_btn.setEnabled(True)
        self.ai_target_q_spin.setValue(q_num)

    def handle_solve_all_finished(self, success, message):
        self.ai_solve_all_btn.setEnabled(True)
        self.ai_solve_all_btn.setVisible(True)
        self.ai_stop_solve_btn.setEnabled(False)
        self.ai_stop_solve_btn.setVisible(False)
        
        if success:
            self.log_in_console(f"[🏆 AI] {message.splitlines()[0]}", "lightgreen", category="quiz")
        else:
            self.log_in_console(f"[❌ AI THẤT BẠI] {message}", "red", category="quiz")

    def show_solved_answers_list(self):
        if USING_PYSIDE:
            from PySide6.QtWidgets import QMessageBox
        else:
            from PyQt5.QtWidgets import QMessageBox
            
        if not self.solved_answers_all:
            QMessageBox.information(self, "Danh sách đáp án", "Chưa giải được câu nào.")
            return

        sorted_keys = sorted(self.solved_answers_all.keys(), key=lambda x: int(x))
        txt = "DANH SÁCH ĐÁP ÁN ĐÃ GIẢI ĐƯỢC:\n\n"
        for k in sorted_keys:
            txt += f"Câu {k}: {self.solved_answers_all[k]}\n"

        # Also offer copying JSON format
        json_str = json.dumps(self.solved_answers_all, indent=2)
        txt += f"\n\nDẠNG BẢN TIN JSON ĐỂ COPY:\n{json_str}"

        box = QMessageBox(self)
        box.setWindowTitle("Đáp án đã thu thập")
        box.setText(txt)
        
        copy_btn = box.addButton("Sao chép JSON vào Clipboard", QMessageBox.ActionRole)
        box.addButton("Đóng", QMessageBox.RejectRole)
        box.exec_()

        if box.clickedButton() == copy_btn:
            clipboard = QApplication.clipboard()
            clipboard.setText(json_str)
            self.log_in_console("[✔] Đã copy chuỗi JSON đáp án vào clipboard!", "lightgreen", category="quiz")

    def start_speed_only(self):
        self.run_worker(skip_mode=False)

    def start_skip_only(self):
        self.run_worker(skip_mode=True)

    def run_worker(self, skip_mode=False):
        target_url = self.url_input.text().strip()
        if not target_url:
            self.log_in_console("[!] Lỗi: Hãy dán URL của bài học để nhận diện tab trình duyệt!", "red", category="video")
            return

        speed = float(self.speed_combo.currentText())
        mute = self.mute_cb.isChecked()
        rem_secs = self.seconds_spin.value()
        
        action_mode = "skip" if skip_mode else "speed"
        self.worker = SpeedControllerWorker(
            target_url, speed, self.config["debug_port"], mute, action_mode, rem_secs
        )
        self.worker.log_signal.connect(self.handle_log_video)
        self.worker.progress_signal.connect(self.handle_progress)
        self.worker.finished_signal.connect(self.handle_finished)
        self.worker.start()

    def handle_log_video(self, text, color):
        self.log_in_console(text, color, category="video")

    def handle_log_quiz(self, text, color):
        self.log_in_console(text, color, category="quiz")

    def handle_progress(self, current, duration):
        percent = int((current / duration) * 100) if duration > 0 else 0
        self.progress_bar.setValue(percent)
        self.time_lbl.setText(f"{format_time(current)} / {format_time(duration)}")

    def handle_finished(self, success, message):
        if success:
            self.log_in_console(f"[🏆 SUCCESS] {message}", "lightgreen", category="video")
        else:
            self.log_in_console(f"[❌ FAILED] {message}", "red", category="video")
        self.progress_bar.setValue(100)

    def toggle_auto_learn(self):
        if self.auto_worker and self.auto_worker.isRunning():
            self.auto_worker.running = False
            self.auto_worker.wait()
            self.auto_status_lbl.setText("TẮT")
            self.auto_status_lbl.setStyleSheet("color: #71717a; font-weight: bold;")
            self.auto_btn.setText("▶ KÍCH HOẠT TỰ ĐỘNG HỌC")
            self.auto_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
                }
            """)
            self.log_in_console("[*] Đã tắt chế độ Tự động học toàn bộ.", "yellow", category="video")
        else:
            target_url = self.url_input.text().strip()
            if not target_url:
                self.log_in_console("[!] Lỗi: Hãy dán URL của bài học để nhận diện tab trình duyệt!", "red", category="video")
                return
            
            self.auto_status_lbl.setText("ĐANG CHẠY")
            self.auto_status_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
            self.auto_btn.setText("⏸ DỪNG TỰ ĐỘNG HỌC")
            self.auto_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #b91c1c);
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f87171, stop:1 #ef4444);
                }
            """)
            self.log_in_console("[*] Bắt đầu kích hoạt chế độ Tự động học toàn bộ...", "lightgreen", category="video")
            
            speed = float(self.speed_combo.currentText())
            mute = self.mute_cb.isChecked()
            rem_secs = self.seconds_spin.value()
            auto_skip = self.auto_skip_cb.isChecked()
            
            self.auto_worker = AutoLearnWorker(
                target_url, speed, self.config["debug_port"], mute, rem_secs, auto_skip
            )
            self.auto_worker.log_signal.connect(self.handle_auto_log)
            self.auto_worker.status_signal.connect(self.handle_auto_status)
            self.auto_worker.finished_signal.connect(self.handle_auto_finished)
            self.auto_worker.start()

    def handle_auto_log(self, text, color):
        self.log_in_console(text, color, category="video")

    def handle_auto_status(self, text):
        self.log_in_console(f"[🏆 AUTO] {text}", "lightgreen", category="video")

    def handle_auto_finished(self, success, message):
        self.auto_status_lbl.setText("TẮT")
        self.auto_status_lbl.setStyleSheet("color: #71717a; font-weight: bold;")
        self.auto_btn.setText("▶ KÍCH HOẠT TỰ ĐỘNG HỌC")
        self.auto_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        if success:
            self.log_in_console(f"[🏆 AUTO] {message}", "lightgreen", category="video")
        else:
            self.log_in_console(f"[⚠️ AUTO] {message}", "yellow", category="video")

    def log_in_console(self, text, color="white", category=None):
        if not category:
            text_lower = text.lower()
            if any(k in text_lower for k in ["chrome", "trình duyệt", "profile", "tab", "kết nối", "oop"]):
                category = "connection"
            elif any(k in text_lower for k in ["video", "tốc độ", "tắt tiếng", "tua", "tự động học", "next", "bài tiếp theo", "tài liệu", "đang phát", "duration"]):
                category = "video"
            elif any(k in text_lower for k in ["quét", "ai", "giải", "câu hỏi", "đáp án", "đề", "prompt", "json", "click", "auto-click", "gemini", "api key", "groq"]):
                category = "quiz"
            else:
                category = "connection"

        color_map = {
            "white": "#1e293b",
            "green": "#047857",
            "lightgreen": "#15803d",
            "red": "#b91c1c",
            "yellow": "#b45309",
            "cyan": "#0369a1",
            "gray": "#475569"
        }
        hex_color = color_map.get(color, "#1e293b")
        html_msg = f"<span style='color: {hex_color}; font-family: Consolas, monospace; font-size: 9.5px;'>{text.replace('\n', '<br>')}</span>"

        if category == "connection":
            self.connection_console.appendHtml(html_msg)
        elif category == "video":
            self.video_console.appendHtml(html_msg)
        elif category == "quiz":
            self.quiz_console.appendHtml(html_msg)

    def open_api_settings(self):
        current_keys = self.client.api_keys
        dialog = APISettingsDialog(self, current_keys)
        if dialog.exec_() == QDialog.Accepted:
            new_keys = dialog.get_keys()
            self.client.api_keys = new_keys
            self.config["api_keys"] = new_keys
            save_config(self.config)
            self.log_in_console(f"[✔] Đã lưu {len(new_keys)} API Keys vào cấu hình. Hệ thống sẽ tự động xoay vòng khi giải.", "lightgreen", category="quiz")

    def trigger_web_copy_prompt(self):
        target_url = self.url_input.text().strip()
        if not target_url:
            self.log_in_console("[❌] Vui lòng nhập link bài học LMS trước!", "red", category="quiz")
            return

        if self.prompt_gen_worker and self.prompt_gen_worker.isRunning():
            self.log_in_console("[!] Tiến trình quét câu hỏi đang chạy.", "yellow", category="quiz")
            return

        self.web_scan_btn.setEnabled(False)
        self.web_scan_btn.setText("⏳ ĐANG QUÉT...")
        self.web_copy_prompt_btn.setEnabled(False)

        limit = self.web_scan_limit_spin.value()
        self.prompt_gen_worker = PromptGenWorker(self.config["debug_port"], target_url, max_questions=limit, quiz_mode=self.config.get("quiz_mode", "auto"))
        self.prompt_gen_worker.log_signal.connect(self.handle_prompt_gen_log)
        self.prompt_gen_worker.finished_signal.connect(self.handle_prompt_gen_finished)
        self.prompt_gen_worker.start()

    def handle_prompt_gen_log(self, text, color="gray"):
        self.log_in_console(text, color, category="quiz")

    def handle_prompt_gen_finished(self, prompt_text, error):
        self.web_scan_btn.setEnabled(True)
        self.web_scan_btn.setText("🔍 BẮT ĐẦU QUÉT")

        if error:
            self.log_in_console(f"[❌] Lỗi quét câu hỏi tạo prompt: {error}", "red", category="quiz")
            return

        if not prompt_text:
            self.log_in_console("[❌] Không trích xuất được nội dung câu hỏi nào.", "red", category="quiz")
            return

        self.scanned_prompt_text = prompt_text
        self.web_copy_prompt_btn.setEnabled(True)
        self.web_copy_prompt_btn.setText("📋 SAO CHÉP PROMPT AI (SẴN SÀNG)")
        
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(prompt_text)
            self.log_in_console("[✔] ĐÃ QUÉT XONG CÂU HỎI VÀ TỰ ĐỘNG COPY VÀO BỘ NHỚ TẠM (CLIPBOARD)!", "green", category="quiz")
            self.log_in_console("[💡] Hãy mở ChatGPT/Gemini Web, nhấn Ctrl+V để dán và gửi cho AI. Sau đó sao chép kết quả JSON dán vào ô dưới.", "cyan", category="quiz")
        except Exception as e:
            self.log_in_console(f"[❌] Lỗi tự động copy prompt: {str(e)}", "red", category="quiz")

    def copy_scanned_prompt_clipboard(self):
        if not hasattr(self, 'scanned_prompt_text') or not self.scanned_prompt_text:
            self.log_in_console("[❌] Không có nội dung prompt nào để sao chép.", "red", category="quiz")
            return
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.scanned_prompt_text)
            self.log_in_console("[✔] Đã sao chép prompt câu hỏi vào clipboard thành công!", "green", category="quiz")
        except Exception as e:
            self.log_in_console(f"[❌] Lỗi sao chép: {str(e)}", "red", category="quiz")

    def trigger_web_auto_click(self):
        target_url = self.url_input.text().strip()
        if not target_url:
            self.log_in_console("[❌] Vui lòng nhập link bài học LMS trước!", "red", category="quiz")
            return

        json_text = self.web_json_input.toPlainText().strip()
        if not json_text:
            self.log_in_console("[❌] Vui lòng dán đoạn JSON đáp án từ AI Web vào ô nhập liệu!", "red", category="quiz")
            return

        # Robust parsing helper functions defined locally
        def clean_json_text(text):
            text = text.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
            return text

        def extract_answers_from_json(obj, results=None):
            if results is None:
                results = {}
            if isinstance(obj, dict):
                q_num = None
                ans = None
                for k, v in obj.items():
                    k_lower = k.lower()
                    if k_lower in ["question", "question_num", "question_number", "id", "q", "num"]:
                        if isinstance(v, int):
                            q_num = v
                        elif isinstance(v, str):
                            dig_match = re.search(r'\d+', v)
                            if dig_match:
                                q_num = int(dig_match.group(0))
                for k, v in obj.items():
                    k_lower = k.lower()
                    if k_lower in ["correct_key", "correct_answer", "answer", "ans", "key", "value"]:
                        if isinstance(v, str) and len(v.strip()) == 1:
                            ans = v.strip().upper()
                        elif isinstance(v, str) and len(v.strip()) > 1:
                            letter_match = re.match(r'^[A-Z]\b', v.strip().upper())
                            if letter_match:
                                ans = letter_match.group(0)
                if q_num is not None and ans is not None:
                    results[str(q_num)] = ans
                    return results
                for k, v in obj.items():
                    k_digits = re.search(r'\d+', k)
                    if k_digits:
                        q_num = int(k_digits.group(0))
                        if isinstance(v, str):
                            v_clean = v.strip().upper()
                            if len(v_clean) == 1 and 'A' <= v_clean <= 'Z':
                                results[str(q_num)] = v_clean
                                continue
                            letter_match = re.match(r'^([A-Z])\b', v_clean)
                            if letter_match:
                                results[str(q_num)] = letter_match.group(1)
                                continue
                    if isinstance(v, (dict, list)):
                        extract_answers_from_json(v, results)
            elif isinstance(obj, list):
                for item in obj:
                    extract_answers_from_json(item, results)
            return results

        def extract_answers_from_text(text):
            results = {}
            lines = text.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                match = re.search(r'(?:câu|question|q)?\s*[\"\'\-\s]*(\d+)[\"\'\-\s]*\s*[:\-\s\.\)=]+\s*[\"\'\-\s]*([A-Z])[\"\'\-\s]*$', line, re.IGNORECASE)
                if match:
                    q_num = match.group(1)
                    ans = match.group(2).upper()
                    results[str(q_num)] = ans
                    continue
                nums = re.findall(r'\b\d+\b', line)
                letters = re.findall(r'\b[A-Z]\b', line)
                if len(nums) == 1 and len(letters) == 1:
                    results[str(nums[0])] = letters[0].upper()
            return results

        def parse_answers_robust(text_val):
            res_dict = {}
            cleaned_text = clean_json_text(text_val)
            try:
                obj = json.loads(cleaned_text)
                if obj:
                    extract_answers_from_json(obj, res_dict)
            except Exception:
                try:
                    fixed_text = re.sub(r',\s*([\]}])', r'\1', cleaned_text)
                    obj = json.loads(fixed_text)
                    if obj:
                        extract_answers_from_json(obj, res_dict)
                except Exception:
                    pass
            if not res_dict:
                res_dict = extract_answers_from_text(text_val)
            return res_dict

        answers_map = parse_answers_robust(json_text)
        if not answers_map:
            self.log_in_console("[❌] Không tìm thấy hoặc không nhận dạng được bất kỳ câu trả lời nào từ dữ liệu dán vào!", "red", category="quiz")
            return

        self.log_in_console(f"[✔] Đã nhận diện thành công {len(answers_map)} đáp án câu hỏi từ dữ liệu nhập.", "lightgreen", category="quiz")

        if self.web_click_worker and self.web_click_worker.isRunning():
            self.log_in_console("[!] Tiến trình auto click đang chạy.", "yellow", category="quiz")
            return

        self.web_start_click_btn.setEnabled(False)
        self.web_start_click_btn.setVisible(False)
        self.web_stop_click_btn.setEnabled(True)
        self.web_stop_click_btn.setVisible(True)

        self.web_click_worker = WebClickWorker(self.config["debug_port"], target_url, answers_map, self.config.get("quiz_mode", "auto"))
        self.web_click_worker.log_signal.connect(self.handle_web_click_log)
        self.web_click_worker.finished_signal.connect(self.handle_web_click_finished)
        self.web_click_worker.start()

    def stop_web_auto_click(self):
        if self.web_click_worker and self.web_click_worker.isRunning():
            self.log_in_console("[*] Đang dừng tiến trình auto-click theo yêu cầu...", "yellow", category="quiz")
            self.web_click_worker.running = False
            self.web_click_worker.wait()

    def handle_web_click_log(self, text, color="gray"):
        self.log_in_console(text, color, category="quiz")

    def handle_web_click_finished(self, success, message, color):
        self.web_start_click_btn.setEnabled(True)
        self.web_start_click_btn.setVisible(True)
        self.web_stop_click_btn.setEnabled(False)
        self.web_stop_click_btn.setVisible(False)
        self.log_in_console(f"[🏆] {message}", color, category="quiz")

    def handle_tab_changed(self, index):
        if index == 1:  # API Mode
            if USING_PYSIDE:
                from PySide6.QtWidgets import QMessageBox
            else:
                from PyQt5.QtWidgets import QMessageBox
            
            api_keys = self.client.get_all_keys()
            if not api_keys:
                msg = (
                    "⚠️ KHUYẾN NGHỊ QUAN TRỌNG CHO BẠN:\n\n"
                    "Chế độ Giải bằng API yêu cầu bạn phải nhập API Key của riêng mình (Gemini/Groq) trước khi làm.\n\n"
                    "Hệ thống khuyến nghị bạn nên dùng chế độ 'GIẢI WEB AI (MIỄN PHÍ)' ở tab bên cạnh:\n"
                    "- Hoàn toàn miễn phí, không cần Key API phức tạp.\n"
                    "- Không bị giới hạn quota hay lỗi quá lượt gọi của nhà cung cấp.\n"
                    "- Giao diện thân thiện và tối ưu hơn cho người dùng không rành kỹ thuật.\n\n"
                    "Nếu vẫn muốn sử dụng API, vui lòng bấm nút Cài đặt API (⚙️ API) ở góc trên để cấu hình Key trước!"
                )
                QMessageBox.warning(self, "Cấu hình API Key & Khuyến nghị", msg)
            else:
                msg = (
                    "⚠️ KHUYẾN NGHỊ SỬ DỤNG:\n\n"
                    "Bạn đã cấu hình API Key. Tuy nhiên, chế độ API này có thể gây tốn phí hoặc bị giới hạn lượt gọi từ nhà cung cấp.\n\n"
                    "Hệ thống khuyến nghị bạn nên ưu tiên dùng chế độ 'GIẢI WEB AI (MIỄN PHÍ)' ở tab bên cạnh vì hoàn toàn miễn phí, an toàn và ổn định hơn!"
                )
                QMessageBox.information(self, "Khuyến nghị sử dụng chế độ miễn phí", msg)

    def update_columns_visibility(self):
        show_col1 = self.toggle_col1_btn.isChecked()
        show_col2 = self.toggle_col2_btn.isChecked()
        show_col3 = self.toggle_col3_btn.isChecked()
        
        # Enforce at least one column is visible
        if not (show_col1 or show_col2 or show_col3):
            sender = self.sender()
            if sender:
                sender.setChecked(True)
            else:
                self.toggle_col3_btn.setChecked(True)
            return

        show_col1 = self.toggle_col1_btn.isChecked()
        show_col2 = self.toggle_col2_btn.isChecked()
        show_col3 = self.toggle_col3_btn.isChecked()

        self.col1_panel.setVisible(show_col1)
        self.col2_panel.setVisible(show_col2)
        self.col3_panel.setVisible(show_col3)

        self.v_sep1.setVisible(show_col1 and (show_col2 or show_col3))
        self.v_sep2.setVisible(show_col2 and show_col3)

        # Calculate exact window width based on visible columns
        visible_cols_width = 0
        visible_count = 0
        if show_col1:
            visible_cols_width += 380
            visible_count += 1
        if show_col2:
            visible_cols_width += 380
            visible_count += 1
        if show_col3:
            visible_cols_width += 410
            visible_count += 1

        extra_width = 40  # main_layout margins + workspace_layout margins
        if visible_count == 2:
            extra_width += 25
        elif visible_count == 3:
            extra_width += 50

        target_width = visible_cols_width + extra_width
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.setFixedSize(target_width, 820)

    def toggle_compact_mode(self):
        if self.container.isVisible():
            self.container.hide()
            self.compact_container.show()
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedSize(350, 65)
            self.compact_timer.start(400)
        else:
            self.compact_container.hide()
            self.container.show()
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedSize(1260, 820)
            self.update_columns_visibility()
            self.compact_timer.stop()

    def animate_compact_mode(self):
        self.compact_dots = (self.compact_dots + 1) % 4
        dots_str = "." * self.compact_dots
        
        status_text = "Hệ thống sẵn sàng"
        if hasattr(self, "auto_worker") and self.auto_worker and self.auto_worker.isRunning():
            status_text = "Đang tự động học video"
        elif hasattr(self, "solve_all_worker") and self.solve_all_worker and self.solve_all_worker.isRunning():
            status_text = "Đang giải trắc nghiệm API"
        elif hasattr(self, "web_click_worker") and self.web_click_worker and self.web_click_worker.isRunning():
            status_text = "Đang tự động chọn đáp án"
        elif hasattr(self, "prompt_gen_worker") and self.prompt_gen_worker and self.prompt_gen_worker.isRunning():
            status_text = "Đang quét câu hỏi"
            
        self.compact_status_lbl.setText(f"⚡ {status_text}{dots_str}")
        
        pulse_emojis = ["🟢", "✨", "🔵", "⚡"]
        self.compact_dot_lbl.setText(pulse_emojis[self.compact_dots])

    def closeEvent(self, event):
        if hasattr(self, "auto_worker") and self.auto_worker and self.auto_worker.isRunning():
            self.auto_worker.running = False
            self.auto_worker.wait()
        if hasattr(self, "solve_all_worker") and self.solve_all_worker and self.solve_all_worker.isRunning():
            self.solve_all_worker.running = False
            self.solve_all_worker.wait()
        if self.prompt_gen_worker and self.prompt_gen_worker.isRunning():
            self.prompt_gen_worker.running = False
            self.prompt_gen_worker.wait()
        if self.web_click_worker and self.web_click_worker.isRunning():
            self.web_click_worker.running = False
            self.web_click_worker.wait()
        event.accept()



class APISettingsDialog(QDialog):
    def __init__(self, parent=None, current_keys=None):
        super().__init__(parent)
        self.setWindowTitle("Cấu hình API Keys - LMS Scraper")
        self.setMinimumSize(500, 400)
        self.key_rows = []
        self.init_ui(current_keys)

    def init_ui(self, current_keys):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("🔑 CẤU HÌNH API KEYS (DYNAMIC ROTATOR)", self)
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: #0369a1;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        layout.addWidget(title_label)
        
        # Instruction text
        help_label = QLabel(
            "Hệ thống tự động nhận dạng loại Key (Gemini: AIzaSy..., Groq: gsk_...) và xoay vòng (fallback) khi lỗi quota.",
            self
        )
        help_label.setStyleSheet("color: #475569; font-size: 11px; line-height: 1.4;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        # Scroll Area for keys
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background-color: #f8fafc;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #f8fafc;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        # Populate current keys
        if current_keys:
            for key in current_keys:
                if key.strip():
                    self.add_key_field(key.strip())
        
        # If no keys, add one empty field by default
        if not self.key_rows:
            self.add_key_field("")

        # Add Key Button
        self.add_key_btn = QPushButton("➕ THÊM TRƯỜNG API KEY MỚI", self)
        self.add_key_btn.setStyleSheet("""
            QPushButton {
                background: #f0f9ff;
                color: #0284c7;
                border: 1px dashed #0284c7;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #e0f2fe;
            }
        """)
        self.add_key_btn.clicked.connect(lambda: self.add_key_field(""))
        layout.addWidget(self.add_key_btn)
        
        # Button container
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.save_btn = QPushButton("Lưu cấu hình", self)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Hủy bỏ", self)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #dc2626);
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f87171, stop:1 #ef4444);
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("background-color: #ffffff; color: #0f172a;")

    def add_key_field(self, key_text=""):
        row_widget = QWidget(self.scroll_content)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        
        # Label/Icon
        lbl = QLabel("🔑", row_widget)
        lbl.setStyleSheet("font-size: 14px;")
        row_layout.addWidget(lbl)
        
        # Key Line Edit
        key_edit = QLineEdit(row_widget)
        key_edit.setPlaceholderText("Nhập API Key...")
        key_edit.setText(key_text)
        key_edit.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #0ea5e9;
            }
        """)
        row_layout.addWidget(key_edit)
        
        # Delete Button
        del_btn = QPushButton("❌", row_widget)
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #ef4444;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #fee2e2;
                border-color: #fca5a5;
            }
        """)
        
        # Connect delete action
        def on_delete():
            if len(self.key_rows) <= 1:
                # Keep at least one empty field
                key_edit.clear()
                return
            self.key_rows.remove(row_data)
            row_widget.deleteLater()
            
        del_btn.clicked.connect(on_delete)
        row_layout.addWidget(del_btn)
        
        # Keep track of row widget & line edit
        row_data = {"widget": row_widget, "edit": key_edit}
        self.key_rows.append(row_data)
        
        self.scroll_layout.addWidget(row_widget)

    def get_keys(self):
        keys = []
        for row in self.key_rows:
            text = row["edit"].text().strip()
            # Clean copy-paste characters
            text = text.replace("`", "")
            if text and not text.startswith("#") and not text.startswith("["):
                keys.append(text)
        return keys


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.WindowText, QColor(15, 23, 42))
    app.setPalette(palette)
    
    gui = FloatingSpeedApp()
    gui.show()
    sys.exit(app.exec())
