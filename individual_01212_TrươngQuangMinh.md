# Báo cáo vai trò cá nhân — Day 9: Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trương Quang Minh |
| MSSV | 2A202601212 |
| Khóa/Lớp | K4 |
| Vai trò chính | Payment Agent, Delivery Agent và tích hợp/chạy thử hệ thống |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Payment Agent | `codebase/agents/payment_agent.py`, `PaymentAgent.process()` | `order_id`, danh sách `items`, dữ liệu `order_payments` | Tổng tiền thanh toán, tổng tiền kỳ vọng, chênh lệch, trạng thái đối soát, loại thanh toán và payment IDs | Hoàn thành |
| Delivery Agent | `codebase/agents/delivery_agent.py`, `DeliveryAgent.process()` | `order_data`, danh sách item có `seller_id` và `shipping_limit_date` | Độ trễ giao hàng, phân tích handoff theo seller, seller giao trễ và bên chịu trách nhiệm | Hoàn thành |
| Cấu hình kết nối và chạy pipeline | `codebase/config.py`, `codebase/runner.py`, `.env.example` | Biến môi trường, thư mục dữ liệu/input/output và danh sách case | Kết nối cấu hình hóa, chạy được batch 50 case, ghi output/log/metadata | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chạy thử và kiểm tra tích hợp end-to-end | `CoordinatorAgent`, `runner.py`, `evaluate_outputs.py` | Xác nhận 50/50 case được xử lý và output đáp ứng schema |
| Hỗ trợ debug lỗi ghi output và lỗi kết nối LLM | Runner và cấu hình LLM | Bổ sung cơ chế ghi file tạm rồi thay thế atomic; chuyển LLM sang chế độ tùy chọn để batch dữ liệu vẫn chạy được khi API lỗi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Đối soát các payment row của một order với tiền item + freight | `payment_agent.py`, `output/EC_001.json` | `expected_total_brl`, `payment_total_brl`, `difference_brl`, `reconciled` và `payment_types` | Output mẫu có `237.34 BRL` thanh toán, chênh lệch `0.0`, `reconciled=true` |
| Phân tích thời gian giao hàng và handoff của seller | `delivery_agent.py`, `output/EC_048.json` | `delivery_variance_hours`, `seller_handoff_analysis`, `late_handoff_seller_ids`, `late_delivery_type` | Log ghi nhận case trễ `185.7` giờ và xác định loại trễ là `seller` |
| Cấu hình kết nối và chạy thử batch | `config.py`, `runner.py`, `logging/metadata.json` | Model/provider, API base URL, cờ `ENABLE_LLM`, đường dẫn project và metadata của lần chạy | Batch cuối xử lý đủ 50 case trong khoảng `9.46s`, không có case thất bại |
| Kiểm tra chất lượng output | `evaluate_outputs.py`, `output/EC_001..EC_050.json` | 50/50 file output hợp lệ theo các nhóm kiểm tra của evaluator | Overall schema/compliance score: `79.00%` |

Artifact chính do phần việc tạo ra hoặc giúp xác minh là 50 file JSON trong `output/`, log chạy trong `logging/run_*.log`, cùng `logging/metadata.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần tách rõ hai loại phân tích nghiệp vụ:

- Xác định số tiền khách đã thanh toán có khớp với tổng tiền sản phẩm và phí vận chuyển hay không.
- Xác định đơn hàng có giao trễ hay không, seller bàn giao trễ hay phần chậm phát sinh ở logistics.

Ngoài ra, pipeline phải chạy được khi LLM không khả dụng; các quyết định định lượng và policy không được phụ thuộc bắt buộc vào API bên ngoài.

### Cách triển khai

`PaymentAgent` lấy toàn bộ payment row của order, sắp xếp theo `payment_sequential`, chuyển các giá trị số không hợp lệ thành giá trị an toàn, rồi tính:

```text
expected_total_brl = sum(price) + sum(freight_value)
difference_brl = payment_total_brl - expected_total_brl
reconciled = abs(difference_brl) <= 0.10
```

Agent cũng phát hiện split payment khi order có từ hai payment row trở lên và tạo ID dạng `order_id:payment_sequential` để agent downstream truy vết.

`DeliveryAgent` chuẩn hóa timestamp, tính chênh lệch giữa thời điểm giao thực tế và thời điểm dự kiến. Với từng seller, agent chọn `shipping_limit_date` sớm nhất rồi so sánh với `order_delivered_carrier_date`. Nếu giao trễ và có seller handoff trễ thì phân loại là `seller`; nếu không thì phân loại là `logistics`.

Trong `config.py`, cấu hình được đọc từ `.env` ở project root, hỗ trợ `DASHSCOPE_API_KEY` và alias `MODEL_API_KEY`, đồng thời cấu hình riêng `MODEL_BASE_URL`, `MODEL_PROVIDER`, `ENABLE_LLM`, `MAX_RETRIES` và `TEMPERATURE`. Mặc định `ENABLE_LLM=false`, giúp chạy batch deterministic và reproducible. `runner.py` gọi các agent, ghi output từng case và tạo trace/metadata trong thư mục `logging/`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input của Payment Agent | `order_id`, `items[].price`, `items[].freight_value`, các row từ `order_payments` |
| Output của Payment Agent | `payment_total_brl`, `expected_total_brl`, `difference_brl`, `reconciled`, `payment_types`, `is_split_payment`, `affected_payment_ids` |
| Input của Delivery Agent | Timestamp trong `order_data` và `items[].seller_id`, `items[].shipping_limit_date` |
| Output của Delivery Agent | `delivery_variance_hours`, `seller_handoff_analysis`, `late_handoff_seller_ids`, `is_late_delivery`, `late_delivery_type` |
| Module phụ thuộc | `DataAccess`, `BaseAgent`, `CoordinatorAgent`, `config.py` |
| Module sử dụng output | `PolicyAgent`, `VerifierAgent` và output assembler |
| Điều kiện lỗi cần xử lý | Giá trị payment/timestamp thiếu hoặc không hợp lệ, LLM timeout/API error, lỗi ghi file output |

### Cách xác minh

```bash
cd codebase
python runner.py
cd ..
python evaluate_outputs.py
```

- **Kết quả mong đợi:** Tạo đủ `EC_001.json` đến `EC_050.json`, không làm dừng batch khi LLM tắt hoặc không khả dụng; evaluator đọc được toàn bộ output.
- **Kết quả thực tế:** 50/50 case hoàn tất, 0 case thất bại; evaluator báo `100.00%` cho schema/compliance validity.
- **Artifact/log:** `output/EC_001.json` đến `output/EC_050.json`, `logging/run_20260805_164601.log`, `logging/metadata.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** LLM có thể hỗ trợ giải thích, nhưng API key, quyền truy cập model hoặc kết nối mạng không ổn định; nếu bắt buộc LLM thì kết quả batch sẽ khó tái lập.
- **Các phương án đã cân nhắc:** (1) Bắt buộc gọi LLM cho mỗi agent; (2) tính toán payment/delivery và policy bằng dữ liệu, chỉ bật LLM cho phần giải thích tùy chọn.
- **Phương án đã chọn:** Dùng phương án 2, đặt `ENABLE_LLM=false` mặc định và cho phép bật qua biến môi trường.
- **Lý do:** Các phép tính đối soát và thời gian cần deterministic; batch vẫn chạy được khi API trả lỗi, đồng thời vẫn giữ khả năng tích hợp LLM khi môi trường đã cấu hình đúng.
- **Bằng chứng quyết định phù hợp:** Lần chạy cuối tạo đủ 50 output, log có 50 dòng `completed`, không có `failed`, và evaluator đạt 100% schema/compliance validity.

