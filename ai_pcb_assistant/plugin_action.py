import pcbnew
import os
import wx
from .ui_chat import AIChatDialog

class AiAssistantPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "AI PCB Assistant"
        self.category = "Utility"
        self.description = "AI-powered assistant for PCB design and layout."
        self.show_toolbar_button = True
        # Set an icon for the toolbar (optional, standard png)
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.icon_file_name = icon_path

    def Run(self):
        # The entry function of the plugin that is executed on user action
        board = pcbnew.GetBoard()
        
        # Get the top level window for KiCad
        pcb_window = None
        for window in wx.GetTopLevelWindows():
            if window.GetTitle().lower().startswith('pcbnew'):
                pcb_window = window
                break
                
        # Initialize and show the UI
        dialog = AIChatDialog(pcb_window, board)
        dialog.Show()
