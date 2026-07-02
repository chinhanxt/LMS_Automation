#!/bin/bash
# Script khởi chạy Demo LMS: cả Server Mockup và Giao diện nổi

cd "$(dirname "$0")"

# 1. Khởi chạy Mock LMS Server
echo "[*] Đang khởi động Mock LMS Server trên cổng 3001..."
nohup ./.venv/bin/python3 mock_lms_server.py > mock_server.log 2>&1 &
SERVER_PID=$!

# Đợi 1 giây để server khởi động hoàn tất
sleep 1

# 2. Khởi chạy Giao diện nổi UI Bypass
echo "[*] Đang khởi động Giao diện nổi LMS Bypass..."
nohup ./.venv/bin/python3 floating_bypass_ui.py > ui.log 2>&1 &
UI_PID=$!

echo -e "\033[0;32m[+] Khởi chạy thành công!\033[0m"
echo -e "  - Mock LMS Server đang chạy (PID: $SERVER_PID). Xem log tại: mock_server.log"
echo -e "  - Web Demo: http://localhost:3001"
echo -e "  - Giao diện nổi UI đang chạy (PID: $UI_PID). Xem log tại: ui.log"
echo -e "\033[0;33m[*] Để tắt demo, hãy chạy lệnh: kill $SERVER_PID $UI_PID\033[0m"
