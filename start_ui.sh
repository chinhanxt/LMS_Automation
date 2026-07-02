#!/bin/bash
# Script khởi chạy nhanh giao diện nổi LMS Video Speeder

# Di chuyển vào thư mục chứa script
cd "$(dirname "$0")"

# Chạy ứng dụng ẩn dưới nền
nohup ./.venv/bin/python3 floating_speed_ui.py > /dev/null 2>&1 &

echo -e "\033[0;32m[+] Giao diện nổi LMS Video Speeder đã được khởi chạy ở chế độ chạy ngầm!\033[0m"
echo -e "[*] Bạn có thể kéo thả cửa sổ này ở bất cứ đâu trên màn hình."
