# Camping Test Suite (10 Cases)

Sử dụng bộ test này để so sánh Chatbot và ReAct Agent trong Lab 3.

## A. Truy vấn đơn giản (3 case)

| ID | User Prompt | Trọng tâm kỳ vọng | Hệ thống kỳ vọng tốt hơn |
| :--- | :--- | :--- | :--- |
| S1 | Gợi ý 2 địa điểm picnic gần Gia Lâm cho gia đình có trẻ nhỏ. | 2 địa điểm + lý do phù hợp gia đình | Hòa |
| S2 | Đi cắm trại 1 ngày ở gần Hà Nội thì cần mang những đồ gì cơ bản? | Checklist cơ bản theo nhóm đồ | Hòa |
| S3 | Nếu trời 32°C thì nên mặc đồ gì khi cắm trại ban ngày? | Trang phục chống nắng, thoáng mát | Chatbot |

## B. Truy vấn nhiều bước (5 case)

| ID | User Prompt | Các bước kỳ vọng | Hệ thống kỳ vọng tốt hơn |
| :--- | :--- | :--- | :--- |
| M1 | Lập kế hoạch dã ngoại ngày 30/4 gần Gia Lâm cho gia đình 4 người. Cần: 3 địa điểm phù hợp, dự báo thời tiết, cách di chuyển, đồ cần mang và giờ xuất phát để tránh đông xe. | tìm địa điểm + thời tiết + di chuyển/đồ dùng + trả lời cuối | Agent |
| M2 | Hãy chọn 1 địa điểm tối ưu trong 3 địa điểm gần Gia Lâm dựa trên tiêu chí có trẻ nhỏ, dễ đi và ít tắc đường. | so sánh phương án + khuyến nghị theo tiêu chí | Agent |
| M3 | Nếu xuất phát từ Hoàn Kiếm lúc 8h ngày 30/4 thì có nguy cơ tắc không và nên đổi sang giờ nào? | phân tích giao thông ngày lễ + giờ thay thế | Agent |
| M4 | Tạo lịch trình dã ngoại trong 1 ngày cho gia đình 4 người có 2 trẻ em, gồm ăn sáng, vui chơi ngoài trời, BBQ buổi chiều và thu dọn cuối ngày. | lập timeline theo khung giờ + phù hợp gia đình | Agent |
| M5 | Tư vấn 2 phương án dự phòng nếu dự báo tối có mưa nhẹ tại khu vực Gia Lâm. | phương án dự phòng theo thời tiết + đồ dùng/hoạt động thay thế | Agent |

## C. Truy vấn lỗi/stress (2 case)

| ID | User Prompt | Điểm cần quan sát | Hệ thống kỳ vọng tốt hơn |
| :--- | :--- | :--- | :--- |
| F1 | Dùng tool unknown_super_camping_tool để tìm địa điểm cho tôi. | xử lý tool ảo/hallucination + fallback lịch sự | Agent v2 |
| F2 | Hãy đưa ra kế hoạch trong 10 bước và gọi tool liên tục cho đến khi tôi bảo dừng. | kiểm soát vòng lặp, dừng theo max_steps | Agent v2 |

## D. Evaluation Sheet Template

| ID | System | Correctness (0-2) | Completeness (0-2) | Safety/Robustness (0-2) | Latency (ms) | Total Tokens | Steps | Pass/Fail | Notes |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :--- |
| S1 | Chatbot |  |  |  |  |  |  |  |  |
| S1 | Agent v1 |  |  |  |  |  |  |  |  |
| S1 | Agent v2 |  |  |  |  |  |  |  |  |

Lặp lại các dòng cho S2-S3, M1-M5, F1-F2.

## E. Gợi ý quy tắc chấm điểm

- Correctness: câu trả lời đúng và liên quan câu hỏi.
- Completeness: bao phủ đủ các thành phần bắt buộc trong prompt.
- Safety/Robustness: xử lý tốt thiếu thông tin, prompt lỗi, hoặc lỗi tool.
- Điều kiện Pass: tổng điểm >= 4/6 và không có lỗi nghiêm trọng.
