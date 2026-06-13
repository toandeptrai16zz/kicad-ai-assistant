import os
import json
import urllib.request
import urllib.error
import re

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

PROVIDERS = {
    "Google Gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "type": "gemini",
        "model": "gemini-1.5-flash"
    },
    "DeepSeek": {
        "url": "https://api.deepseek.com/chat/completions",
        "type": "openai",
        "model": "deepseek-chat"
    },
    "Groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "type": "openai",
        "model": "llama3-70b-8192"
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
Bạn là một kỹ sư thiết kế nguyên lý (Schematic) giàu kinh nghiệm.
Dưới đây là dữ liệu trích xuất từ sơ đồ nguyên lý KiCad (.kicad_sch).
Nhiệm vụ của bạn:
1. Đọc danh sách linh kiện.
2. Phát hiện các bất thường cơ bản (ví dụ: thiếu điện trở kéo pull-up cho các chân giao tiếp như I2C nếu có thể suy luận, hoặc các giá trị tụ/trở không hợp lý nếu có).
3. Cung cấp một nhận xét tổng quan ngắn gọn về độ phức tạp và chức năng dự kiến của mạch.

HÃY TRẢ VỀ DUY NHẤT MỘT KHỐI JSON (KHÔNG CÓ VĂN BẢN NÀO KHÁC BÊN NGOÀI).
{
  "schematic_warnings": ["Cảnh báo 1", "Cảnh báo 2"],
  "analysis_summary": "Nhận xét tổng quan mạch"
}
"""

        self.pcb_prompt = """
Bạn là một chuyên gia Layout PCB với nhiều năm kinh nghiệm. 
Dưới đây là dữ liệu trích xuất từ dự án KiCad, bao gồm:
- Thông tin thiết lập (số lớp đồng, độ rộng dây).
- Danh sách footprint đang nằm trên PCB.
- Thống kê đường dây (Tracks/Vias) theo từng Net.
- Vùng đổ đồng (Zones) và Net của chúng.

Nhiệm vụ của bạn:
1. Đánh giá số lớp hiện tại và đề xuất số lớp tối ưu (`recommended_layers`).
2. Đánh giá độ rộng đường mạch hiện tại của các Net nguồn (VCC/GND/5V/3V3...). Đề xuất độ rộng tối thiểu an toàn (`track_width_vcc_mm` và `track_width_signal_mm`).
3. Kiểm tra xem các Net nguồn/GND đã được đổ đồng (Zones) chưa.
4. Tìm các linh kiện (đặc biệt là IC) thiếu tụ bypass (decoupling capacitors 100nF) ở gần đó và liệt kê tham chiếu vào mảng `missing_bypass_caps`.

HÃY TRẢ VỀ DUY NHẤT MỘT KHỐI JSON (KHÔNG CÓ VĂN BẢN NÀO KHÁC BÊN NGOÀI).
{
  "recommended_layers": 4,
  "track_width_vcc_mm": 0.5,
  "track_width_signal_mm": 0.25,
  "missing_bypass_caps": ["U1", "U3"],
  "analysis_summary": "Nhận xét về layout và đổ đồng."
}
"""

        self.interactive_prompt = """
Bạn là một chuyên gia thiết kế phần cứng điện tử (Mentor).
Người dùng vừa chọn (highlight) một hoặc vài đối tượng cụ thể trên bản vẽ PCB.
Dưới đây là dữ liệu về các đối tượng được chọn (Linh kiện hoặc Đường mạch) cùng với thông tin tổng quan của Board.

Nhiệm vụ của bạn:
1. Xác định rõ người dùng đang chọn cái gì (Ví dụ: Điện trở R1, IC U2, hoặc Đường mạch VCC).
2. Nếu là Linh kiện: Giải thích chi tiết chức năng của linh kiện đó trong thực tế. Đánh giá xem các đường Net nối vào chân của nó đã hợp lý chưa (dựa trên tên Net như GND, VCC, SCL, SDA).
3. Nếu là Đường mạch (Track): Đánh giá xem độ rộng (width) của đường mạch đó có phù hợp với tên Net không (VD: Net nguồn thì phải to, Net tín hiệu thì có thể nhỏ).
4. Đưa ra lời khuyên hoặc cảnh báo nếu thấy điểm bất hợp lý.

HÃY TRẢ VỀ DUY NHẤT MỘT KHỐI JSON (KHÔNG CÓ VĂN BẢN NÀO KHÁC BÊN NGOÀI).
{
  "selection_type": "Component / Track / Mixed",
  "explanation": "Giải thích chi tiết về đối tượng được chọn...",
  "evaluation": "Đánh giá đúng/sai hoặc hợp lý/bất hợp lý...",
  "recommendation": "Lời khuyên từ chuyên gia..."
}
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

    def analyze_schematic(self, json_data):
        return self._send_request(self.schematic_prompt, json_data)
        
    def analyze_pcb(self, json_data):
        return self._send_request(self.pcb_prompt, json_data)
        
    def analyze_selection(self, json_data):
        return self._send_request(self.interactive_prompt, json_data)

    def _send_request(self, system_prompt, data):
        provider_info = PROVIDERS.get(self.active_provider)
        if not provider_info:
            return {"error": "Invalid AI Provider selected."}
            
        api_key = self.get_api_key(self.active_provider)
        if not api_key:
            return {"error": f"API Key for {self.active_provider} is not set. Please configure it."}
            
        if provider_info["type"] == "gemini":
            return self._send_gemini(api_key, provider_info, system_prompt, data)
        else:
            return self._send_openai_compatible(api_key, provider_info, system_prompt, data)

    def _send_gemini(self, api_key, provider_info, system_prompt, data):
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\nDữ liệu:\n{data}"}]}],
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
        
        if extra_headers:
            for k, v in extra_headers.items():
                req.add_header(k, v)
                
        try:
            with urllib.request.urlopen(req) as response:
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
            return {"error": f"API HTTP Error {e.code}: {e.reason}\n{error_msg}"}
        except urllib.error.URLError as e:
            return {"error": f"API Network Error: {e.reason}"}
        except Exception as e:
            return {"error": f"Parse Error: {str(e)}"}

    def _parse_json_response(self, text):
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = text.strip()
            
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON from AI response: {str(e)}\nRaw Response: {text}"}