## 6. Một lỗi hoặc blocker đã xử lý

### Lỗi ghi file output

- **Triệu chứng:** Lần chạy `run_20260805_162410.log` ghi nhận `PermissionError` khi ghi đè `output/EC_001.json`.
- **Nguyên nhân gốc:** Ghi trực tiếp vào file output có thể gặp file đang bị khóa hoặc quyền thay thế không ổn định.
- **Cách xử lý:** `runner.py` ghi JSON vào file tạm trong cùng thư mục, flush và `fsync`, sau đó dùng `os.replace()` để thay thế file đích theo cách atomic; file tạm được dọn nếu có exception.
- **Cách xác minh sau khi sửa:** `logging/run_20260805_164601.log` ghi nhận đủ `EC_001`–`EC_050 completed`, không có case failed.
- **Điều học được:** Luồng batch cần cơ chế ghi output có tính atomic để một lỗi I/O không làm hỏng artifact hoặc gây trạng thái ghi dở.

### Lỗi kết nối/API LLM được hỗ trợ debug

- **Triệu chứng:** Một số lần chạy ghi nhận lỗi connection, HTTP 401 do API key không hợp lệ hoặc HTTP 403 do model chưa được cấp quyền.
- **Cách xử lý:** Kiểm tra lại `.env.example` và cách nạp `.env` từ project root; tách LLM thành phần tùy chọn bằng `ENABLE_LLM`, để fallback deterministic xử lý dữ liệu và policy.
- **Cách xác minh:** Chạy lại với `ENABLE_LLM=false`; batch 50 case hoàn tất và output không chứa API key, token hoặc secret.

## 7. Hiểu biết về luồng end-to-end

1. Input `EC_001`–`EC_050` được `runner.py` đọc, `DataAccess` nạp các CSV Olist, sau đó `CoordinatorAgent` lấy order/customer/item context và gọi `PaymentAgent` cùng `DeliveryAgent` song song. Kết quả được chuyển cho `PolicyAgent`, chuẩn hóa qua `VerifierAgent` rồi ghi thành JSON trong `output/`.
2. Bài lab này không dùng Crossref hoặc vector index. Evaluation set là 50 case JSON cố định; evaluator kiểm tra các trường bắt buộc, kiểu dữ liệu và sự hiện diện của evidence/output contract để phát hiện output thiếu hoặc sai cấu trúc.
3. Quality check chính nằm ở việc parse dữ liệu, xử lý timestamp/payment thiếu, kiểm tra các trường delivery/payment trong output và đối chiếu log số case hoàn tất. Freshness monitoring không phải thành phần được triển khai trong pipeline này.
4. Dùng cùng một test set giúp so sánh công bằng trước và sau khi sửa agent/config/runner, đồng thời phân biệt lỗi logic với lỗi do input thay đổi.
5. Việc sửa được xem là thành công khi tạo đủ 50 output JSON, runner không có case failed, output có đủ payment/delivery fields và evaluator đạt `100.00%` schema/compliance validity.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu biết của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trương Quang Minh  
**Ngày xác nhận:** 2026-08-05
