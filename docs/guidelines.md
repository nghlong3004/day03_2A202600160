# Tài liệu Tham khảo: Trợ lý cắm trại (ReAct Agent)

## 1. Tổng quan Dự án

Dự án là một Trợ lý AI (Agent) tư vấn và lên kế hoạch cắm trại. Không giống như chatbot thông thường, Agent được trang bị các Tools để tìm kiếm thông tin theo thời gian thực thay vì bịa ra câu trả lời.

Hệ thống hoạt động theo vòng lặp **ReAct (Reasoning + Acting)**:
1. **Thought:** Phân tích câu hỏi của user để quyết định xem cần dùng công cụ nào.
2. **Action:** Gọi một công cụ cụ thể với tham số phù hợp.
3. **Observation:** Nhận kết quả từ công cụ.
4. Lặp lại vòng lặp nếu cần thêm thông tin, hoặc tổng hợp thành **Final Answer**.

**Kịch bản Camping Bot:**
Khi nhận yêu cầu lên kế hoạch (ví dụ: *"Tôi muốn 30/4 đi cắm trại quanh Hà Nội..."*), Agent sẽ tự động đi theo luồng:
- Gọi công cụ `search_camping_sites` để tìm địa điểm thực tế.
- Gọi công cụ `get_weather_forecast` để lấy dự báo thời tiết.
- Gọi công cụ `get_travel_and_gear_recommendations` để lên lịch trình di chuyển và danh sách đồ đạc.

## 2. Kiến trúc mã nguồn & Cách viết Tool

```text
src/
├── core/
│   ├── llm_provider.py       # Interface gốc định nghĩa cấu trúc chuẩn cho mọi LLM
│   ├── provider.py           # Provider có sẵn (cũng dùng cho Grok, OpenRouter...)
│   └── gemini_provider.py    # Provider rẽ nhánh tương thích riêng SDK của Google
├── tools/                    # Nơi định nghĩa các công cụ phục vụ luồng
│   └── location_tools.py
│   └── weather_tools.py          
├── agent/
│   ├── agent.py              # Lõi điều khiển vòng lặp ReAct (Thought-Action-Observation)
│   └── camping_agent.py      # Module chứa system prompt hướng dẫn Agent
```

Theo cấu trúc này, công cụ (Tool) đóng vai trò trung tâm. Mỗi công cụ là một hàm Python xử lý logic, đi kèm phần JSON mô tả để hướng dẫn AI khi nào thì nên dùng.

**Lưu ý cực kỳ quan trọng:** Phần mô tả (description) phải rất cụ thể để LLM không phải "đoán mò". Mọi người tham khảo ví dụ dưới đây khi viết mô tả:

** Tệ (Agent sẽ đoán mò)**
* `name`: do_stuff
* `description`: "Hàm tìm kiếm"
* `args`: input (any)
* `return`: không ghi
* `error`: không ghi
*(Hậu quả: Agent không biết khi nào gọi, truyền gì, nhận gì. Rất dễ bị kẹt vòng lặp)*

** Tốt (Agent hiểu rõ)**
* `name`: search_flights
* `description`: "Search available flights between two airports on a specific date, filtered by max price in VND"
* `args`: origin (str, IATA), destination (str, IATA), date (str, YYYY-MM-DD), max_price (int, VND)
* `return`: {flights: [{airline, time, price}]}
* `error`: empty list if none; TimeoutError after 5s

Ví dụ nếu bạn viết tool lấy thời tiết trong `camping_tools.py`, hãy viết như sau:
```python
def get_weather(query: str) -> str:
    return "Kết quả chạy của tool"

# Thêm định nghĩa vào registry của file. Áp dụng quy tắc "Tốt" vào mô tả!
{
    "name": "get_weather",
    "description": "Lấy dự báo thời tiết cho một địa điểm cụ thể. Cần truyền vào tham số location (tên thành phố). Trả về: Chuỗi chứa Nhiệt độ và khả năng mưa.",
    "function": get_weather
}
```

## 3. Tích hợp LLM (API Providers)

Code hiện tại dùng chuẩn SDK của OpenAI, nên mọi người hoàn toàn có thể tự dùng các nền tảng AI khác theo tài khoản tùy thích để chạy code, chỉ cần đổi `base_url` và `api_key` tại module `src/core/deepseek_provider.py`.

Một số nền tảng phổ biến có hỗ trợ chuẩn OpenAI API (chỉ cần đổi URL và Key, không cần đổi thư viện):
* **DeepSeek:** Dùng tài khoản platform.deepseek.com (`https://api.deepseek.com`, model: `deepseek-chat`). Mình đang dùng cái này.
* **Google Gemini:** Nay đã hỗ trợ gọi qua chuẩn OpenAI. Cấu hình Base URL: `https://generativelanguage.googleapis.com/v1beta/openai/` (model gợi ý: `gemini-2.5-flash` hoặc `gemini-1.5-pro`). Lấy key miễn phí tại Google AI Studio.
* **xAI (Grok):** Tương thích hoàn toàn OpenAI SDK. Cấu hình Base URL: `https://api.x.ai/v1` (model gợi ý: `grok-2`). Đăng ký tại x.ai.
* **OpenRouter:** Cổng trung chuyển cung cấp rất nhiều model miễn phí (như Meta Llama 3 8B...). Cấu hình `https://openrouter.ai/api/v1`.
* **GitHub Models:** Nếu bạn có Personal Access Token của GitHub, bạn có thể gọi model `gpt-4o` hay `gpt-4o-mini` miễn phí (Base URL là `https://models.inference.ai.azure.com`). Rất khuyến khích đổi sang cái này.
* **Alibaba Cloud (Qwen):** Rất mạnh tạo văn bản tiếng Việt tự nhiên (`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`).

## 4. Các hạng mục cần hoàn thiện

* **Tối ưu Prompt & Trace analysis:** Tinh chỉnh `CAMPING_SYSTEM_PROMPT` để Agent xuất văn bản đẹp và thân thiện hơn. Chạy thử các LLM khác và gom các trường hợp Agent nhầm lẫn/gọi tool sai (từ file JSON trong thư mục log) làm tài liệu đưa vào báo cáo thất bại (Failure Traces).
* **Phát triển logic Tool:** Viết thêm và hoàn thiện hàm trong `camping_tools.py`. Tìm cách bắt lỗi (exception) khi người dùng truyền tham số sai để Agent không sập mạng vòng lặp.
* **Hồ sơ báo cáo:** Viết `GROUP_REPORT.md` (chạy script so sánh để thống kê thời gian phản hồi, số token) và soạn tóm tắt lỗi (từ case phân tích) cho file `INDIVIDUAL_REPORT.md`.
