#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import re
import urllib.parse
from urllib.parse import urlparse
import requests

# Try PyQt5 first since it has higher compatibility on Linux, fallback to PySide6
try:
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
        QLineEdit, QPushButton, QPlainTextEdit, QFrame, QCheckBox,
        QGraphicsDropShadowEffect
    )
    from PyQt5.QtCore import Qt, QThread, QPoint, QSize
    from PyQt5.QtCore import pyqtSignal as Signal
    from PyQt5.QtGui import QColor, QPalette, QBrush
    USING_PYSIDE = False
except ImportError:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
        QLineEdit, QPushButton, QPlainTextEdit, QFrame, QCheckBox,
        QGraphicsDropShadowEffect
    )
    from PySide6.QtCore import Qt, QThread, Signal, QPoint, QSize
    from PySide6.QtGui import QColor, QPalette, QBrush
    USING_PYSIDE = True

CONFIG_FILE = "config_ui.json"

DEFAULT_CONFIG = {
    "base_url": "http://localhost:3001",
    "endpoint": "/api/lessons/complete",
    "jwt_token": "PASTE_YOUR_JWT_TOKEN_HERE",
    "last_url": "",
    "progress_percent": 100,
    "watched_seconds": 9999
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


class BypassWorker(QThread):
    log_signal = Signal(str, str)  # (text, color)
    finished_signal = Signal(bool, str)  # (success, message)

    def __init__(self, base_url, endpoint, jwt_token, payload):
        super().__init__()
        self.base_url = base_url
        self.endpoint = endpoint
        self.jwt_token = jwt_token
        self.payload = payload

    def run(self):
        url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
        }
        if self.jwt_token and self.jwt_token != "PASTE_YOUR_JWT_TOKEN_HERE":
            if not self.jwt_token.lower().startswith("bearer "):
                headers["Authorization"] = f"Bearer {self.jwt_token}"
            else:
                headers["Authorization"] = self.jwt_token

        self.log_signal.emit(f"[*] Đang kết nối tới: {url}", "cyan")
        self.log_signal.emit(f"[*] Payload gửi đi: {json.dumps(self.payload, ensure_ascii=False)}", "gray")

        try:
            resp = requests.post(url, headers=headers, json=self.payload, timeout=10)
            self.log_signal.emit(f"[+] Status code: {resp.status_code}", "yellow")
            
            try:
                resp_data = resp.json()
                resp_str = json.dumps(resp_data, indent=2, ensure_ascii=False)
            except ValueError:
                resp_str = resp.text
                
            self.log_signal.emit(f"[+] Phản hồi từ server:\n{resp_str}", "lightgreen")

            if resp.status_code in (200, 201):
                self.finished_signal.emit(True, "Bypass thành công! Server đã chấp nhận.")
            else:
                self.finished_signal.emit(False, f"Server từ chối (HTTP {resp.status_code})")
        except Exception as e:
            self.log_signal.emit(f"[!] Lỗi kết nối: {str(e)}", "red")
            self.finished_signal.emit(False, f"Lỗi: {str(e)}")


class FloatingBypassApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.drag_position = QPoint()
        
        self.init_ui()
        self.parse_url_input()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(380, 520)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QWidget(self)
        self.container.setObjectName("Container")
        
        self.container.setStyleSheet("""
            QWidget#Container {
                background-color: rgba(22, 28, 41, 0.93);
                border: 1px solid rgba(0, 191, 255, 0.3);
                border-radius: 16px;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#TitleLabel {
                color: #00e5ff;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLineEdit {
                background-color: rgba(10, 15, 26, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: #ffffff;
                padding: 8px 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #00bfff;
                background-color: rgba(10, 15, 26, 0.95);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00b4db, stop:1 #0083b0);
                border: none;
                border-radius: 8px;
                color: white;
                font-family: 'Outfit', 'Inter', sans-serif;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c6ff, stop:1 #0072ff);
            }
            QPushButton:pressed {
                background: #0056b3;
            }
            QPushButton#CloseBtn {
                background: transparent;
                color: #ff5f56;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
                border-radius: 4px;
            }
            QPushButton#CloseBtn:hover {
                background-color: rgba(255, 95, 86, 0.2);
            }
            QPushButton#MinBtn {
                background: transparent;
                color: #ffbd2e;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
                border-radius: 4px;
            }
            QPushButton#MinBtn:hover {
                background-color: rgba(255, 189, 46, 0.2);
            }
            QPlainTextEdit {
                background-color: #070b12;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #39ff14;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 5px;
            }
            QFrame#Separator {
                background-color: rgba(255, 255, 255, 0.08);
                max-height: 1px;
            }
            QFrame#BadgeFrame {
                background-color: rgba(0, 229, 255, 0.1);
                border: 1px solid rgba(0, 229, 255, 0.2);
                border-radius: 6px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 191, 255, 60))
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 12, 15, 15)
        container_layout.setSpacing(10)

        # --- 1. Custom Title Bar ---
        title_bar_layout = QHBoxLayout()
        
        title_label = QLabel("⚡ LMS BYPASS", self.container)
        title_label.setObjectName("TitleLabel")
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()

        min_btn = QPushButton("─", self.container)
        min_btn.setObjectName("MinBtn")
        min_btn.setFixedSize(20, 20)
        min_btn.setToolTip("Thu nhỏ")
        min_btn.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(min_btn)

        close_btn = QPushButton("✕", self.container)
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(20, 20)
        close_btn.setToolTip("Đóng")
        close_btn.clicked.connect(self.close)
        title_bar_layout.addWidget(close_btn)

        container_layout.addLayout(title_bar_layout)

        sep = QFrame(self.container)
        sep.setObjectName("Separator")
        container_layout.addWidget(sep)

        # --- 2. URL Input Section ---
        url_label = QLabel("DÁN LINK TRANG WEB BÀI HỌC:", self.container)
        container_layout.addWidget(url_label)

        self.url_input = QLineEdit(self.container)
        self.url_input.setPlaceholderText("https://lms.hutech.edu.vn/courses/.../items/...")
        self.url_input.setText(self.config["last_url"])
        self.url_input.textChanged.connect(self.parse_url_input)
        container_layout.addWidget(self.url_input)

        # --- 3. Recognized Web Context Info ---
        self.info_badge = QFrame(self.container)
        self.info_badge.setObjectName("BadgeFrame")
        info_badge_layout = QVBoxLayout(self.info_badge)
        info_badge_layout.setContentsMargins(10, 8, 10, 8)
        info_badge_layout.setSpacing(4)

        self.badge_title = QLabel("🔍 PHÂN TÍCH VỊ TRÍ WEB:", self.info_badge)
        self.badge_title.setStyleSheet("color: #00e5ff; font-size: 10px;")
        info_badge_layout.addWidget(self.badge_title)

        self.domain_label = QLabel("Tên miền: Chưa nhận diện", self.info_badge)
        self.domain_label.setStyleSheet("color: #cbd5e1; font-weight: normal;")
        info_badge_layout.addWidget(self.domain_label)

        self.lesson_label = QLabel("Lesson ID: Trống", self.info_badge)
        self.lesson_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        info_badge_layout.addWidget(self.lesson_label)

        container_layout.addWidget(self.info_badge)

        # --- 4. JWT Token Input ---
        token_label = QLabel("MÃ JWT TOKEN / AUTHORIZATION HEADER:", self.container)
        container_layout.addWidget(token_label)

        self.token_input = QLineEdit(self.container)
        self.token_input.setPlaceholderText("Bearer eyJhbGciOiJIUzI1NiIsIn...")
        self.token_input.setText(self.config["jwt_token"])
        self.token_input.textChanged.connect(self.save_token_on_edit)
        container_layout.addWidget(self.token_input)

        # --- 5. Advanced Config toggle ---
        self.advanced_check = QCheckBox("Hiển thị Tùy chỉnh nâng cao", self.container)
        self.advanced_check.setStyleSheet("""
            QCheckBox {
                color: #94a3b8;
                font-size: 10px;
                font-weight: normal;
            }
            QCheckBox::indicator {
                width: 12px;
                height: 12px;
            }
        """)
        self.advanced_check.stateChanged.connect(self.toggle_advanced)
        container_layout.addWidget(self.advanced_check)

        # Advanced config widget (collapsed by default)
        self.advanced_widget = QWidget(self.container)
        adv_layout = QVBoxLayout(self.advanced_widget)
        adv_layout.setContentsMargins(0, 0, 0, 0)
        adv_layout.setSpacing(6)

        # Custom Base URL
        lbl_base = QLabel("BASE URL SERVER API:", self.advanced_widget)
        lbl_base.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.base_url_input = QLineEdit(self.advanced_widget)
        self.base_url_input.setText(self.config["base_url"])
        self.base_url_input.textChanged.connect(self.update_config_fields)
        adv_layout.addWidget(lbl_base)
        adv_layout.addWidget(self.base_url_input)

        # Custom Endpoint
        lbl_endpoint = QLabel("ENDPOINT HOÀN THÀNH:", self.advanced_widget)
        lbl_endpoint.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.endpoint_input = QLineEdit(self.advanced_widget)
        self.endpoint_input.setText(self.config["endpoint"])
        self.endpoint_input.textChanged.connect(self.update_config_fields)
        adv_layout.addWidget(lbl_endpoint)
        adv_layout.addWidget(self.endpoint_input)

        self.advanced_widget.setVisible(False)
        container_layout.addWidget(self.advanced_widget)

        # --- 6. Large Action Button ---
        self.action_btn = QPushButton("⚡ KÍCH HOẠT HOÀN THÀNH (BYPASS)", self.container)
        self.action_btn.clicked.connect(self.start_bypass)
        container_layout.addWidget(self.action_btn)

        # --- 7. Console logs panel ---
        console_label = QLabel("LOGS HOẠT ĐỘNG:", self.container)
        container_layout.addWidget(console_label)

        self.console = QPlainTextEdit(self.container)
        self.console.setReadOnly(True)
        self.console.appendPlainText("[*] Khởi động ứng dụng. Sẵn sàng nhận link.")
        container_layout.addWidget(self.console)

        main_layout.addWidget(self.container)
        self.setLayout(main_layout)

    # --- Mouse Events for Draggable Window ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if USING_PYSIDE:
                global_pos = event.globalPosition().toPoint()
            else:
                global_pos = event.globalPos()
            self.drag_position = global_pos - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if USING_PYSIDE:
                global_pos = event.globalPosition().toPoint()
            else:
                global_pos = event.globalPos()
            self.move(global_pos - self.drag_position)
            event.accept()

    # --- URL Parsing Logic ---
    def parse_url_input(self):
        url_text = self.url_input.text().strip()
        self.config["last_url"] = url_text
        save_config(self.config)

        if not url_text:
            self.domain_label.setText("Tên miền: Chưa nhận diện")
            self.lesson_label.setText("Lesson ID: Trống")
            self.badge_title.setText("🔍 PHÂN TÍCH VỊ TRÍ WEB:")
            self.info_badge.setStyleSheet("background-color: rgba(0, 229, 255, 0.1); border: 1px solid rgba(0, 229, 255, 0.2);")
            return

        try:
            parsed = urlparse(url_text)
            domain = parsed.netloc or parsed.path.split('/')[0]
            self.domain_label.setText(f"Tên miền: {domain}")
            
            path = parsed.path
            lesson_id = ""

            match_item = re.search(r'/items/([a-zA-Z0-9_\-]+)', path)
            match_lesson = re.search(r'/lessons/([a-zA-Z0-9_\-]+)', path)

            if match_item:
                lesson_id = match_item.group(1)
                self.badge_title.setText("🔍 PHÁT HIỆN: CANVAS / HUTECH LMS ITEM")
                self.info_badge.setStyleSheet("background-color: rgba(57, 255, 20, 0.1); border: 1px solid rgba(57, 255, 20, 0.2);")
            elif match_lesson:
                lesson_id = match_lesson.group(1)
                self.badge_title.setText("🔍 PHÁT HIỆN: BÀI HỌC (LESSON)")
                self.info_badge.setStyleSheet("background-color: rgba(0, 229, 255, 0.1); border: 1px solid rgba(0, 229, 255, 0.2);")
            else:
                segments = [s for s in path.split('/') if s]
                if segments:
                    lesson_id = segments[-1]
                else:
                    lesson_id = "Không rõ"
                
                self.badge_title.setText("🔍 KHÔNG RÕ THỂ LOẠI (FALLBACK ID)")
                self.info_badge.setStyleSheet("background-color: rgba(255, 189, 46, 0.1); border: 1px solid rgba(255, 189, 46, 0.2);")

            self.lesson_label.setText(f"Lesson ID: {lesson_id}")
            self.current_parsed_lesson_id = lesson_id

        except Exception as e:
            self.domain_label.setText("Tên miền: Lỗi phân tích")
            self.lesson_label.setText(f"Lỗi: {str(e)}")

    def save_token_on_edit(self):
        self.config["jwt_token"] = self.token_input.text().strip()
        save_config(self.config)

    def update_config_fields(self):
        self.config["base_url"] = self.base_url_input.text().strip()
        self.config["endpoint"] = self.endpoint_input.text().strip()
        save_config(self.config)

    def toggle_advanced(self, state):
        is_visible = (state == Qt.Checked or state == 2 or state == True)
        self.advanced_widget.setVisible(is_visible)
        
        if is_visible:
            self.resize(380, 620)
        else:
            self.resize(380, 520)

    # --- Start Bypass Process ---
    def start_bypass(self):
        url_text = self.url_input.text().strip()
        if not url_text:
            self.log_in_console("[!] Lỗi: Bạn chưa điền link trang web bài học!", "red")
            return

        lesson_id = getattr(self, "current_parsed_lesson_id", "")
        if not lesson_id or lesson_id == "Không rõ":
            self.log_in_console("[!] Cảnh báo: Không parse được Lesson ID. Thử lấy segment cuối.", "yellow")
            segments = [s for s in urlparse(url_text).path.split('/') if s]
            if segments:
                lesson_id = segments[-1]
            else:
                self.log_in_console("[!] Lỗi: Không thể tìm thấy Lesson ID trong link này.", "red")
                return

        payload = {
            "lesson_id": lesson_id,
            "progress_percent": self.config["progress_percent"],
            "watched_seconds": self.config["watched_seconds"],
            "completed": True
        }

        self.action_btn.setEnabled(False)
        self.action_btn.setText("⏳ ĐANG XỬ LÝ BYPASS...")
        self.log_in_console(f"\n--- Bắt đầu yêu cầu cho bài học: {lesson_id} ---", "white")

        self.worker = BypassWorker(
            base_url=self.config["base_url"],
            endpoint=self.config["endpoint"],
            jwt_token=self.config["jwt_token"],
            payload=payload
        )
        self.worker.log_signal.connect(self.handle_worker_log)
        self.worker.finished_signal.connect(self.handle_worker_finished)
        self.worker.start()

    def handle_worker_log(self, text, color):
        self.log_in_console(text, color)

    def handle_worker_finished(self, success, message):
        self.action_btn.setEnabled(True)
        self.action_btn.setText("⚡ KÍCH HOẠT HOÀN THÀNH (BYPASS)")
        
        if success:
            self.log_in_console(f"[🏆 SUCCESS] {message}", "lightgreen")
        else:
            self.log_in_console(f"[❌ FAILED] {message}", "red")

    def log_in_console(self, text, color="white"):
        color_map = {
            "white": "#e2e8f0",
            "green": "#39ff14",
            "lightgreen": "#adff2f",
            "red": "#ff4d4d",
            "yellow": "#ffbd2e",
            "cyan": "#00e5ff",
            "gray": "#71717a"
        }
        hex_color = color_map.get(color, "#e2e8f0")
        
        html_msg = f"<span style='color: {hex_color};'>{text.replace('\n', '<br>')}</span>"
        self.console.appendHtml(html_msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(22, 28, 41))
    palette.setColor(QPalette.WindowText, Qt.white)
    app.setPalette(palette)
    
    gui = FloatingBypassApp()
    gui.show()
    sys.exit(app.exec())
