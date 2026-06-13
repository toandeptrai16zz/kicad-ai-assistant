import pcbnew
import json
import os
import re

class BoardExtractor:
    def __init__(self, board):
        self.board = board
        
    def get_components(self):
        """Extract all footprints (components) on the board."""
        components = []
        if not self.board:
            return components
            
        for footprint in self.board.GetFootprints():
            ref = footprint.GetReference()
            value = footprint.GetValue()
            try:
                pkg = footprint.GetFPID().AsString()
            except Exception:
                pkg = "Unknown"
                
            pos = footprint.GetPosition()
            x_mm = pos.x / 1e6
            y_mm = pos.y / 1e6
            layer = footprint.GetLayerName()
            
            # Extract unique nets connected to this component
            nets = set()
            for pad in footprint.Pads():
                net_name = pad.GetNetname()
                if net_name:
                    nets.add(net_name)
            
            components.append({
                "reference": ref,
                "value": value,
                "package": pkg,
                "layer": layer,
                "nets": list(nets)
            })
            
        return components

    def get_board_setup(self):
        """Extract board configuration like layers and design rules."""
        setup_info = {}
        if not self.board:
            return setup_info
            
        setup_info["copper_layers"] = self.board.GetCopperLayerCount()
        design_settings = self.board.GetDesignSettings()
        try:
            default_track_width_mm = design_settings.GetCustomTrackWidths()[0] / 1e6 if design_settings.GetCustomTrackWidths() else 0.25
            setup_info["default_track_width_mm"] = round(default_track_width_mm, 3)
        except Exception:
            setup_info["default_track_width_mm"] = "Unknown"
            
        return setup_info

    def get_tracks_summary(self):
        """Summarize track lengths and widths per Net."""
        if not self.board: return {}
        
        net_summary = {}
        for track in self.board.GetTracks():
            net_name = track.GetNetname()
            if not net_name: continue
            
            if net_name not in net_summary:
                net_summary[net_name] = {
                    "track_count": 0,
                    "via_count": 0,
                    "max_width_mm": 0,
                    "min_width_mm": 999.0
                }
            
            if hasattr(track, 'Type') and track.Type() == pcbnew.PCB_VIA_T:
                net_summary[net_name]["via_count"] += 1
            else:
                net_summary[net_name]["track_count"] += 1
                width_mm = track.GetWidth() / 1e6
                if width_mm > net_summary[net_name]["max_width_mm"]:
                    net_summary[net_name]["max_width_mm"] = width_mm
                if width_mm < net_summary[net_name]["min_width_mm"]:
                    net_summary[net_name]["min_width_mm"] = width_mm
                    
        for net in net_summary.values():
            if net["min_width_mm"] == 999.0:
                net["min_width_mm"] = 0.0
            net["max_width_mm"] = round(net["max_width_mm"], 3)
            net["min_width_mm"] = round(net["min_width_mm"], 3)
            
        return net_summary

    def get_zones_summary(self):
        """Summarize copper pours."""
        if not self.board: return []
        zones = []
        try:
            if hasattr(self.board, 'Zones'):
                zone_list = self.board.Zones()
            else:
                zone_list = [self.board.GetArea(i) for i in range(self.board.GetAreaCount())]
                
            for zone in zone_list:
                zones.append({
                    "net": zone.GetNetname(),
                    "layer": zone.GetLayerName()
                })
        except Exception:
            pass
        return zones

    def parse_schematic(self):
        """Extract components directly from schematic file."""
        if not self.board: return {}
        
        pcb_path = self.board.GetFileName()
        if not pcb_path: return {"error": "Board is not saved."}
        
        sch_path = pcb_path.replace(".kicad_pcb", ".kicad_sch")
        if not os.path.exists(sch_path):
            return {"error": f"Schematic file not found at {sch_path}"}
            
        sch_summary = {
            "symbol_count": 0,
            "symbols": []
        }
        
        try:
            with open(sch_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            symbol_blocks = re.findall(r'\(symbol\s(.*?)(?=\(symbol\s|\Z)', content, re.DOTALL)
            sch_summary["symbol_count"] = len(symbol_blocks)
            
            for block in symbol_blocks:
                ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
                val_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
                if ref_match:
                    sch_summary["symbols"].append({
                        "reference": ref_match.group(1),
                        "value": val_match.group(1) if val_match else ""
                    })
        except Exception as e:
            return {"error": str(e)}
            
        return sch_summary

    def to_json_schematic(self):
        """Return only the schematic data as JSON."""
        return json.dumps({"schematic_summary": self.parse_schematic()}, indent=2)

    def to_json_pcb(self):
        """Return only the PCB data as JSON."""
        data = {
            "board_setup": self.get_board_setup(),
            "components_on_pcb": self.get_components(),
            "tracks_summary": self.get_tracks_summary(),
            "zones_summary": self.get_zones_summary()
        }
        return json.dumps(data, indent=2)

    def to_json_selection(self):
        """Extract the current user selection and provide targeted context."""
        if not self.board: return json.dumps({"error": "No board found."})
        
        try:
            selection = pcbnew.GetCurrentSelection()
        except Exception as e:
            return json.dumps({"error": f"Failed to get selection: {str(e)}"})
            
        if not selection:
            return json.dumps({"error": "No items selected. Please select a footprint or a track on the board first."})
            
        selected_data = {"items": []}
        
        for item in selection:
            if isinstance(item, pcbnew.FOOTPRINT):
                # Component selected
                ref = item.GetReference()
                val = item.GetValue()
                pads_info = []
                for pad in item.Pads():
                    net_name = pad.GetNetname()
                    pad_num = pad.GetPadName()
                    if net_name:
                        pads_info.append({"pad": pad_num, "net": net_name})
                        
                selected_data["items"].append({
                    "type": "Component",
                    "reference": ref,
                    "value": val,
                    "connected_nets": pads_info
                })
                
            elif isinstance(item, pcbnew.PCB_TRACK):
                # Track selected
                net_name = item.GetNetname()
                width_mm = item.GetWidth() / 1e6
                length_mm = item.GetLength() / 1e6
                layer = item.GetLayerName()
                
                selected_data["items"].append({
                    "type": "Track",
                    "net": net_name,
                    "width_mm": round(width_mm, 3),
                    "length_mm": round(length_mm, 3),
                    "layer": layer
                })
            else:
                selected_data["items"].append({
                    "type": "Other",
                    "info": str(type(item))
                })
                
        # Include a brief overview of the board to give the AI some context
        selected_data["board_context"] = self.get_board_setup()
        
        return json.dumps(selected_data, indent=2)

