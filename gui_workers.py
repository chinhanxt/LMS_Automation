# -*- coding: utf-8 -*-
import time
import random
import re
import requests
import json
import websocket

try:
    from PyQt5.QtCore import QThread, pyqtSignal as Signal
except ImportError:
    from PySide6.QtCore import QThread, Signal

from chrome_automation import ChromeAutomation
from gemini_client import GeminiClient

def format_time(seconds):
    if seconds is None or seconds < 0:
        return "00:00"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class SpeedControllerWorker(QThread):
    log_signal = Signal(str, str)
    progress_signal = Signal(float, float)
    finished_signal = Signal(bool, str)

    def __init__(self, target_url, speed, debug_port, mute_video, action_mode, remaining_seconds):
        super().__init__()
        self.target_url = target_url.strip()
        self.speed = speed
        self.debug_port = debug_port
        self.mute_video = mute_video
        self.action_mode = action_mode
        self.remaining_seconds = remaining_seconds
        self.automation = ChromeAutomation(debug_port)

    def run(self):
        self.log_signal.emit(f"[*] Đang kết nối tới trình duyệt (Port: {self.debug_port})...", "cyan")
        tab = self.automation.find_matching_tab(self.target_url)
        if not tab:
            self.log_signal.emit("[!] Không tìm thấy tab nào khớp với URL.", "yellow")
            self.finished_signal.emit(False, "Không tìm thấy tab")
            return

        self.log_signal.emit(f"[+] Đang kết nối tab: \"{tab.get('title')[:35]}\"...", "lightgreen")
        
        try:
            contexts = self.automation.get_all_contexts(tab)
            self.log_signal.emit(f"[*] Phát hiện {len(contexts)} khung hình (contexts)...", "cyan")
            
            success_count = 0
            mute_js = "v.muted = true;\n" if self.mute_video else ""

            for ctx_id, origin in contexts:
                # Check video duration
                get_dur_js = "document.querySelector('video') ? document.querySelector('video').duration : 0"
                try:
                    duration = self.automation.execute_js_on_tab(tab, get_dur_js, context_id=ctx_id)
                except Exception:
                    duration = 0

                if not duration or duration <= 0:
                    continue

                self.log_signal.emit(f"[*] Phát hiện video dài {int(duration)}s tại {origin[:20]}...", "cyan")

                # Override buffer played
                override_js = (
                    "var v = document.querySelector('video');\n"
                    "if (v) {\n"
                    "    var fakeRanges = {\n"
                    "        length: 1,\n"
                    "        start: function(i) { return 0; },\n"
                    "        end: function(i) { return " + str(duration) + "; }\n"
                    "    };\n"
                    "    try {\n"
                    "        Object.defineProperty(v, 'played', { get: function() { return fakeRanges; }, configurable: true });\n"
                    "        Object.defineProperty(v, 'buffered', { get: function() { return fakeRanges; }, configurable: true });\n"
                    "    } catch(e) {}\n"
                    "}"
                )
                self.automation.execute_js_on_tab(tab, override_js, context_id=ctx_id)

                # Inject unified seek-bypass patch (lies about seek to LMS script, and blocks snapback calls)
                unified_seek_patch = (
                    "var v = document.querySelector('video');\n"
                    "if (v && !v.dataset.seekPatched) {\n"
                    "    v.dataset.seekPatched = 'true';\n"
                    "    try {\n"
                    "        var origDescriptor = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime');\n"
                    "        Object.defineProperty(v, 'currentTime', {\n"
                    "            get: function() {\n"
                    "                if (window.isBypassingSeek) {\n"
                    "                    return window.lastTimeVal !== undefined ? window.lastTimeVal : origDescriptor.get.call(this);\n"
                    "                }\n"
                    "                return origDescriptor.get.call(this);\n"
                    "            },\n"
                    "            set: function(val) {\n"
                    "                var current = origDescriptor.get.call(this);\n"
                    "                var stack = new Error().stack || '';\n"
                    "                if (val < current && (stack.includes('seeking') || stack.includes('seeked') || stack.includes('EventListener') || stack.includes('timeupdate'))) {\n"
                    "                    console.log('Blocked snapback from', current, 'to', val);\n"
                    "                    return;\n"
                    "                }\n"
                    "                origDescriptor.set.call(this, val);\n"
                    "            },\n"
                    "            configurable: true\n"
                    "        });\n"
                    "    } catch(e) {}\n"
                    "}"
                )
                self.automation.execute_js_on_tab(tab, unified_seek_patch, context_id=ctx_id)

                if self.action_mode == "skip":
                    # Override checkCompletion and send completion status directly
                    bypass_lms_js = (
                        "if (typeof sendCompletionStatus === 'function') {\n"
                        "    sendCompletionStatus(true);\n"
                        "}\n"
                        "window.checkCompletion = function() {\n"
                        "    if (typeof sendCompletionStatus === 'function') { sendCompletionStatus(true); }\n"
                        "    var statStatus = document.getElementById('stat-status');\n"
                        "    if (statStatus) { statStatus.innerHTML = '<span class=\"status-completed\">🎉 HOÀN THÀNH BÀI HỌC</span>'; }\n"
                        "};"
                    )
                    self.automation.execute_js_on_tab(tab, bypass_lms_js, context_id=ctx_id)

                    target_time = duration - self.remaining_seconds
                    if target_time <= 0:
                        target_time = duration - 2

                    # Run seek simulation loop in JS inside browser (single call) to bypass restrictions & socket overhead
                    seek_js = (
                        f"(function() {{\n"
                        f"    var v = document.querySelector('video');\n"
                        f"    if (!v) return false;\n"
                        f"    var duration = v.duration;\n"
                        f"    if (!duration || isNaN(duration)) return false;\n"
                        f"    var targetTime = duration - {self.remaining_seconds};\n"
                        f"    if (targetTime <= 0) targetTime = duration - 2;\n"
                        f"    window.isBypassingSeek = true;\n"
                        f"    var steps = 50;\n"
                        f"    var stepVal = targetTime / steps;\n"
                        f"    for (var i = 0; i <= steps; i++) {{\n"
                        f"        var currentTime = Math.min(i * stepVal, targetTime);\n"
                        f"        window.lastTimeVal = currentTime;\n"
                        f"        v.currentTime = currentTime;\n"
                        f"        v.dispatchEvent(new Event('timeupdate'));\n"
                        f"    }}\n"
                        f"    v.currentTime = targetTime;\n"
                        f"    setTimeout(function() {{\n"
                        f"        window.isBypassingSeek = false;\n"
                        f"    }}, 500);\n"
                        f"    return targetTime;\n"
                        f"}})();"
                    )
                    actual_target = self.automation.execute_js_on_tab(tab, seek_js, context_id=ctx_id)
                    if not actual_target:
                        actual_target = target_time

                    # Smoothly animate progress bar locally in Python (no WebSockets calls)
                    steps = 50
                    step_val = actual_target / steps
                    for i in range(steps + 1):
                        current_time = min(i * step_val, actual_target)
                        self.progress_signal.emit(current_time, duration)
                        time.sleep(0.01)

                    play_js = (
                        "var v = document.querySelector('video');\n"
                        "if (v) {\n"
                        "    if (v.playbackRate !== " + str(self.speed) + ") {\n"
                        "        v.playbackRate = " + str(self.speed) + ";\n"
                        "    }\n"
                        "    " + mute_js +
                        "    if (v.paused) {\n"
                        "        v.play();\n"
                        "    }\n"
                        "}"
                    )
                    self.automation.execute_js_on_tab(tab, play_js, context_id=ctx_id)
                    
                else:  # speed mode
                    play_js = (
                        "var v = document.querySelector('video');\n"
                        "if (v) {\n"
                        "    if (v.playbackRate !== " + str(self.speed) + ") {\n"
                        "        v.playbackRate = " + str(self.speed) + ";\n"
                        "    }\n"
                        "    " + mute_js +
                        "    if (v.paused) {\n"
                        "        v.play();\n"
                        "    }\n"
                        "}"
                    )
                    self.automation.execute_js_on_tab(tab, play_js, context_id=ctx_id)
                    self.progress_signal.emit(duration, duration)

                success_count += 1

            if success_count > 0:
                self.finished_signal.emit(True, f"Đã xử lý xong {success_count} video!")
            else:
                self.finished_signal.emit(False, "Không tìm thấy video nào.")
        except Exception as e:
            self.finished_signal.emit(False, f"Lỗi: {str(e)}")


