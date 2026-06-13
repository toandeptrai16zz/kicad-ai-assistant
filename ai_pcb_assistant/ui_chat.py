import wx
import pcbnew
import json
import threading
import os

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
        self.attached_pdf = None
        
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
        
        # User Input & Attachment Area
        input_area_vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Attachment Chip (Hidden by default)
        self.attachment_panel = wx.Panel(panel)
        self.attachment_panel.SetBackgroundColour(wx.Colour(60, 60, 60))
        self.attachment_panel.Hide()
        
        attach_hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_attachment = wx.StaticText(self.attachment_panel, label="📄 file.pdf")
        self.lbl_attachment.SetForegroundColour(wx.Colour(220, 220, 220))
        
        btn_remove_attach = wx.Button(self.attachment_panel, label="✕", size=(25, 25))
        btn_remove_attach.Bind(wx.EVT_BUTTON, self.on_remove_attachment)
        
        attach_hbox.Add(self.lbl_attachment, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.LEFT | wx.TOP | wx.BOTTOM, border=5)
        attach_hbox.Add(btn_remove_attach, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        
        self.attachment_panel.SetSizer(attach_hbox)
        input_area_vbox.Add(self.attachment_panel, flag=wx.BOTTOM, border=5)
        
        # Input row
        hbox_input = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_attach_pdf = wx.Button(panel, label="📎", size=(35, -1))
        self.btn_attach_pdf.Bind(wx.EVT_BUTTON, self.on_attach_pdf)
        hbox_input.Add(self.btn_attach_pdf, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        
        self.chat_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.chat_input.Bind(wx.EVT_TEXT_ENTER, self.on_send)
        hbox_input.Add(self.chat_input, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=5)
        
        btn_send = wx.Button(panel, label="Send")
        btn_send.Bind(wx.EVT_BUTTON, self.on_send)
        hbox_input.Add(btn_send, flag=wx.ALIGN_CENTER_VERTICAL)
        
        input_area_vbox.Add(hbox_input, flag=wx.EXPAND)
        
        vbox.Add(input_area_vbox, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        # Action Buttons
        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_hbox = hbox_actions
        
        btn_sch = wx.Button(panel, label="Phân tích Schematic")
        btn_sch.Bind(wx.EVT_BUTTON, lambda e: self.on_analyze_ai("schematic"))
        
        btn_pcb = wx.Button(panel, label="Phân tích PCB")
        btn_pcb.Bind(wx.EVT_BUTTON, lambda e: self.on_analyze_ai("pcb"))
        
        btn_selection = wx.Button(panel, label="Hỏi mục đang chọn")
        btn_selection.Bind(wx.EVT_BUTTON, lambda e: self.on_analyze_ai("selection"))
        
        btn_auto = wx.Button(panel, label="Tự động áp dụng (Auto Fix)")
        btn_auto.Bind(wx.EVT_BUTTON, self.on_auto_apply)
        
        btn_cluster = wx.Button(panel, label="Auto-Cluster")
        btn_cluster.Bind(wx.EVT_BUTTON, self.on_auto_cluster)
        btn_cluster.SetToolTip("Gom cụm linh kiện dựa theo Schematic")
        
        btn_hbox.Add(btn_sch, proportion=1, flag=wx.RIGHT, border=5)
        btn_hbox.Add(btn_pcb, proportion=1, flag=wx.RIGHT, border=5)
        btn_hbox.Add(btn_selection, proportion=1, flag=wx.RIGHT, border=5)
        btn_hbox.Add(btn_auto, proportion=1, flag=wx.RIGHT, border=5)
        btn_hbox.Add(btn_cluster, proportion=1)
        
        vbox.Add(hbox_actions, flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.EXPAND, border=10)

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
        
        if user_text.lower() == "phân tích schematic":
            self.on_analyze_ai("schematic")
        elif user_text.lower() == "phân tích pcb":
            self.on_analyze_ai("pcb")
        elif user_text.lower() == "hỏi mục đang chọn":
            self.on_analyze_ai("selection")
        elif user_text.lower() in ["auto", "tự động"]:
            self.on_auto_apply(None)
        else:
            self.on_analyze_ai("chat", custom_text=user_text)

    def on_analyze_ai(self, mode, custom_text=None):
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
        elif mode == "selection":
            self.append_log(f"\n--- Bắt đầu phân tích Mục đang chọn ---")
            json_data = self.extractor.to_json_selection()
            if "error" in json_data and "No items selected" in json_data:
                self.append_log(f"\nLỗi: Không có mục nào được chọn. Hãy click chuột chọn một linh kiện hoặc đường mạch trên màn hình KiCad rồi thử lại.")
                return
        elif mode == "chat":
            json_data = {"user_question": custom_text}
            selection_data = self.extractor.to_json_selection()
            if isinstance(selection_data, str):
                try:
                    parsed_sel = json.loads(selection_data)
                    if "error" not in parsed_sel:
                        json_data["context_selected_item"] = parsed_sel
                except Exception:
                    pass
            json_data = json.dumps(json_data, indent=2)
            
        if self.attached_pdf:
            self.append_log(f"Đã đính kèm Datasheet: {os.path.basename(self.attached_pdf)}")
            
        self.append_log(f"AI ({provider}): Đang phân tích... (Vui lòng đợi vài giây)")
        
        threading.Thread(target=self._run_ai_analysis, args=(json_data, mode, self.attached_pdf), daemon=True).start()

    def _run_ai_analysis(self, json_data, mode, pdf_path):
        if mode == "schematic":
            result = self.ai_client.analyze_schematic(json_data, pdf_path)
        elif mode == "pcb":
            result = self.ai_client.analyze_pcb(json_data, pdf_path)
        elif mode == "selection":
            result = self.ai_client.analyze_selection(json_data, pdf_path)
        elif mode == "chat":
            result = self.ai_client.analyze_chat(json_data, pdf_path)
            
        if "error" in result:
            self.append_log(f"\nLỗi từ AI: {result['error']}")
        else:
            self.append_log(f"\nAI: Phân tích {mode.upper()} hoàn tất.\n{'-'*40}\n{result.get('markdown', '')}")
            self.append_log(f"\n{'-'*40}\n--- Hoàn tất ---")
            
        # Lưu lại phần dữ liệu JSON cấu hình để phục vụ nút Auto Fix
        self.last_ai_result = result.get('data', {})

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

    def on_auto_cluster(self, event):
        self.append_log("\n--- Bắt đầu Tự động gom cụm linh kiện (Auto-Cluster) ---")
        msg = self.automator.auto_cluster_footprints()
        self.append_log(f"Hệ thống: {msg}")

    def on_remove_attachment(self, event=None):
        try:
            self.attached_pdf = None
            self.attachment_panel.Hide()
            self.attachment_panel.GetParent().Layout()
            self.Refresh()
            self.append_log("Đã gỡ bỏ file PDF đính kèm.")
        except Exception as e:
            self.append_log(f"Lỗi gỡ file: {str(e)}")

    def on_attach_pdf(self, event):
        try:
            with wx.FileDialog(self, "Chọn Datasheet (PDF/Ảnh)", wildcard="Tài liệu (*.pdf;*.png;*.jpg)|*.pdf;*.png;*.jpg",
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return

                self.attached_pdf = fileDialog.GetPath()
                filename = os.path.basename(self.attached_pdf)
                
                self.lbl_attachment.SetLabel(f"📄 {filename}")
                self.attachment_panel.Show()
                self.attachment_panel.Layout()
                self.attachment_panel.GetParent().Layout()
                self.Refresh()
                
                self.append_log(f"Đã đính kèm file: {filename}. AI sẽ đọc file này trong lần tương tác tiếp theo.")
                
                provider = self.ai_client.active_provider
                if PROVIDERS.get(provider, {}).get("type") != "gemini":
                    self.append_log("⚠️ Chú ý: Việc đọc tài liệu/hình ảnh đính kèm chỉ được hỗ trợ trên Gemini. Vui lòng đổi mạng ở ô phía trên.")
        except Exception as e:
            self.append_log(f"Lỗi hiển thị file: {str(e)}")
