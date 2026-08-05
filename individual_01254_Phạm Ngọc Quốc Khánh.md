# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                |
| --------------- | ----------------------- |
| Họ và tên       | Phạm Ngọc Quốc Khánh   |
| MSSV            | 2A202601254             |
| Khóa/Lớp        | K4                      |
| Vai trò chính   | Coordinator Agent, Policy Agent & Schema Architect |
| Ngày hoàn thành | 2026-08-05              |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Coordinator Agent (điều phối pipeline) | `coordinator_agent.py` | Input JSON (`EC_001..EC_050`) | Orchestration flow song song `asyncio.gather`, lắp ghép `CaseOutput` | Hoàn thành |
| Customer Agent | `customer_agent.py` | `order_id`, `order_data` | `customer_unique_id`, `related_order_ids`, `is_repeat_customer` | Hoàn thành |
| Policy Agent (tổng hợp EC_POLICY_V2) | `policy_agent.py` | Kết quả từ 4 agent | Primary/secondary issues, refund, evidence IDs, resolution actions | Hoàn thành |
| Output Schema & Validation | `models.py` | Agent results | Pydantic-validated JSON output, `CaseInput` với `extra="ignore"` | Hoàn thành |
| Data Access Layer | `data_access.py` | CSV file paths | Pandas DataFrame query methods (`get_order`, `get_customer_orders`...) | Hoàn thành |
| Calculation Tools | `calc_tools.py` | Raw CSV data | `PaymentReconciliationTool`, `DeliveryTimingTool` pre-computed | Hoàn thành |
| Tài liệu kiến trúc | `architecture.md` | — | Sơ đồ Mermaid, bảng vai trò, luồng handoff | Hoàn thành |
| Trap documentation | `traps.md` | — | 16 bẫy nghiệp vụ & dữ liệu đã phát hiện và ghi chép | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Phát hiện và ghi chép 16+ bẫy nghiệp vụ | Toàn bộ pipeline, hỗ trợ Hà Anh và Quang Minh tránh bẫy | Điểm tổng tăng từ 0 → 67 → 79 điểm |
| Review và sửa lỗi evidence truncation | `policy_agent.py` — hỗ trợ Quang Minh | Fix lỗi payment evidence bị bỏ sót cho đơn multi-item |
| Nới lỏng input validation để chống crash test mù | `models.py`, `coordinator_agent.py` | `extra="forbid"` → `extra="ignore"`, loại bỏ `authenticated_customer_id` check |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Thiết kế pipeline 6-agent với asyncio | `coordinator_agent.py` | Pipeline chạy song song Customer+OrderProduct → Payment+Delivery → Policy | `.venv/bin/python codebase/runner.py` |
| Xây dựng Customer Agent tra cứu lịch sử | `customer_agent.py` | `customer_unique_id` chính xác, `related_order_ids` giữ thứ tự CSV | Kiểm tra output JSON của 50 cases |
| Áp dụng EC_POLICY_V2 với 6 primary issues | `policy_agent.py` | Đúng thứ tự ưu tiên, refund amount, evidence IDs, resolution actions | Script audit tự động trên 50 cases |
| Thiết kế Pydantic output schema | `models.py` | `CaseOutput.to_output_dict()` serialize chuẩn JSON schema Section 6 | So sánh output với README schema |
| Xây dựng Calculation Tools tách biệt | `calc_tools.py` | Tool tính toán deterministic cho Payment và Delivery | Unit test trên edge cases |

Artifact chính tạo ra: **Coordinator Agent**, **Customer Agent**, **Policy Agent** — 3 agent cốt lõi điều phối toàn bộ pipeline và ra quyết định nghiệp vụ cuối cùng. Cùng với `architecture.md` và `traps.md` làm tài liệu tham chiếu cho cả nhóm.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Xây dựng lớp điều phối (Coordinator) và lớp quyết định chính sách (Policy) cho hệ thống multi-agent. Coordinator phải chạy các agent song song đúng thứ tự phụ thuộc, còn Policy Agent phải áp dụng chính xác 6 primary issues theo thứ tự ưu tiên, xây dựng evidence IDs từ dữ liệu CSV, và tính toán refund/actions — tất cả dựa 100% vào dữ liệu kiểm chứng, không tin vào lời khiếu nại của khách hàng.