class AutoLearnWorker(QThread):
    log_signal = Signal(str, str)
    progress_signal = Signal(float, float)
    finished_signal = Signal(bool, str)
    status_signal = Signal(str)

    def __init__(self, target_url, speed, debug_port, mute_video, remaining_seconds, auto_skip_video):
        super().__init__()
        self.target_url = target_url.strip()
        self.speed = speed
        self.debug_port = debug_port
        self.mute_video = mute_video
        self.remaining_seconds = remaining_seconds
        self.auto_skip_video = auto_skip_video
        self.running = True
        self.skipped_urls = set()
        self.automation = ChromeAutomation(debug_port)

    def interruptible_sleep(self, seconds):
        steps = int(seconds * 10)
        for _ in range(steps):
            if not self.running:
                break
            time.sleep(0.1)

    def run(self):
        self.log_signal.emit("[▶] Đang khởi động chế độ tự động học...", "green")
        
        while self.running:
            tab = self.automation.find_matching_tab(self.target_url)
            if not tab:
                self.status_signal.emit("Không tìm thấy tab")
                self.interruptible_sleep(2.0)
                continue

            try:
                # 1. Check for quizzes/essays
                status_js = """
                (function() {
                    var isQuiz = false;
                    var quizKeywords = ['bài tập', 'trắc nghiệm', 'tự luận', 'nộp bài', 'câu hỏi', 'quiz', 'assignment', 'questionnaire'];
                    var pageText = document.body.innerText.toLowerCase();
                    
                    var hasInputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]').length > 0;
                    var hasSubmit = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"]')).some(el => {
                        var text = (el.value || el.innerText || el.textContent || "").toLowerCase();
                        return text.includes('nộp') || text.includes('gửi') || text.includes('submit');
                    });
                    
                    var hasEdxQuiz = document.querySelectorAll('.problem, .problem-header, .capa_inputtype, .quiz-question').length > 0;
                    var hasFileInput = document.querySelectorAll('input[type="file"]').length > 0;
                    
                    if (hasEdxQuiz || hasFileInput || (hasInputs && hasSubmit)) {
                        isQuiz = true;
                    } else {
                        var matchCount = 0;
                        quizKeywords.forEach(function(kw) {
                            if (pageText.includes(kw)) matchCount++;
                        });
                        if (matchCount >= 3) {
                            isQuiz = true;
                        }
                    }
                    return { isQuiz: isQuiz, url: window.location.href };
                })();
                """
                val = self.automation.execute_js_on_tab(tab, status_js)
                is_quiz = val.get("isQuiz", False) if val else False
                current_url = val.get("url", "") if val else tab.get("url", "")

                if is_quiz:
                    self.log_signal.emit(f"[⚠️ WARNING] Phát hiện bài tập / tự luận tại trang này. Dừng tự động học để bạn xử lý.", "yellow")
                    self.status_signal.emit("Tạm dừng (Bài tập)")
                    self.finished_signal.emit(False, "Phát hiện bài tập/tự luận.")
                    break

                # 2. Check for video
                contexts = self.automation.get_all_contexts(tab)
                has_video = False
                video_ended = False
                video_duration = 0
                video_current_time = 0
                video_context_id = None

                for ctx_id, origin in contexts:
                    video_check_js = """
                    (function() {
                        var v = document.querySelector('video');
                        if (v) {
                            return {
                                hasVideo: true,
                                ended: v.ended,
                                duration: v.duration || 0,
                                currentTime: v.currentTime || 0
                            };
                        }
                        return { hasVideo: false };
                    })();
                    """
                    try:
                        val_vid = self.automation.execute_js_on_tab(tab, video_check_js, context_id=ctx_id)
                        if val_vid and val_vid.get("hasVideo"):
                            has_video = True
                            video_ended = val_vid.get("ended", False)
                            video_duration = val_vid.get("duration", 0)
                            video_current_time = val_vid.get("currentTime", 0)
                            video_context_id = ctx_id
                            break
                    except Exception:
                        pass

                if has_video:
                    if video_duration <= 0:
                        # Video exists but metadata not loaded yet. Wait.
                        self.status_signal.emit("Đang tải video...")
                        self.interruptible_sleep(1.0)
                        continue

                    # Apply unified seek patch first to remove restrictive locks and lie to LMS script
                    self.run_unified_seek_patch(tab, video_context_id)

                    target_time = video_duration - self.remaining_seconds
                    if target_time <= 0:
                        target_time = max(0, video_duration - 2)

                    completion_target = max(0.0, video_duration - 1.0)
                    if video_ended or video_current_time >= completion_target:
                        self.log_signal.emit("[✔] Video đã hoàn thành. Chuẩn bị chuyển bài tiếp theo...", "lightgreen")
                        self.status_signal.emit("Chuyển tiếp...")
                        self.interruptible_sleep(2.0)
                        if not self.running:
                            break
                        self.click_next_btn(tab)
                        self.interruptible_sleep(3.5)
                        continue
                    else:
                        if self.auto_skip_video:
                            if current_url not in self.skipped_urls:
                                self.log_signal.emit(f"[*] Phát hiện video dài {int(video_duration)}s. Đang tự động tua...", "cyan")
                                self.status_signal.emit("Đang tua video...")
                                self.run_skip_on_context(tab, video_context_id, video_duration)
                                self.skipped_urls.add(current_url)
                            else:
                                self.status_signal.emit("Đang phát nốt...")
                                self.run_play_only_on_context(tab, video_context_id)
                                self.progress_signal.emit(video_current_time, video_duration)
                        else:
                            self.status_signal.emit("Đang học video...")
                            self.run_play_only_on_context(tab, video_context_id)
                            self.progress_signal.emit(video_current_time, video_duration)
                else:
                    self.log_signal.emit("[✔] Trang tài liệu đọc. Chờ học 3 giây...", "white")
                    self.status_signal.emit("Đang đọc tài liệu...")
                    self.progress_signal.emit(100, 100)
                    self.interruptible_sleep(3.0)
                    if not self.running:
                        break
                    self.log_signal.emit("[*] Hết thời gian chờ. Chuyển sang bài tiếp theo...", "lightgreen")
                    self.click_next_btn(tab)
                    self.interruptible_sleep(3.5)
                    continue

                self.interruptible_sleep(2.0)
            except Exception as e:
                self.status_signal.emit("Lỗi kết nối...")
                self.interruptible_sleep(3.0)

        self.status_signal.emit("Đang tắt")
        self.finished_signal.emit(True, "Đã dừng tự động học")

    def run_unified_seek_patch(self, tab, ctx_id):
        unified_seek_patch = (
            "var v = document.querySelector('video');\n"
            "if (v && !v.dataset.seekPatched) {\n"
            "    v.dataset.seekPatched = 'true';\n"
            "    try {\n"
            "        var origDescriptor = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime');\n"
            "        Object.defineProperty(v, 'currentTime', {\n"
            "            get: function() {\n"
            "                if (window.isBypassingSeek) {\n"
                    "                    return window.lastTimeVal !== undefined ? window.lastTimeVal : origDescriptor.get.call(this);\n"
            "                }\n"
            "                return origDescriptor.get.call(this);\n"
            "            },\n"
            "            set: function(val) {\n"
            "                var current = origDescriptor.get.call(this);\n"
            "                var stack = new Error().stack || '';\n"
            "                if (val < current && (stack.includes('seeking') || stack.includes('seeked') || stack.includes('EventListener') || stack.includes('timeupdate'))) {\n"
            "                    console.log('Blocked snapback from', current, 'to', val);\n"
            "                    return;\n"
            "                }\n"
            "                origDescriptor.set.call(this, val);\n"
            "            },\n"
            "            configurable: true\n"
            "        });\n"
            "    } catch(e) {}\n"
            "}"
        )
        self.automation.execute_js_on_tab(tab, unified_seek_patch, context_id=ctx_id)

    def run_play_only_on_context(self, tab, ctx_id):
        mute_js = "v.muted = true;\n" if self.mute_video else ""
        play_js = (
            "var v = document.querySelector('video');\n"
            "if (v) {\n"
            "    if (v.playbackRate !== " + str(self.speed) + ") {\n"
            "        v.playbackRate = " + str(self.speed) + ";\n"
            "    }\n"
            "    " + mute_js +
            "    if (v.paused) {\n"
            "        v.play();\n"
            "    }\n"
            "}"
        )
        self.automation.execute_js_on_tab(tab, play_js, context_id=ctx_id)

    def run_skip_on_context(self, tab, ctx_id, duration):
        override_js = (
            "var v = document.querySelector('video');\n"
            "if (v) {\n"
            "    var fakeRanges = {\n"
            "        length: 1,\n"
            "        start: function(i) { return 0; },\n"
            "        end: function(i) { return " + str(duration) + "; }\n"
            "    };\n"
            "    try {\n"
            "        Object.defineProperty(v, 'played', { get: function() { return fakeRanges; }, configurable: true });\n"
            "        Object.defineProperty(v, 'buffered', { get: function() { return fakeRanges; }, configurable: true });\n"
            "    } catch(e) {}\n"
            "}"
        )
        self.automation.execute_js_on_tab(tab, override_js, context_id=ctx_id)
        
        # Override checkCompletion and send completion status directly
        bypass_lms_js = (
            "if (typeof sendCompletionStatus === 'function') {\n"
            "    sendCompletionStatus(true);\n"
            "}\n"
            "window.checkCompletion = function() {\n"
            "    if (typeof sendCompletionStatus === 'function') { sendCompletionStatus(true); }\n"
            "    var statStatus = document.getElementById('stat-status');\n"
            "    if (statStatus) { statStatus.innerHTML = '<span class=\"status-completed\">🎉 HOÀN THÀNH BÀI HỌC</span>'; }\n"
            "};"
        )
        self.automation.execute_js_on_tab(tab, bypass_lms_js, context_id=ctx_id)

        # Inject unified seek-bypass patch
        self.run_unified_seek_patch(tab, ctx_id)

        target_time = duration - self.remaining_seconds
        if target_time <= 0:
            target_time = duration - 2
            
        seek_js = (
            f"(function() {{\n"
            f"    var v = document.querySelector('video');\n"
            f"    if (!v) return false;\n"
            f"    var duration = v.duration;\n"
            f"    if (!duration || isNaN(duration)) return false;\n"
            f"    var targetTime = duration - {self.remaining_seconds};\n"
            f"    if (targetTime <= 0) targetTime = duration - 2;\n"
            f"    window.isBypassingSeek = true;\n"
            f"    var steps = 50;\n"
            f"    var stepVal = targetTime / steps;\n"
            f"    for (var i = 0; i <= steps; i++) {{\n"
            f"        var currentTime = Math.min(i * stepVal, targetTime);\n"
            f"        window.lastTimeVal = currentTime;\n"
            f"        v.currentTime = currentTime;\n"
            f"        v.dispatchEvent(new Event('timeupdate'));\n"
            f"    }}\n"
            f"    v.currentTime = targetTime;\n"
            f"    setTimeout(function() {{\n"
            f"        window.isBypassingSeek = false;\n"
            f"    }}, 500);\n"
            f"    return targetTime;\n"
            f"}})();"
        )
        actual_target = self.automation.execute_js_on_tab(tab, seek_js, context_id=ctx_id)
        if not actual_target:
            actual_target = target_time

        # Smoothly animate progress bar locally
        steps = 50
        step_val = actual_target / steps
        for i in range(steps + 1):
            if not self.running:
                return
            current_time = min(i * step_val, actual_target)
            self.progress_signal.emit(current_time, duration)
            time.sleep(0.01)
            
        mute_js = "v.muted = true;\n" if self.mute_video else ""
        play_js = (
            "var v = document.querySelector('video');\n"
            "if (v) {\n"
            "    if (v.playbackRate !== " + str(self.speed) + ") {\n"
            "        v.playbackRate = " + str(self.speed) + ";\n"
            "    }\n"
            "    " + mute_js +
            "    if (v.paused) {\n"
            "        v.play();\n"
            "    }\n"
            "}"
        )
        self.automation.execute_js_on_tab(tab, play_js, context_id=ctx_id)

    def click_next_btn(self, tab):
        click_js = """
        (function() {
            function isVisibleAndEnabled(el) {
                if (!el) return false;
                if (el.disabled) return false;
                if (el.classList.contains('disabled')) return false;
                if (el.getAttribute('aria-disabled') === 'true') return false;
                
                // Check computed style
                try {
                    let style = window.getComputedStyle(el);
                    if (style.display === 'none') return false;
                    if (style.visibility === 'hidden') return false;
                } catch(e) {}
                
                // Check rendering size
                let rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return false;
                
                return true;
            }

            // Priority 1: Check known sequence navigation next buttons (specific classes and aria-labels)
            let selectors = [
                'button.next-button',
                'a.next-button',
                '[aria-label*="Tiếp theo"]',
                '[aria-label*="tiếp theo"]',
                '[aria-label*="Next"]',
                '[aria-label*="next"]',
                'button.button-next',
                'button.sequence-navigation-next',
                'a.button-next',
                'a.sequence-navigation-next',
                '.sequence-nav-button.button-next',
                '.next a',
                'button.next-btn',
                'a.next-btn',
                '#next-btn',
                '.btn-next'
            ];
            for (let sel of selectors) {
                let el = document.querySelector(sel);
                if (isVisibleAndEnabled(el)) {
                    el.click();
                    return true;
                }
            }

            // Priority 2: Scan all clickable elements for text matches (English and Vietnamese)
            let clickables = Array.from(document.querySelectorAll('button, a, [role="button"], .sequence-nav-button'));
            let keywords = ['tiếp theo', 'tiếp tục', 'kế tiếp', 'tiếp', 'bài sau', 'next', 'forward', '>'];
            for (let el of clickables) {
                if (!isVisibleAndEnabled(el)) {
                    continue;
                }
                let text = (el.innerText || el.textContent || "").toLowerCase().trim();
                for (let kw of keywords) {
                    if (text === kw || (text.includes(kw) && text.length < 25)) {
                        el.click();
                        return true;
                    }
                }
            }

            // Priority 3: Fallback to elements containing classes or IDs with 'next' but filter for button/link-like elements
            let fallbackElms = Array.from(document.querySelectorAll('[class*="next"], [id*="next"]'));
            for (let el of fallbackElms) {
                let tagName = el.tagName.toLowerCase();
                if (tagName === 'button' || tagName === 'a' || el.getAttribute('role') === 'button' || el.classList.contains('btn') || el.classList.contains('button')) {
                    if (isVisibleAndEnabled(el)) {
                        el.click();
                        return true;
                    }
                }
            }

            // Priority 4: Look for sequence navigation right arrow button specifically
            let rightArrowNav = document.querySelector('.sequence-nav-button[data-direction="next"]');
            if (isVisibleAndEnabled(rightArrowNav)) {
                rightArrowNav.click();
                return true;
            }

            return false;
        })();
        """
        try:
            clicked = self.automation.execute_js_on_tab(tab, click_js)
            if clicked:
                self.log_signal.emit("[✔] Đã tự chuyển sang bài tiếp theo.", "lightgreen")
            else:
                self.log_signal.emit("[!] Không tự click được nút Next. Hãy click thủ công.", "yellow")
        except Exception:
            pass


