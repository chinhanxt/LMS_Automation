# -*- coding: utf-8 -*-
import os
import requests
import time

class GeminiClient:
    def __init__(self, key_file="keyAI.md", default_model="gemini-1.5-flash", api_keys=None):
        self.key_file = key_file
        self.default_model = default_model
        self.api_keys = api_keys or []

    def get_api_key(self):
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    content = content.replace("`", "").strip()
                    lines = [l.strip() for l in content.splitlines() if l.strip()]
                    for line in lines:
                        if not line.startswith("#") and not line.startswith("["):
                            return line
            except Exception:
                pass
        return ""

    def get_all_keys(self):
        # 1. Start with configured UI keys
        keys = list(self.api_keys)
        
        # 2. Add fallback to local keyAI.md key
        key_file_val = self.get_api_key()
        if key_file_val and key_file_val not in keys:
            keys.append(key_file_val)
            
        return keys

    def solve_question(self, question_text, choices=None, model_name=None):
        keys = self.get_all_keys()
        if not keys:
            raise ValueError("Không tìm thấy API Key nào trong cấu hình hoặc file keyAI.md.")

        # System prompt - strictly return only the letter to save tokens
        system_prompt = (
            "Bạn là trợ lý giải trắc nghiệm LMS cực kỳ chính xác.\n"
            "Hãy phân tích câu hỏi và danh sách lựa chọn bên dưới, sau đó đưa ra đáp án chính xác nhất.\n"
            "Chỉ trả về duy nhất 1 CHỮ CÁI viết hoa đại diện cho đáp án được chọn (ví dụ: A hoặc B hoặc C hoặc D hoặc E, v.v.).\n"
            "KHÔNG ĐƯỢC GIẢI THÍCH, KHÔNG ĐƯỢC TRẢ LỜI GÌ THÊM, CHỈ TRẢ VỀ ĐÚNG 1 KÝ TỰ CHỮ CÁI DUY NHẤT."
        )

        formatted_question = f"[Câu hỏi]:\n{question_text}"
        if choices:
            formatted_question += "\n\n[Danh sách lựa chọn]:\n" + "\n".join(choices)
            
        full_prompt = f"{system_prompt}\n\n{formatted_question}"

        last_error = None
        
        for key_idx, key in enumerate(keys):
            is_groq = key.startswith("gsk_")
            
            if is_groq:
                # --- Groq Key Router ---
                groq_models = ["llama-3.3-70b-versatile", "llama-3-8b-8192", "mixtral-8x7b-32768"]
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                
                for model in groq_models:
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "user", "content": full_prompt}
                        ],
                        "temperature": 0.2
                    }
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    
                    try:
                        response = requests.post(url, headers=headers, json=payload, timeout=20)
                        if response.status_code == 200:
                            res_json = response.json()
                            choices_res = res_json.get("choices", [])
                            if choices_res:
                                text = choices_res[0].get("message", {}).get("content", "")
                                return text.strip()
                            else:
                                raise ValueError("Không tìm thấy câu trả lời trong phản hồi Groq.")
                        elif response.status_code == 429:
                            raise ValueError(f"Mã 429 (Resource Exhausted) trên Groq với model {model}.")
                        else:
                            raise ValueError(f"Lỗi API Groq (Mã {response.status_code}): {response.text}")
                    except (requests.exceptions.RequestException, ValueError) as e:
                        last_error = f"Groq Key #{key_idx+1} ({model}): {str(e)}"
                        if "Mã 429" in str(e):
                            break
                        continue
            else:
                # --- Gemini Key Router ---
                target_model = model_name or self.default_model
                gemini_models = [target_model]
                for m in ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-2.5-flash"]:
                    if m not in gemini_models:
                        gemini_models.append(m)
                        
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": full_prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.2
                    }
                }
                
                for model in gemini_models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                    
                    try:
                        response = requests.post(url, headers=headers, json=payload, timeout=25)
                        if response.status_code == 200:
                            res_json = response.json()
                            candidates = res_json.get("candidates", [])
                            if candidates:
                                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                return text.strip()
                            else:
                                raise ValueError("Không tìm thấy câu trả lời trong phản hồi Gemini.")
                        elif response.status_code == 429:
                            raise ValueError(f"Mã 429 (Resource Exhausted) trên Gemini với model {model}.")
                        else:
                            raise ValueError(f"Lỗi API Gemini (Mã {response.status_code}): {response.text}")
                    except (requests.exceptions.RequestException, ValueError) as e:
                        last_error = f"Gemini Key #{key_idx+1} ({model}): {str(e)}"
                        if "Mã 429" in str(e):
                            break
                        continue
                        
        raise ConnectionError(f"Tất cả các API Keys đều lỗi hoặc hết quota. Lỗi cuối: {str(last_error)}")
