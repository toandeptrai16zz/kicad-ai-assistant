import os
import json
import urllib.request
import urllib.error
import re
import time
import base64
import base64

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

PROVIDERS = {
    "Google Gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
        "type": "gemini",
        "model": "gemini-flash-latest"
    },
    "DeepSeek": {
        "url": "https://api.deepseek.com/chat/completions",
        "type": "openai",
        "model": "deepseek-chat"
    },
    "Groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "type": "openai",
        "model": "llama-3.3-70b-versatile"
    },
    "OpenAI": {
        "url": "https://api.openai.com/v1/chat/completions",
        "type": "openai",
        "model": "gpt-4o-mini"
    }
}

class AIClient:
    def __init__(self):
        self.config = self._load_config()
        self.active_provider = self.config.get("active_provider", "Google Gemini")
        
        self.schematic_prompt = """
Bạn là một Kỹ sư phần cứng kiêm Mentor chuyên review thiết kế mạch (Schematic) siêu cấp.
Dưới đây là dữ liệu trích xuất từ sơ đồ nguyên lý KiCad (.kicad_sch).
Nhiệm vụ của bạn:
1. Đọc và phân tích thật cặn kẽ danh sách linh kiện và các kết nối.
2. Trình bày bài đánh giá dưới dạng văn bản Markdown chi tiết, rõ ràng, chia làm các mục như Tóm tắt, Nhận xét, Cảnh báo.
3. VỚI MỖI LỖI HOẶC GỢI Ý TÌM THẤY, bạn BẮT BUỘC phải viết rõ 3 phần:
   - Ưu/Nhược điểm của thiết kế hiện tại.
   - Việc cần làm (Gợi ý cách khắc phục cụ thể, ví dụ đổi điện trở thành 2.2k hoặc 4.7k).
   - Kết luận: Có bắt buộc phải làm hay không, hay chỉ là optional.
4. QUAN TRỌNG: KHÔNG sử dụng định dạng toán học LaTeX (như $10k\\Omega$ hoặc $\\mu F$). Hãy viết đơn vị bằng văn bản thuần túy (VD: 10k ohm, 2.2uF, 10uF) để người dùng dễ đọc.
5. Ở DƯỚI CÙNG của câu trả lời, bạn BẮT BUỘC phải đính kèm một khối mã JSON (```json ... ```) chứa các thông số kỹ thuật khô khan để hệ thống Auto-Fix chạy.

Cấu trúc yêu cầu:
(Phần chữ: Markdown giải thích tự do, có sử dụng emoji cho sinh động)

```json
{
  "analysis_summary": "Tóm tắt ngắn gọn 1-2 câu để log hệ thống."
}
```
"""

        self.pcb_prompt = """
Bạn là một Kỹ sư Layout PCB lão làng. 
Dưới đây là dữ liệu trích xuất từ dự án KiCad (số lớp, track width, danh sách component, via, zone).
Nhiệm vụ của bạn:
1. Đánh giá số lớp hiện tại, độ rộng dây nguồn/tín hiệu, vùng đổ đồng, tụ bypass.
2. Trình bày bài đánh giá dưới dạng văn bản Markdown chi tiết, dễ đọc.
3. VỚI MỖI VẤN ĐỀ TÌM THẤY, BẮT BUỘC phân tích theo:
   - Ưu/Nhược điểm hiện tại (Tại sao dây 0.25mm lại dễ cháy nếu chạy nguồn 2A).
   - Việc cần làm (Actionable Steps).
   - Kết luận (Bắt buộc phải sửa hay không).
4. QUAN TRỌNG: KHÔNG sử dụng định dạng toán học LaTeX (như $10k\\Omega$ hoặc $\\mu F$). Hãy viết đơn vị bằng văn bản thuần túy (VD: 10k ohm, 2.2uF, 10uF) để người dùng dễ đọc.
5. Ở DƯỚI CÙNG của câu trả lời, bạn BẮT BUỘC phải đính kèm một khối mã JSON (```json ... ```) chứa cấu hình thông số chuẩn để hệ thống tự động sửa mạch (Auto-Fix).

Cấu trúc yêu cầu:
(Phần chữ: Markdown tự do giải thích siêu chi tiết, có emoji)

```json
{
  "recommended_layers": 4,
  "track_width_vcc_mm": 0.5,
  "track_width_signal_mm": 0.25,
  "missing_bypass_caps": ["U1", "U3"]
}
```
"""

        self.interactive_prompt = """
Bạn là một Chuyên gia phân tích linh kiện và mạch điện (Hardware Mentor).
Người dùng vừa chọn (highlight) một đối tượng trên PCB hoặc Schematic. (Kèm theo thông tin Board bên dưới).
Nhiệm vụ của bạn:
1. Phân tích chi tiết chức năng của linh kiện/đường dây đó.
2. Trình bày dưới dạng văn bản Markdown rõ ràng.
3. BẮT BUỘC phân tích:
   - Ưu/Nhược điểm của cách kết nối hiện tại (VD: Trở 10k thì tiết kiệm điện nhưng sườn xung chậm).
   - Hành động gợi ý.
   - Kết luận đánh giá chung.
4. QUAN TRỌNG: KHÔNG sử dụng định dạng toán học LaTeX (như $10k\\Omega$ hoặc $\\mu F$). Hãy viết đơn vị bằng văn bản thuần túy (VD: 10k ohm, 2.2uF, 10uF) để người dùng dễ đọc.
5. Ở DƯỚI CÙNG, bạn BẮT BUỘC đính kèm khối mã JSON rỗng (chỉ để hệ thống không bị lỗi parser).

Cấu trúc yêu cầu:
(Văn bản Markdown siêu chi tiết giải thích cho người dùng)

```json
{}
```
"""

        self.chat_prompt = """
Bạn là một kỹ sư trưởng thiết kế phần cứng (Hardware Lead Engineer) giàu kinh nghiệm.
Người dùng đang hỏi bạn một câu hỏi tự do về mạch điện của họ.
Tôi có đính kèm danh sách TOÀN BỘ linh kiện trong mạch của họ (project_schematic_context) để bạn có cái nhìn tổng quan (đây là mạch nguồn, mạch flight controller, mạch âm thanh...). Nếu có thông tin về linh kiện đang chọn (context_selected_item) hoặc file PDF đính kèm, hãy ưu tiên kết hợp chúng.

Nhiệm vụ của bạn:
1. Đọc kỹ câu hỏi của người dùng.
2. NGUYÊN TẮC: Luôn nhìn vào danh sách linh kiện tổng thể (project_schematic_context) để trả lời. Nếu người dùng hỏi "đây là mạch gì", hãy liệt kê các IC chính (VD: STM32, ICM-42688) và đưa ra kết luận về chức năng của toàn bộ bo mạch.
3. Trả lời câu hỏi một cách thân thiện, xưng "tôi" gọi "bạn", phân tích sâu sắc như một người hướng dẫn, sử dụng Markdown rõ ràng.
4. QUAN TRỌNG: KHÔNG sử dụng định dạng toán học LaTeX (như $10k\\Omega$ hoặc $\\mu F$). Hãy viết đơn vị bằng văn bản thuần túy (VD: 10k ohm, 2.2uF, 10uF).
5. Ở DƯỚI CÙNG của câu trả lời, bạn BẮT BUỘC đính kèm khối mã JSON rỗng (chỉ để hệ thống không bị lỗi parser).

Cấu trúc yêu cầu:
(Câu trả lời Markdown)

```json
{}
```
"""

    def _load_config(self):
        default_config = {
            "active_provider": "Google Gemini",
            "keys": {}
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    # Migrate old config format if needed
                    if "api_key" in data and isinstance(data["api_key"], str):
                        default_config["keys"]["Google Gemini"] = data["api_key"]
                        self._save_config(default_config)
                        return default_config
                    return data
            except Exception:
                pass
        return default_config

    def _save_config(self, config):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

    def save_api_key(self, provider, key):
        if "keys" not in self.config:
            self.config["keys"] = {}
        self.config["keys"][provider] = key
        self.config["active_provider"] = provider
        self.active_provider = provider
        self._save_config(self.config)

    def get_api_key(self, provider):
        if "keys" not in self.config:
            return ""
        return self.config["keys"].get(provider, "")

    def set_active_provider(self, provider):
        self.active_provider = provider
        self.config["active_provider"] = provider
        self._save_config(self.config)

    def analyze_schematic(self, json_data, pdf_path=None):
        return self._send_request(self.schematic_prompt, json_data, pdf_path)
        
    def analyze_pcb(self, json_data, pdf_path=None):
        return self._send_request(self.pcb_prompt, json_data, pdf_path)
        
    def analyze_selection(self, json_data, pdf_path=None):
        return self._send_request(self.interactive_prompt, json_data, pdf_path)

    def analyze_chat(self, json_data, pdf_path=None):
        return self._send_request(self.chat_prompt, json_data, pdf_path)

    def _send_request(self, system_prompt, data, pdf_path=None):
        provider_info = PROVIDERS.get(self.active_provider)
        if not provider_info:
            return {"error": "Invalid AI Provider selected."}
            
        api_key = self.get_api_key(self.active_provider)
        if not api_key:
            return {"error": f"API Key for {self.active_provider} is not set. Please configure it."}
            
        if pdf_path and provider_info["type"] != "gemini":
            return {"error": f"Lỗi: Tính năng đọc Datasheet/Hình ảnh hiện tại chỉ được hỗ trợ trên mạng Google Gemini. Vui lòng chọn Google Gemini hoặc gỡ file đính kèm."}

        if provider_info["type"] == "gemini":
            return self._send_gemini(api_key, provider_info, system_prompt, data, pdf_path)
        else:
            return self._send_openai_compatible(api_key, provider_info, system_prompt, data)

    def _send_gemini(self, api_key, provider_info, system_prompt, data, pdf_path=None):
        parts = [{"text": f"{system_prompt}\n\nDữ liệu:\n{data}"}]
        
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                file_b64 = base64.b64encode(file_bytes).decode('utf-8')
                
                mime_type = "application/pdf"
                ext = pdf_path.lower()
                if ext.endswith('.png'): mime_type = "image/png"
                elif ext.endswith('.jpg') or ext.endswith('.jpeg'): mime_type = "image/jpeg"
                
                parts.append({
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": file_b64
                    }
                })
            except Exception as e:
                return {"error": f"Không thể đọc file đính kèm: {str(e)}"}

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.2}
        }
        url = f"{provider_info['url']}?key={api_key}"
        return self._do_http_post(url, payload)

    def _send_openai_compatible(self, api_key, provider_info, system_prompt, data):
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": provider_info["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data}
            ],
            "temperature": 0.2
        }
        return self._do_http_post(provider_info['url'], payload, headers)

    def _do_http_post(self, url, payload, extra_headers=None):
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        if extra_headers:
            for k, v in extra_headers.items():
                req.add_header(k, v)
                
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Increased timeout to 60s for heavy AI generation
                with urllib.request.urlopen(req, timeout=60) as response:
                    response_body = response.read().decode('utf-8')
                    result_data = json.loads(response_body)
                    
                    # Extract text based on standard schemas
                    if 'candidates' in result_data: # Gemini
                        text_response = result_data['candidates'][0]['content']['parts'][0]['text']
                    elif 'choices' in result_data: # OpenAI
                        text_response = result_data['choices'][0]['message']['content']
                    else:
                        return {"error": "Unknown API Response structure."}
                        
                    return self._parse_json_response(text_response)
                    
            except urllib.error.HTTPError as e:
                error_msg = e.read().decode('utf-8')
                
                # Retry on 429 Too Many Requests, or 5xx Server Errors
                if e.code in [429, 500, 502, 503, 504] and attempt < max_retries - 1:
                    # Smart delay parsing for Google Gemini Rate Limits
                    dynamic_delay = retry_delay
                    if e.code == 429:
                        try:
                            error_data = json.loads(error_msg)
                            for detail in error_data.get('error', {}).get('details', []):
                                if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                                    delay_str = detail.get('retryDelay', '0s')
                                    delay_sec = int(float(re.search(r'\d+', delay_str).group()))
                                    if 0 < delay_sec < 60:
                                        dynamic_delay = delay_sec + 1
                        except Exception:
                            pass
                            
                    time.sleep(dynamic_delay)
                    retry_delay *= 2
                    continue
                    
                return {"error": f"API HTTP Error {e.code}: {e.reason}\n{error_msg}"}
            except Exception as e:
                # Catch timeout, URLError, connection reset, etc.
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return {"error": f"API Request Failed: {str(e)} (Đã thử lại {max_retries} lần nhưng vẫn thất bại)"}

    def _parse_json_response(self, text):
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        json_data = {}
        markdown_text = text.strip()
        
        if match:
            json_str = match.group(1)
            # Remove the JSON block from the markdown output to keep it clean
            markdown_text = text[:match.start()].strip() + "\n" + text[match.end():].strip()
            try:
                json_data = json.loads(json_str)
            except json.JSONDecodeError:
                pass
        else:
            # Fallback if AI returned raw JSON without code block
            try:
                if text.strip().startswith('{'):
                    json_data = json.loads(text.strip())
                    markdown_text = ""
            except json.JSONDecodeError:
                pass
                
        return {
            "markdown": markdown_text.strip() if markdown_text.strip() else "(Phân tích hoàn tất nhưng không có nội dung văn bản)",
            "data": json_data
        }