### Cách triển khai

**Coordinator Agent** (`coordinator_agent.py`):
- Nhận input JSON, validate qua Pydantic `CaseInput` (với `extra="ignore"` để chống crash từ trường lạ).
- Chạy song song `CustomerAgent` + `OrderProductAgent` (Step 2), rồi `PaymentAgent` + `DeliveryAgent` (Step 3), cuối cùng `PolicyAgent` (Step 4).
- Lắp ghép `CaseOutput` từ kết quả của tất cả agent qua Pydantic schema.

**Policy Agent** (`policy_agent.py`):
- Kiểm tra 6 primary issues theo thứ tự ưu tiên: canceled → unavailable → late_seller → late_logistics → valid_split → unsupported_claim.
- Xây dựng `evidence_ids` đảm bảo không bỏ sót payment evidence (fix lỗi truncation capacity).
- Tính `responsible_parties`: chỉ seller vi phạm (late handoff) mới vào evidence.
- Xây dựng `resolution_actions` theo đúng thứ tự nghiệp vụ, với điều kiện loại trừ `verify_payment_allocation` khi primary là `valid_split_payment`.

**Customer Agent** (`customer_agent.py`):
- Tra cứu `customer_unique_id` qua `customer_id` → lấy toàn bộ order lịch sử.
- Giữ thứ tự dòng gốc CSV cho `related_order_ids` (theo quy định Mục 6 README).
- Loại trùng lặp và giới hạn tối đa 5 order.

**Nguyên tắc không tin user**: `customer_request.message` không bao giờ được sử dụng để ra quyết định. Mọi kết luận dựa 100% vào dữ liệu CSV.

### Input, output và contract

| Thành phần              | Mô tả |
| ----------------------- | ----- |
| Input                   | 50 file JSON (`input/EC_001.json` → `EC_050.json`) chứa `case_id`, `customer_request.claimed_order_id` |
| Output                  | `CaseOutput` dict chứa 11 section (case_assessment, affected_entities, customer_context, product_context, delivery_analysis, payment_reconciliation, root_cause_analysis, evidence_ids, financial_resolution, resolution_actions) |
| Module phụ thuộc        | `data_access.py` (CSV queries), `calc_tools.py` (deterministic math), `models.py` (Pydantic schemas) |
| Module sử dụng output   | `runner.py` (ghi file JSON), Autograder (chấm điểm) |
| Điều kiện lỗi cần xử lý | Order không tồn tại (`ValueError`), input chứa trường lạ (`extra="ignore"`), zero-item orders, NaN/None trong CSV |

### Cách xác minh

```bash
.venv/bin/python codebase/runner.py
```

