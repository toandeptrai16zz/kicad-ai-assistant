import wx
import pcbnew
import json
import threading

from .extractor import BoardExtractor
from .ai_client import AIClient, PROVIDERS
from .automation import BoardAutomator

class AIChatDialog(wx.Dialog):
    def __init__(self, parent, board):
        super().__init__(parent, title="AI PCB Assistant (Multi-API)", size=(700, 750),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.board = board
        self.ai_client = AIClient()
        self.automator = BoardAutomator(self.board)
        self.extractor = BoardExtractor(self.board)
        self.last_ai_result = None
        self.last_analysis_mode = None
        
        self.init_ui()
        self.CenterOnParent()

    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Config row for Provider and API Key
        hbox_config = wx.BoxSizer(wx.HORIZONTAL)
        
        hbox_config.Add(wx.StaticText(panel, label="AI Provider:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        
        self.provider_choice = wx.Choice(panel, choices=list(PROVIDERS.keys()))
        active_idx = list(PROVIDERS.keys()).index(self.ai_client.active_provider) if self.ai_client.active_provider in PROVIDERS else 0
        self.provider_choice.SetSelection(active_idx)
        self.provider_choice.Bind(wx.EVT_CHOICE, self.on_provider_change)
        hbox_config.Add(self.provider_choice, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=15)
        
        hbox_config.Add(wx.StaticText(panel, label="API Key:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.api_key_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._load_current_key_to_ui()
            
        btn_save_key = wx.Button(panel, label="Save Key")
        btn_save_key.Bind(wx.EVT_BUTTON, self.on_save_key)
        
        hbox_config.Add(self.api_key_input, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=5)
        hbox_config.Add(btn_save_key, flag=wx.ALIGN_CENTER_VERTICAL)
        vbox.Add(hbox_config, flag=wx.EXPAND | wx.ALL, border=10)

        # Chat Log
        self.chat_log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        vbox.Add(self.chat_log, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        # User Input
        hbox_input = wx.BoxSizer(wx.HORIZONTAL)
        self.chat_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.chat_input.Bind(wx.EVT_TEXT_ENTER, self.on_send)
        hbox_input.Add(self.chat_input, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=5)
        
        btn_send = wx.Button(panel, label="Send")
        btn_send.Bind(wx.EVT_BUTTON, self.on_send)
        hbox_input.Add(btn_send, flag=wx.ALIGN_CENTER_VERTICAL)
        
        vbox.Add(hbox_input, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        # Action Buttons
        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_analyze_sch = wx.Button(panel, label="Phân tích Schematic")
        btn_analyze_sch.Bind(wx.EVT_BUTTON, lambda e: self.on_analyze_ai("schematic"))
        hbox_actions.Add(btn_analyze_sch, flag=wx.RIGHT, border=5)

        btn_analyze_pcb = wx.Button(panel, label="Phân tích PCB")
        btn_analyze_pcb.Bind(wx.EVT_BUTTON, lambda e: self.on_analyze_ai("pcb"))
        hbox_actions.Add(btn_analyze_pcb, flag=wx.RIGHT, border=5)
        
        btn_analyze_sel = wx.Button(panel, label="Hỏi mục đang chọn")
        btn_analyze_sel.Bind(wx.EVT_BUTTON, lambda e: self.on_analyze_ai("selection"))
        hbox_actions.Add(btn_analyze_sel, flag=wx.RIGHT, border=5)
        
        btn_auto_apply = wx.Button(panel, label="Tự động áp dụng (Auto Fix)")
        btn_auto_apply.Bind(wx.EVT_BUTTON, self.on_auto_apply)
        hbox_actions.Add(btn_auto_apply, flag=wx.RIGHT, border=5)
        
        vbox.Add(hbox_actions, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)
        
        self.append_log(f"AI: Xin chào! Hệ thống đang sử dụng {self.ai_client.active_provider}.")
        self.append_log("AI: Bạn có thể chọn AI Provider khác ở menu thả xuống phía trên.")

    def _load_current_key_to_ui(self):
        current_provider = self.provider_choice.GetString(self.provider_choice.GetSelection())
        key = self.ai_client.get_api_key(current_provider)
        self.api_key_input.SetValue(key)

    def on_provider_change(self, event):
        provider = self.provider_choice.GetString(self.provider_choice.GetSelection())
        self.ai_client.set_active_provider(provider)
        self._load_current_key_to_ui()
        self.append_log(f"Hệ thống: Đã chuyển sang sử dụng {provider}.")

    def append_log(self, text):
        wx.CallAfter(self.chat_log.AppendText, text + "\n")

    def on_save_key(self, event):
        provider = self.provider_choice.GetString(self.provider_choice.GetSelection())
        key = self.api_key_input.GetValue().strip()
        if key:
            self.ai_client.save_api_key(provider, key)
            self.append_log(f"Hệ thống: Đã lưu API Key cho {provider}.")
            
    def on_send(self, event):
        user_text = self.chat_input.GetValue().strip()
        if not user_text:
            return
            
        self.append_log(f"\nBạn: {user_text}")
        self.chat_input.Clear()
        
        if "schematic" in user_text.lower():
            self.on_analyze_ai("schematic")
        elif "pcb" in user_text.lower():
            self.on_analyze_ai("pcb")
        elif "chọn" in user_text.lower() or "selection" in user_text.lower():
            self.on_analyze_ai("selection")
        elif "auto" in user_text.lower() or "tự động" in user_text.lower():
            self.on_auto_apply(None)
        else:
            self.append_log("AI: Vui lòng bấm các nút phân tích, hoặc gõ 'phân tích pcb', 'phân tích schematic', 'hỏi mục đang chọn', 'auto'.")

    def on_analyze_ai(self, mode):
        if not self.board:
            self.append_log("\nLỗi: Không tìm thấy Board.")
            return
            
        provider = self.provider_choice.GetString(self.provider_choice.GetSelection())
        if not self.ai_client.get_api_key(provider):
            self.append_log(f"\nLỗi: Vui lòng nhập API Key cho {provider} trước.")
            return

        self.last_analysis_mode = mode
        
        if mode == "schematic":
            self.append_log(f"\n--- Bắt đầu trích xuất dữ liệu Schematic ---")
            json_data = self.extractor.to_json_schematic()
        elif mode == "pcb":
            self.append_log(f"\n--- Bắt đầu trích xuất dữ liệu PCB ---")
            json_data = self.extractor.to_json_pcb()
        else:
            self.append_log(f"\n--- Bắt đầu phân tích Mục đang chọn ---")
            json_data = self.extractor.to_json_selection()
            if "error" in json_data and "No items selected" in json_data:
                self.append_log(f"\nLỗi: Không có mục nào được chọn. Hãy click chuột chọn một linh kiện hoặc đường mạch trên màn hình KiCad rồi thử lại.")
                return
            
        self.append_log(f"AI ({provider}): Đang phân tích... (Vui lòng đợi vài giây)")
        
        threading.Thread(target=self._run_ai_analysis, args=(json_data, mode), daemon=True).start()

    def _run_ai_analysis(self, json_data, mode):
        if mode == "schematic":
            result = self.ai_client.analyze_schematic(json_data)
        elif mode == "pcb":
            result = self.ai_client.analyze_pcb(json_data)
        else:
            result = self.ai_client.analyze_selection(json_data)
            
        if "error" in result:
            self.append_log(f"\nLỗi từ AI: {result['error']}")
            return
            
        self.last_ai_result = result
        self.append_log(f"\nAI: Phân tích {mode.upper()} hoàn tất. Kết quả:")
        self.append_log(json.dumps(result, indent=2, ensure_ascii=False))
        
        if mode == "pcb":
            self.append_log("\nAI: Bạn có thể tự sửa lỗi, hoặc bấm 'Tự động áp dụng' để tôi sửa mạch thay bạn.")
        
        self.append_log("\n--- Hoàn tất ---")

    def on_auto_apply(self, event):
        if not self.last_ai_result or self.last_analysis_mode != "pcb":
            self.append_log("\nLỗi: Tính năng tự động (Auto Fix) hiện tại chỉ áp dụng cho PCB. Vui lòng phân tích PCB trước.")
            return
            
        result = self.last_ai_result
        self.append_log("\n--- Bắt đầu Tự động hóa KiCad (Giai đoạn 4) ---")
        
        # 1. Track width
        vcc_width = result.get('track_width_vcc_mm')
        signal_width = result.get('track_width_signal_mm')
        if vcc_width and signal_width:
            msg = self.automator.apply_track_width_suggestions(vcc_width, signal_width)
            self.append_log(f"Hệ thống: {msg}")
            
        # 2. Layer setup
        rec_layers = result.get('recommended_layers')
        if rec_layers:
            msg = self.automator.check_layer_setup(rec_layers)
            self.append_log(f"Hệ thống: {msg}")
            
        # 3. AI DRC
        missing_caps = result.get('missing_bypass_caps')
        if missing_caps:
            msg = self.automator.run_ai_drc(missing_caps)
            self.append_log(f"Hệ thống DRC: {msg}")
            
        wx.CallAfter(pcbnew.Refresh)
        self.append_log("\n--- Đã áp dụng tự động thành công ---")
