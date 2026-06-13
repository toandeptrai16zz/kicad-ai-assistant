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

    def auto_cluster_footprints(self):
        """Auto-place footprints on PCB based on their layout in Schematic (Clustering)."""
        if not self.board:
            return "Không tìm thấy board."
            
        pcb_path = self.board.GetFileName()
        if not pcb_path: 
            return "Lỗi: Mạch chưa được lưu (Board is not saved)."
            
        sch_path = pcb_path.replace(".kicad_pcb", ".kicad_sch")
        import os, re
        if not os.path.exists(sch_path):
            return f"Lỗi: Không tìm thấy file Schematic tại {sch_path}"
            
        try:
            with open(sch_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            symbol_blocks = re.findall(r'\(symbol\s(.*?)(?=\(symbol\s|\Z)', content, re.DOTALL)
            mapping = {}
            for block in symbol_blocks:
                if '(uuid' not in block:
                    continue
                ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
                if not ref_match:
                    continue
                ref = ref_match.group(1)
                
                at_match = re.search(r'\(at\s+([0-9.-]+)\s+([0-9.-]+)', block)
                if at_match:
                    x = float(at_match.group(1))
                    y = float(at_match.group(2))
                    mapping[ref] = (x, y)
                    
            if not mapping:
                return "Không trích xuất được tọa độ từ Schematic."
                
            moved_count = 0
            SCALE = 0.5
            OFFSET_X = -50.0 
            OFFSET_Y = -50.0
            
            for footprint in self.board.GetFootprints():
                ref = footprint.GetReference()
                if ref in mapping:
                    sch_x, sch_y = mapping[ref]
                    pcb_x_mm = sch_x * SCALE + OFFSET_X
                    pcb_y_mm = sch_y * SCALE + OFFSET_Y
                    
                    pos_x = int(pcb_x_mm * 1000000)
                    pos_y = int(pcb_y_mm * 1000000)
                    
                    footprint.SetPosition(pcbnew.wxPoint(pos_x, pos_y))
                    moved_count += 1
                    
            pcbnew.Refresh()
            return f"Thành công! Đã tự động gom cụm {moved_count} linh kiện theo bản vẽ Schematic."
            
        except Exception as e:
            return f"Lỗi Auto-Cluster: {str(e)}"
