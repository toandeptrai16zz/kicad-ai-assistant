import pcbnew
import math

class BoardAutomator:
    def __init__(self, board):
        self.board = board

    def apply_track_width_suggestions(self, vcc_width_mm, signal_width_mm):
        """Update NetClasses for VCC/GND and Signal nets."""
        if not self.board:
            return "No board found."
            
        # Convert mm to internal units (nm)
        vcc_iu = int(vcc_width_mm * 1e6)
        signal_iu = int(signal_width_mm * 1e6)
        
        design_settings = self.board.GetDesignSettings()
        netclasses = design_settings.GetNetClasses()
        
        updated_nets = []
        
        # Iterate over all nets in the board
        nets = self.board.GetNetsByName()
        for net_name, net_info in nets.items():
            if not net_name: # Skip empty net
                continue
                
            net_name_upper = net_name.upper()
            if "VCC" in net_name_upper or "GND" in net_name_upper or "+3V3" in net_name_upper or "+5V" in net_name_upper:
                # This is a power net, we assign it to a "Power" netclass if we can, or just set tracks
                # For simplicity, let's iterate through tracks of this net and update them
                # A proper way is updating the Netclass, but changing existing tracks is more visible.
                updated_nets.append(net_name)
        
        # Update existing tracks directly as a POC
        track_updates = 0
        for track in self.board.GetTracks():
            net_name = track.GetNetname()
            net_name_upper = net_name.upper()
            
            if "VCC" in net_name_upper or "GND" in net_name_upper or "+5V" in net_name_upper or "+3V3" in net_name_upper:
                if track.GetWidth() < vcc_iu:
                    track.SetWidth(vcc_iu)
                    track_updates += 1
            else:
                # Signal net
                if track.GetWidth() < signal_iu:
                    # In a real tool, we might not want to blindly change all signal tracks,
                    # but for this POC we'll apply the AI suggestion if they are smaller.
                    pass 

        return f"Đã cập nhật độ rộng dây cho {track_updates} segments nguồn (VCC/GND) lên {vcc_width_mm}mm."

    def check_layer_setup(self, recommended_layers):
        """Check if current copper layers match AI recommendations."""
        if not self.board:
            return ""
            
        current_layers = self.board.GetCopperLayerCount()
        if current_layers < recommended_layers:
            return f"CẢNH BÁO: AI đề xuất dùng {recommended_layers} lớp, nhưng mạch hiện tại chỉ có {current_layers} lớp. Vui lòng xem xét tăng số lớp!"
        elif current_layers > recommended_layers:
            return f"Lưu ý: Mạch có {current_layers} lớp, AI cho rằng {recommended_layers} lớp là đủ. Có thể tối ưu chi phí."
        return "Số lớp thiết lập phù hợp với gợi ý của AI."

    def run_ai_drc(self, missing_bypass_caps):
        """Highlight components missing bypass caps."""
        if not self.board or not missing_bypass_caps:
            return "Không có lỗi DRC từ AI."
            
        # Draw a shape or marker over the components, or just return a warning string
        warnings = []
        for ref in missing_bypass_caps:
            footprint = self.board.FindFootprintByReference(ref)
            if footprint:
                warnings.append(f"IC {ref} thiếu tụ bypass gần đó. Vui lòng thêm tụ 100nF.")
                # We could add an error marker or change color
                # footprint.ClearSelected() 
                # pcbnew.Refresh()
                
        if warnings:
            return "\n".join(warnings)
        return "Kiểm tra DRC AI hoàn tất, không tìm thấy linh kiện lỗi trên mạch."