class AIScanWorker(QThread):
    finished_signal = Signal(dict, str)  # (result_dict, error_message)

    def __init__(self, debug_port, target_url, question_number, quiz_mode="auto"):
        super().__init__()
        self.debug_port = debug_port
        self.target_url = target_url
        self.question_number = question_number
        self.quiz_mode = quiz_mode
        self.automation = ChromeAutomation(debug_port)

    def run(self):
        tab = self.automation.find_matching_tab(self.target_url)
        if not tab:
            self.finished_signal.emit({}, "Không tìm thấy tab trình duyệt khớp với link bên trái.")
            return

        try:
            res = self.automation.scan_question(tab, self.question_number, quiz_mode=self.quiz_mode)
            if not res:
                self.finished_signal.emit({}, "Không trích xuất được dữ liệu từ DOM của trang web.")
            elif not res.get("success"):
                self.finished_signal.emit({}, res.get("error", "Lỗi không xác định."))
            else:
                self.finished_signal.emit(res, "")
        except Exception as e:
            self.finished_signal.emit({}, f"Lỗi quét DOM: {str(e)}")


class AISolveWorker(QThread):
    finished_signal = Signal(str, str, str)  # (ans_letter, reason, error)

    def __init__(self, client, question_number, question_text, choices=None):
        super().__init__()
        self.client = client
        self.question_number = question_number
        self.question_text = question_text
        self.choices = choices

    def run(self):
        try:
            opt_texts = []
            if self.choices:
                for opt in self.choices:
                    letter = opt.get("letter", "")
                    text = opt.get("text", "")
                    opt_texts.append(f"{letter}. {text}")
            
            solution = self.client.solve_question(self.question_text, opt_texts)
            
            # Match answer letter (A, B, C, D...)
            import re
            match = re.search(r'\b([A-Z])\b', solution)
            ans_letter = match.group(1) if match else "?"
            
            self.finished_signal.emit(ans_letter, solution, "")
        except Exception as e:
            self.finished_signal.emit("", "", str(e))


