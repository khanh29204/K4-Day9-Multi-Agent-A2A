# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                          |
| --------------- | --------------------------------- |
| Họ và tên       | Phạm Hà Anh                       |
| MSSV            | 2A202601240                       |
| Khóa/Lớp        | K4                                |
| Vai trò chính   | Data Engineer & Multi-Agent Tester|
| Ngày hoàn thành | 2026-08-05                        |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable    | File/hàm phụ trách                                | Input nhận vào         | Output bàn giao               | Trạng thái |
| --------------------- | ------------------------------------------------- | ---------------------- | ----------------------------- | ---------- |
| CSDL SQLite & Indexes | `create_sqlite_db.py`, `data/olist_ecommerce.db` | 9 file CSV thô         | `olist_ecommerce.db` (156MB)  | Hoàn thành |
| Agent Data Tools      | `db_tools.py`                                     | Order ID, Customer ID  | Dữ liệu context chuẩn (< 5ms) | Hoàn thành |
| Auto-Evaluator        | `evaluate_outputs.py`                             | `output/*.json`        | Thống kê điểm 7 tiêu chí     | Hoàn thành |
| Fixing Data Traps     | `codebase/agents/order_product_agent.py`          | `product_category_name`| Giữ tên gốc tiếng Bồ Đào Nha  | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                        | Thành viên/module được hỗ trợ       | Kết quả                                    |
| -------------------------------- | ----------------------------------- | ------------------------------------------ |
| Tích hợp Groq API & LLM Client   | `codebase/runner.py`, `llm_client.py`| Chạy thực nghiệm pipeline thành công       |
| Rà soát bẫy dữ liệu (Data Traps) | `traps.md`, `codebase/agents/`      | Đảm bảo xử lý đúng 14/14 bẫy nghiệp vụ     |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện              | File/hàm/artifact liên quan                | Kết quả bàn giao           | Cách xác minh                        |
| ---------------------------------- | ------------------------------------------ | -------------------------- | ------------------------------------ |
| Đóng gói CSDL & Đánh B-Tree Index  | `create_sqlite_db.py`, `db_tools.py`       | Database SQLite tối ưu     | `python db_tools.py`                 |
| Sửa lỗi dịch tên danh mục sản phẩm| `codebase/agents/order_product_agent.py`   | Category giữ tên gốc Bồ Đào Nha| `python -m unittest codebase.tests.test_order_product_agent` |
| Đánh giá và kiểm thử tự động      | `evaluate_outputs.py`                      | 50/50 test cases đạt 100%  | `python evaluate_outputs.py`         |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Tối ưu tra cứu dữ liệu từ 9 CSV thô sang SQLite đánh Index B-Tree giúp tốc độ truy vấn giảm từ > 1s xuống < 5ms per query. Sửa lỗi Category Translation từ tiếng Anh (`health_beauty`) về tiếng Bồ Đào Nha gốc (`beleza_saude`) giúp khớp 100% mẫu Ground Truth của bộ chấm điểm.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Việc tra cứu 9 file CSV thô khi chạy 50 trường hợp qua 6 agent gây nghẽn hiệu năng, tốn token và tốn thời gian. Đồng thời, việc dịch tên danh mục sản phẩm từ tiếng Bồ Đào Nha sang tiếng Anh làm mất dữ liệu 2 danh mục và làm sai lệch Ground Truth của bộ test chấm điểm.

### Cách triển khai
1. Sử dụng Pandas và SQLite3 tự động đóng gói 9 bảng dữ liệu Olist thành `olist_ecommerce.db`.
2. Tạo các B-Tree Indexes trên các cột khóa chính/ngoại (`order_id`, `customer_id`, `seller_id`, `product_id`).
3. Cập nhật `order_product_agent.py` lấy trực tiếp `product_category_name` từ CSV mà không thông qua hàm dịch `get_category_translation`.
4. Xây dựng script `evaluate_outputs.py` để chấm điểm 7 thành phần của output JSON.

### Input, output và contract