- **Kết quả mong đợi:** 50 file JSON output chuẩn schema, không case nào crash.
- **Kết quả thực tế:** 50/50 cases xử lý thành công, điểm leaderboard 79.1980/100.
- **Artifact/log:** `output/EC_*.json`, `logging/trace.jsonl`, `logging/metadata.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Input JSON trong test mù có thể chứa trường lạ không có trong schema đề bài (ví dụ `authenticated_customer_id`, `priority`, `metadata`). Cần quyết định: reject input lạ hay bỏ qua?

- **Các phương án đã cân nhắc:**
  1. **`extra="forbid"` (strict validation)**: Reject toàn bộ input chứa trường không mong đợi → đảm bảo input luôn đúng schema, nhưng rủi ro crash nếu test mù inject trường lạ.
  2. **`extra="ignore"` (graceful handling)**: Bỏ qua trường lạ, chỉ sử dụng các trường đã định nghĩa → robust trước input không mong đợi, nhưng không phát hiện lỗi schema.

- **Phương án đã chọn:** `extra="ignore"` (graceful handling).

- **Lý do:** Trong môi trường chấm điểm tự động, mỗi case crash nhận 0 điểm (hard gate). Rủi ro mất điểm do crash nghiêm trọng hơn rủi ro không phát hiện trường thừa. Hệ thống chỉ sử dụng `claimed_order_id` để truy vấn CSV, nên trường lạ không ảnh hưởng kết quả.

- **Bằng chứng quyết định phù hợp:** Test thành công với input chứa `extra_trap_field`, `extra_scope_field` — Pydantic bỏ qua âm thầm, case chạy bình thường.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Evidence IDs của các đơn multi-item (5+ items) bị thiếu toàn bộ payment evidence (`payment:<order_id>:1`, `payment:<order_id>:2`).

- **Lệnh hoặc bước tái hiện:**
  ```python
  # Đơn có 5 items, 2 payments:
  # detail_capacity = 20 - 1(order) - 1(seller) - 1(policy) = 17
  # items fill 5 slots → details has 5 entries
  # payments: if len(details) >= detail_capacity: break → SKIPPED!
  ```

- **Nguyên nhân gốc:** Hàm `_build_evidence_ids` trong `policy_agent.py` sử dụng biến `detail_capacity` chia sẻ giữa item evidence và payment evidence. Khi item evidence nạp đầy capacity trước, vòng lặp payment bị `break` hoàn toàn → toàn bộ payment evidence bị bỏ sót.

- **Cách xử lý:** Loại bỏ thuật toán capacity chia sẻ. Thay bằng cách thêm item evidence (`items[:5]`) và payment evidence (`payment_rows[:5]`) độc lập vào danh sách `evidence`, rồi cắt `evidence[:20]` ở cuối. Tổng tối đa = 1(order) + 5(items) + 5(payments) + 3(sellers) + 1(policy) = 15 ≤ 20, nên không bao giờ vượt giới hạn.

- **Cách xác minh sau khi sửa:**
  ```bash
  .venv/bin/python -c "..." # Script audit kiểm tra evidence_ids trên 50 cases
  # Output: 0 mismatches
  ```

- **Điều học được:** Khi xây dựng danh sách evidence từ nhiều nguồn (items, payments, sellers), không nên chia sẻ biến capacity giữa các nguồn vì nguồn nạp trước sẽ "chiếm hết" quota của nguồn sau.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ input đến output như thế nào?**
   `runner.py` đọc 50 file input JSON → `CoordinatorAgent` nhận `claimed_order_id` → `DataAccess` query 9 file CSV Olist qua Pandas → `CustomerAgent` + `OrderProductAgent` chạy song song (Step 2) → `PaymentAgent` + `DeliveryAgent` chạy song song (Step 3) → `PolicyAgent` tổng hợp áp dụng EC_POLICY_V2 (Step 4) → Coordinator lắp ghép `CaseOutput` qua Pydantic → Ghi file JSON output.

2. **Ground truth và autograder chấm điểm ra sao?**
   Autograder so sánh 50 file JSON output với hidden ground truth theo 7 hạng mục trọng số: primary/secondary issues (15%), affected entities (15%), customer/product context (15%), delivery analysis (15%), payment reconciliation (15%), root cause/evidence (15%), financial/actions (10%). Mỗi case bị hard gate nhận 0 điểm. Điểm cuối là trung bình 50 case.

3. **Quality checks ở đâu trong pipeline?**
   - **Input validation**: Pydantic `CaseInput` kiểm tra cấu trúc input (với `extra="ignore"` để chấp nhận trường lạ).
   - **Data validation**: Mỗi agent kiểm tra NaN/None/empty trước khi xử lý.
   - **Output validation**: Pydantic `CaseOutput` kiểm tra kiểu dữ liệu, giới hạn mảng, null handling.
   - **Audit scripts**: Script Python kiểm tra secondary issues, resolution actions, evidence IDs trên toàn bộ 50 cases.

4. **Vì sao phải ưu tiên dữ liệu CSV thay vì tin lời khách hàng?**
   Cùng phản ánh "giao hàng trễ" nhưng dữ liệu CSV có thể cho thấy đơn giao đúng hạn. Hệ thống dựa vào timestamp thực tế (`order_delivered_customer_date` vs `order_estimated_delivery_date`), không bao giờ dùng `customer_request.message` để ra quyết định policy.

5. **Pipeline được coi là thành công dựa trên artifact và metric nào?**
   50 file JSON output khớp schema Section 6 README, `trace.jsonl` chứa log LLM call, `metadata.json` khai báo model, điểm leaderboard ≥ 79/100, audit script kiểm tra 100% match trên tất cả hạng mục.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Ngọc Quốc Khánh
**Ngày xác nhận:** 2026-08-05