class AISolveAllWorker(QThread):
    log_signal = Signal(str, str)
    finished_signal = Signal(bool, str)
    update_ui_signal = Signal(str, str, int, int, list)  # (question_text, solution, current_q_num, total_questions, options_list)
    update_signal = Signal(int, str)  # (q_num, ans_letter)

    def __init__(self, debug_port, target_url, api_keys, auto_fill, skip_img, quiz_mode="auto"):
        super().__init__()
        self.debug_port = debug_port
        self.target_url = target_url
        self.api_keys = api_keys
        self.auto_fill = auto_fill
        self.skip_img = skip_img
        self.quiz_mode = quiz_mode
        self.automation = ChromeAutomation(debug_port)
        self.client = GeminiClient(api_keys=api_keys)
        self.running = True
        self.solved_answers = {}

    def run(self):
        tab = self.automation.find_matching_tab(self.target_url)
        if not tab:
            self.finished_signal.emit(False, "Không tìm thấy tab trình duyệt khớp.")
            return

        self.log_signal.emit("[*] Bắt đầu tự động quét và giải toàn bộ đề...", "cyan")

        # 1. Scan the first question to find totalQuestions
        try:
            first_scan = self.automation.scan_question(tab, 1, quiz_mode=self.quiz_mode)
        except Exception as e:
            self.finished_signal.emit(False, f"Lỗi quét câu đầu tiên: {str(e)}")
            return

        if not first_scan or not first_scan.get("success"):
            self.finished_signal.emit(False, f"Lỗi khởi động quét: {first_scan.get('error', 'Không tìm thấy câu hỏi')}")
            return

        total_questions = first_scan.get("totalQuestions", 0)
        self.log_signal.emit(f"[+] Tìm thấy tổng cộng {total_questions} câu hỏi trên trang.", "lightgreen")

        for i in range(1, total_questions + 1):
            if not self.running:
                break

            self.log_signal.emit(f"[*] Đang xử lý Câu {i} / {total_questions}...", "yellow")
            
            try:
                # Scan current question
                if not self.running:
                    break
                scan_res = self.automation.scan_question(tab, i, quiz_mode=self.quiz_mode)
                if not self.running:
                    break
                if not scan_res or not scan_res.get("success"):
                    self.log_signal.emit(f"[❌] Không quét được dữ liệu Câu {i}: {scan_res.get('error')}", "red")
                    continue

                q_text = scan_res.get("questionText", "")
                options = scan_res.get("options", [])
                has_img = scan_res.get("hasImages", False)

                # Format options display
                opt_display_list = []
                opt_texts = []
                for opt in options:
                    letter = chr(65 + opt["index"])  # 0->A, 1->B...
                    text_val = opt["text"].strip()
                    # Strip existing prefix like "A. ", "A) ", etc.
                    text_val = re.sub(r'^[A-Z]\s*[\.\:\-\)]\s*', '', text_val)
                    opt_display_list.append(f"{letter}. {text_val}")
                    opt_texts.append(f"{letter}. {text_val}")

                full_q_display = f"Câu {i}:\n{q_text}\n\nLựa chọn:\n" + "\n".join(opt_display_list)
                
                # Check skip images
                if has_img and self.skip_img:
                    self.log_signal.emit(f"[🖼️] Phát hiện Câu {i} chứa hình ảnh / sơ đồ. Bỏ qua theo cài đặt bảo mật.", "yellow")
                    self.update_ui_signal.emit(full_q_display, "⚠️ BỎ QUA DO CÓ HÌNH ẢNH/SƠ ĐỒ", i, total_questions, opt_display_list)
                    for _ in range(15):
                        if not self.running:
                            break
                        time.sleep(0.1)
                    continue

                if not self.running:
                    break
                self.update_ui_signal.emit(full_q_display, "Đang gửi lên AI...", i, total_questions, opt_display_list)

                # Call Gemini client
                solution = self.client.solve_question(q_text, opt_texts)
                
                if not self.running:
                    break

                # Match answer letter (A, B, C, D...)
                match = re.search(r'\b([A-Z])\b', solution)
                if match:
                    ans_letter = match.group(1)
                    self.solved_answers[i] = ans_letter
                else:
                    ans_letter = "?"
                    self.solved_answers[i] = "Chưa nhận dạng"

                self.update_signal.emit(i, ans_letter)
                self.update_ui_signal.emit(full_q_display, solution, i, total_questions, opt_display_list)
                self.log_signal.emit(f"[✔] Đã giải xong câu {i}: Đáp án [{ans_letter}]", "lightgreen")

                # If auto fill is active
                if self.auto_fill and ans_letter != "?":
                    if not self.running:
                        break
                    opt_idx = ord(ans_letter) - 65
                    click_res = self.automation.click_option(tab, i, opt_idx, quiz_mode=self.quiz_mode)
                    if click_res and click_res.get("success"):
                        self.log_signal.emit(f"    [✍️ Auto-click] Đã chọn đáp án [{ans_letter}] cho Câu {i}.", "lightgreen")
                    else:
                        self.log_signal.emit(f"    [!] Lỗi click đáp án Câu {i}: {click_res.get('error')}", "yellow")

                # Anti-cheat human delay (random between 1.2 and 2.6 seconds)
                delay = random.uniform(1.2, 2.6)
                steps = int(delay * 10)
                for _ in range(steps):
                    if not self.running:
                        break
                    time.sleep(0.1)

            except Exception as e:
                self.log_signal.emit(f"[❌] Lỗi xử lý Câu {i}: {str(e)}", "red")
                for _ in range(20):
                    if not self.running:
                        break
                    time.sleep(0.1)

        # Build final summary of results
        status_str = "Đã hoàn thành" if self.running else "Đã dừng nửa chừng"
        summary_lines = [
            "🏆 --- DANH SÁCH ĐÁP ÁN ĐÃ GIẢI ---",
            f"Trạng thái: {status_str}",
            f"Tiến độ: {len(self.solved_answers)} / {total_questions} câu",
            ""
        ]
        for q_num in sorted(self.solved_answers.keys()):
            summary_lines.append(f"Câu {q_num}: {self.solved_answers[q_num]}")
            
        summary_text = "\n".join(summary_lines)
        self.finished_signal.emit(True, summary_text)