| Thành phần              | Mô tả                                                          |
| ----------------------- | -------------------------------------------------------------- |
| Input                   | 9 file CSV dữ liệu Olist trong `data/`, 50 file JSON trong `input/` |
| Output                  | CSDL SQLite `olist_ecommerce.db`, 50 file JSON trong `output/` |
| Module phụ thuộc        | `data_access.py`, `codebase/agents/order_product_agent.py`    |
| Module sử dụng output   | `coordinator_agent.py`, `runner.py`, `evaluate_outputs.py`     |
| Điều kiện lỗi cần xử lý | Trường hợp danh mục chưa có bản dịch hoặc đơn hàng bị hủy 0 item|

### Cách xác minh

```bash
python db_tools.py
python -m unittest codebase.tests.test_order_product_agent -v
python evaluate_outputs.py
```

- **Kết quả mong đợi:** Tốc độ query < 10ms, unit test passed, score evaluator đạt 100.00%.
- **Kết quả thực tế:** Tốc độ query < 5ms, 2/2 unit test pass, score evaluator đạt 100.00%.
- **Artifact/log:** `output/*.json`, `output.zip`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp xử lý tên danh mục sản phẩm (`product_category_name`).
- **Các phương án đã cân nhắc:**
  1. Phương án A: Dùng `get_category_translation()` dịch toàn bộ tên danh mục sang tiếng Anh (`health_beauty`).
  2. Phương án B: Giữ nguyên tên danh mục gốc tiếng Bồ Đào Nha (`beleza_saude`) lấy trực tiếp từ `olist_products_dataset.csv`.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** File dịch `product_category_name_translation.csv` chỉ chứa 71 danh mục (thiếu 2 danh mục so với 73 danh mục thực tế), và Ground Truth của bộ test chấm điểm yêu cầu giữ nguyên tên gốc tiếng Bồ Đào Nha.
- **Bằng chứng quyết định phù hợp:** Kết quả khớp 100% từng key/value với Ground Truth case `EC_001.json` và khôi phục 43 file JSON bị lệch tên danh mục.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Bài nộp bị rớt điểm ở mục `Ngữ cảnh khách hàng/sản phẩm` do tên danh mục xuất ra tiếng Anh thay vì tiếng Bồ Đào Nha gốc.
- **Lệnh hoặc bước tái hiện:** So sánh `product_context.category_names` giữa output được sinh ra (`health_beauty`) và Ground Truth mẫu (`beleza_saude`).
- **Nguyên nhân gốc:** `OrderProductAgent` trước đó đã tự động gọi `self.data.get_category_translation(category_name)`.
- **Cách xử lý:** Cập nhật `order_product_agent.py` loại bỏ bước dịch, gán trực tiếp `category_name` thu thập từ `product.get("product_category_name")`.
- **Cách xác minh sau khi sửa:** Chạy lại script convert và kiểm tra `output/EC_001.json` thấy `"category_names": ["beleza_saude"]`.
- **Điều học được:** Luôn tuân thủ đúng định dạng dữ liệu gốc của Ground Truth thay vì tự động chuyển đổi ngôn ngữ khi không có yêu cầu bắt buộc.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ input đến output:** Input JSON chứa `claimed_order_id` $\rightarrow$ `CoordinatorAgent` khởi tạo và gọi `CustomerAgent` & `OrderProductAgent` $\rightarrow$ Query SQLite/Pandas $\rightarrow$ Handoff kết quả cho `PaymentAgent` & `DeliveryAgent` đối soát $\rightarrow$ `PolicyAgent` tổng hợp và áp dụng quy tắc `EC_POLICY_V2` xuất ra JSON cuối cùng.
2. **Evaluation set và ground-truth:** Bộ 50 trường hợp `EC_001.json` - `EC_050.json` dùng để đo đạc độ chính xác của Primary/Secondary Issues, Affected Entities, Context, Delivery, Payment, Root Cause và Financial Resolution.
3. **Quy tắc gán case status:** `action_required` khi `recommended_refund_brl > 0`, ngược lại là `no_action`.
4. **Vì sao phải đảm bảo array limits:** Mọi mảng output (`order_ids`, `item_ids`, `seller_ids`, `evidence_ids`,...) đều phải được `[:limit]` để tránh vi phạm giới hạn kích thước mảng của bộ chấm tự động.
5. **Chống bẫy dữ liệu:** Zero-item order bắt buộc trả về `null` cho `expected_total_brl`, `difference_brl` và `reconciled`.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Hà Anh  
**Ngày xác nhận:** 2026-08-05
