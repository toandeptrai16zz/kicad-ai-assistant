# KiCad AI PCB Assistant

Một Plugin mã nguồn mở cho KiCad, tích hợp trí tuệ nhân tạo (Hỗ trợ Đa API: Google Gemini, DeepSeek, Groq, OpenAI) để trở thành "Siêu trợ lý" hỗ trợ bạn từ khâu thiết kế Nguyên lý (Schematic) đến Layout (PCB).

## Tính năng nổi bật

1. **Giao diện Chat thông minh & Đa API**: Tích hợp menu chọn nhà cung cấp AI (Google Gemini, DeepSeek, Groq, OpenAI). Tự động lưu cấu hình Key độc lập cho từng nền tảng, mọi thao tác phân tích nằm ngay trên màn hình thiết kế.
2. **Phân tích Schematic**: 
   - Đọc trực tiếp cấu trúc file `.kicad_sch` từ ngữ cảnh của board.
   - Rà soát danh sách linh kiện, cảnh báo thiếu điện trở kéo (Pull-up/Pull-down) cho các chuẩn giao tiếp.
3. **Phân tích PCB Layout**:
   - Thống kê toàn bộ đường mạch (Tracks, Vias), số lượng lớp (Layers), vùng đổ đồng (Zones).
   - Đề xuất số lớp phù hợp và cảnh báo nếu bạn đang thiết kế sai số lớp so với độ phức tạp của mạch.
   - Gợi ý kích thước đường dây (Track Width) tiêu chuẩn cho nguồn (VCC/GND) và tín hiệu (Signal).
   - **AI DRC**: Rà soát các IC thiếu tụ bypass (100nF) gần đó.
4. **Phân tích Mục đang chọn (Tương tác trực tiếp)**:
   - Click vào một linh kiện (Footprint) hoặc đường mạch (Track) trên màn hình. AI sẽ phân tích chính xác đối tượng đó (nó dùng làm gì, đường dây nối vào đã chuẩn chưa, kích thước dây có đủ tải không).
5. **Tự động áp dụng (Auto Fix)**:
   - Chỉ cần bấm nút `Tự động áp dụng`, plugin sẽ can thiệp vào `pcbnew` để phóng to các đường mạch nguồn bị nhỏ dựa trên chuẩn đã được AI tính toán.

## Cài đặt

Plugin này hoạt động tốt nhất với KiCad phiên bản 8.0 trở lên (hỗ trợ cả Nightly 10.0).

1. Clone repository này về máy của bạn:
   ```bash
   git clone https://github.com/toandeptrai16zz/kicad-ai-assistant.git
   ```
2. Sao chép (hoặc tạo symlink) thư mục `ai_pcb_assistant` vào thư mục plugin của KiCad:
   - **Linux**: `~/.local/share/kicad/10.0/scripting/plugins/` (Thay `10.0` bằng phiên bản bạn đang dùng)
   - **Windows**: `C:\Users\<Tên_User>\Documents\KiCad\10.0\scripting\plugins\`
3. Mở KiCad, bật PCB Editor, bạn sẽ thấy plugin "AI PCB Assistant" trên thanh công cụ (External Plugins).

## Hướng dẫn sử dụng

1. Mở plugin, chọn mạng AI bạn thích trong **Menu thả xuống** (Ví dụ: Google Gemini hoặc DeepSeek).
2. Nhập **API Key** tương ứng và bấm `Save Key`.
3. Bấm **Phân tích Schematic** để soi sơ đồ nguyên lý.
4. Bấm **Phân tích PCB** để soi tổng quan đường mạch.
5. **Phân tích chi tiết**: Click chuột vào một linh kiện/đường mạch trên KiCad, rồi bấm **Hỏi mục đang chọn**. AI sẽ đánh giá riêng biệt đối tượng đó.
6. (Tuỳ chọn) Bấm **Tự động áp dụng (Auto Fix)** để plugin tự động nới rộng các đường dây nguồn bị hẹp.

## Đóng góp (Contributing)

Vì đây là một dự án **mã nguồn mở**, mọi đóng góp từ cộng đồng (Pull Requests) đều được chào đón! Bạn có thể:
- Nâng cấp Prompts cho AI để phân tích sâu hơn (Ví dụ: tính toán trở kháng vi sai, phân tích nhiễu chéo Crosstalk).
- Mở rộng thêm tính năng Auto Fix (Ví dụ: Tự động di chuyển tụ bypass lại gần IC).

## Lộ trình tương lai (Future Roadmap)
- **Tích hợp Model Context Protocol (MCP Server)**: Biến plugin này thành một máy chủ MCP cục bộ. Thay vì sử dụng khung chat trong KiCad, bạn có thể mở các ứng dụng AI bên thứ ba (như **Claude Desktop**) và cho phép chúng truy cập, đọc hiểu bản vẽ KiCad của bạn theo thời gian thực (Real-time). Tầm nhìn xa hơn là cho phép Claude Desktop trực tiếp gửi lệnh vẽ mạch tự động vào KiCad thông qua giao thức MCP này.

## Giấy phép (License)
Dự án được phân phối dưới giấy phép MIT. Xem file `LICENSE` để biết thêm chi tiết.