class PromptGenWorker(QThread):
    log_signal = Signal(str, str)
    finished_signal = Signal(str, str)  # (prompt_text, error)

    def __init__(self, debug_port, target_url, max_questions=0, quiz_mode="auto"):
        super().__init__()
        self.debug_port = debug_port
        self.target_url = target_url
        self.max_questions = max_questions
        self.quiz_mode = quiz_mode
        self.automation = ChromeAutomation(debug_port)
        self.running = True

    def run(self):
        tab = self.automation.find_matching_tab(self.target_url)
        if not tab:
            self.finished_signal.emit("", "Không tìm thấy tab trình duyệt khớp.")
            return

        self.log_signal.emit("[*] Đang kết nối Chrome để quét câu hỏi trên trang...", "cyan")
        
        # 1. Scan the first question to find totalQuestions
        try:
            first_scan = self.automation.scan_question(tab, 1, quiz_mode=self.quiz_mode)
        except Exception as e:
            self.finished_signal.emit("", f"Lỗi quét câu đầu tiên: {str(e)}")
            return

        if not first_scan or not first_scan.get("success"):
            self.finished_signal.emit("", f"Lỗi khởi động quét: {first_scan.get('error', 'Không tìm thấy câu hỏi')}")
            return

        total_questions = first_scan.get("totalQuestions", 0)
        
        # Determine scan limit based on max_questions
        if self.max_questions and self.max_questions > 0:
            scan_limit = min(total_questions, self.max_questions)
            self.log_signal.emit(f"[+] Tìm thấy tổng cộng {total_questions} câu hỏi. Đang bắt đầu trích xuất {scan_limit} câu đầu tiên...", "lightgreen")
        else:
            scan_limit = total_questions
            self.log_signal.emit(f"[+] Tìm thấy tổng cộng {total_questions} câu hỏi. Đang bắt đầu trích xuất toàn bộ...", "lightgreen")

        prompt_parts = [
            "Bạn là trợ lý giải trắc nghiệm LMS. Hãy phân tích các câu hỏi dưới đây và trả về đáp án dưới dạng một đối tượng JSON duy nhất, có key là số thứ tự câu hỏi và value là chữ cái đáp án viết hoa (A, B, C, D, E...).\n"
            "Ví dụ định dạng trả về (CHỈ TRẢ VỀ ĐÚNG JSON NÀY, KHÔNG THÊM BẤT KỲ VĂN BẢN GIẢI THÍCH NÀO KHÁC):\n"
            "{\n"
            "  \"1\": \"A\",\n"
            "  \"2\": \"C\",\n"
            "  \"3\": \"B\"\n"
            "}\n\n"
            "Dưới đây là danh sách câu hỏi cần giải:\n"
            "---"
        ]

        for i in range(1, scan_limit + 1):
            if not self.running:
                self.finished_signal.emit("", "Đã dừng quét theo yêu cầu.")
                return

            self.log_signal.emit(f"[*] Đang quét Câu {i} / {scan_limit}...", "yellow")
            
            try:
                scan_res = self.automation.scan_question(tab, i, quiz_mode=self.quiz_mode)
                if not scan_res or not scan_res.get("success"):
                    self.log_signal.emit(f"[❌] Lỗi quét Câu {i}: {scan_res.get('error')}", "red")
                    continue
                
                q_text = scan_res.get("questionText", "")
                options = scan_res.get("options", [])
                
                q_prompt = f"Câu {i}: {q_text}\n"
                for opt in options:
                    letter = chr(65 + opt["index"])
                    text_val = opt["text"].strip()
                    text_val = re.sub(r'^[A-Z]\s*[\.\:\-\)]\s*', '', text_val)
                    q_prompt += f"{letter}. {text_val}\n"
                
                prompt_parts.append(q_prompt)
            except Exception as e:
                self.log_signal.emit(f"[❌] Lỗi quét Câu {i}: {str(e)}", "red")

        prompt_parts.append("---")
        full_prompt = "\n".join(prompt_parts)
        self.finished_signal.emit(full_prompt, "")


