#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import http.server
import json
import os
import re
import sys

PORT = 3001

# Trạng thái học tập giả lập trên server
lesson_status = {
    "completed": False,
    "progress_percent": 0,
    "watched_seconds": 0
}

# Tìm file video MP4 có sẵn trong máy để stream
VIDEO_PATH = "/home/chinhan/Downloads/YTSave_YouTube_Luyen-Nghe-Tieng-Anh-Co-Ban-A1-Nguoi-Vie_Media_4ycKrWTvzNY_006_144p.mp4"
if not os.path.exists(VIDEO_PATH):
    # Nếu file kia không tồn tại, tìm bất kỳ file MP4 nào trong Downloads
    downloads_dir = "/home/chinhan/Downloads"
    if os.path.exists(downloads_dir):
        files = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".mp4")]
        if files:
            VIDEO_PATH = files[0]

class MockLMSHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Ghi log ra stdout/log file
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format%args))

    def do_OPTIONS(self):
        # Hỗ trợ CORS
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        global VIDEO_PATH
        # Hỗ trợ CORS cho mọi GET request
        if self.path == "/" or self.path == "/index.html" or self.path == "/mock_video_test.html":
            self.serve_html()
        elif self.path.startswith("/video"):
            self.serve_video()
        elif self.path == "/api/status":
            self.send_json(200, lesson_status)
        else:
            # Phục vụ file tĩnh khác nếu có
            file_name = self.path.lstrip("/")
            if os.path.exists(file_name) and os.path.isfile(file_name):
                self.serve_static_file(file_name)
            else:
                self.send_error(404, "File Not Found")

    def do_POST(self):
        global lesson_status
        if self.path == "/api/lessons/complete":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                lesson_status["completed"] = data.get("completed", True)
                lesson_status["progress_percent"] = data.get("progress_percent", 100)
                lesson_status["watched_seconds"] = data.get("watched_seconds", 0)
                
                print(f"[Server] Đã nhận tín hiệu hoàn thành: {data}")
                self.send_json(200, {"status": "success", "data": lesson_status})
            except Exception as e:
                self.send_json(400, {"status": "error", "message": str(e)})
        else:
            self.send_error(404, "Not Found")

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def serve_html(self):
        html_path = "mock_video_test.html"
        if not os.path.exists(html_path):
            self.send_error(404, "mock_video_test.html not found on server")
            return
            
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def serve_static_file(self, file_name):
        self.send_response(200)
        if file_name.endswith(".js"):
            self.send_header("Content-Type", "application/javascript")
        elif file_name.endswith(".css"):
            self.send_header("Content-Type", "text/css")
        elif file_name.endswith(".html") or file_name.endswith(".htm"):
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        with open(file_name, "rb") as f:
            self.wfile.write(f.read())

    def serve_video(self):
        global VIDEO_PATH
        if not os.path.exists(VIDEO_PATH):
            self.send_error(404, f"Video file not found: {VIDEO_PATH}")
            return

        file_size = os.path.getsize(VIDEO_PATH)
        range_header = self.headers.get("Range")

        # Xử lý HTTP Range (206 Partial Content) để Chrome có thể seek mượt mà
        if range_header:
            match = re.search(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                start = int(match.group(1))
                end = match.group(2)
                end = int(end) if end else file_size - 1

                if start >= file_size:
                    self.send_error(416, "Requested Range Not Satisfiable")
                    return

                self.send_response(206)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(end - start + 1))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(VIDEO_PATH, "rb") as f:
                    f.seek(start)
                    chunk_size = 65536
                    bytes_to_send = end - start + 1
                    while bytes_to_send > 0:
                        chunk = f.read(min(chunk_size, bytes_to_send))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        bytes_to_send -= len(chunk)
                return

        # Phục vụ toàn bộ file (200 OK)
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        with open(VIDEO_PATH, "rb") as f:
            chunk_size = 65536
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                self.wfile.write(chunk)

def run():
    print(f"[*] Khởi chạy server trên cổng {PORT}...")
    print(f"[*] Sử dụng file video: {VIDEO_PATH}")
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, MockLMSHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Đang dừng server...")
        httpd.server_close()
        sys.exit(0)

if __name__ == "__main__":
    run()