class WebClickWorker(QThread):
    log_signal = Signal(str, str)
    finished_signal = Signal(bool, str, str)  # (success, message, color)
    
    def __init__(self, debug_port, target_url, json_answers, quiz_mode="auto"):
        super().__init__()
        self.debug_port = debug_port
        self.target_url = target_url
        self.json_answers = json_answers
        self.quiz_mode = quiz_mode
        self.automation = ChromeAutomation(debug_port)
        self.running = True

    def run(self):
        tab = self.automation.find_matching_tab(self.target_url)
        if not tab:
            self.finished_signal.emit(False, "Không tìm thấy tab trình duyệt khớp.", "red")
            return

        self.log_signal.emit("[*] Bắt đầu tự động click đáp án theo danh sách...", "cyan")
        
        total = len(self.json_answers)
        clicked_count = 0
        
        for q_str, ans_letter in self.json_answers.items():
            if not self.running:
                break
                
            try:
                try:
                    q_num = int(q_str)
                except ValueError:
                    import re
                    digit_match = re.search(r'\d+', q_str)
                    if digit_match:
                        q_num = int(digit_match.group(0))
                    else:
                        self.log_signal.emit(f"[!] Bỏ qua câu hỏi '{q_str}' do định dạng không hợp lệ.", "yellow")
                        continue
                    
                ans_letter = str(ans_letter).strip().upper()
                if not ans_letter or ord(ans_letter) < 65 or ord(ans_letter) > 90:
                    self.log_signal.emit(f"[!] Bỏ qua Câu {q_num} do đáp án '{ans_letter}' không hợp lệ.", "yellow")
                    continue
                    
                self.log_signal.emit(f"[*] Đang click Câu {q_num} -> Đáp án [{ans_letter}]...", "yellow")
                
                # Click
                opt_idx = ord(ans_letter) - 65
                click_res = self.automation.click_option(tab, q_num, opt_idx, quiz_mode=self.quiz_mode)
                
                if click_res and click_res.get("success"):
                    self.log_signal.emit(f"[✔] Đã click chọn đáp án [{ans_letter}] cho Câu {q_num}.", "lightgreen")
                    clicked_count += 1
                else:
                    self.log_signal.emit(f"[❌] Lỗi click Câu {q_num}: {click_res.get('error')}", "red")
                    
                # Random delay between clicks to feel human (0.5 to 1.2s)
                delay = random.uniform(0.5, 1.2)
                steps = int(delay * 10)
                for _ in range(steps):
                    if not self.running:
                        break
                    time.sleep(0.1)
            except Exception as e:
                self.log_signal.emit(f"[❌] Lỗi thực thi click Câu {q_str}: {str(e)}", "red")
                time.sleep(1.0)

        status_msg = f"Đã dừng tiến trình. Đã tự động click {clicked_count}/{total} câu hỏi." if not self.running else f"Đã hoàn thành tự động click {clicked_count}/{total} câu hỏi."
        color_msg = "yellow" if not self.running else "lightgreen"
        self.finished_signal.emit(True, status_msg, color_msg)
