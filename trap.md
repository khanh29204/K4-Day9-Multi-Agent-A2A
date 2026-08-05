# ⚠️ Danh Sách Bẫy & Lưu Ý Quan Trọng (Traps & Edge Cases Guide)

Tài liệu này tổng hợp toàn bộ các **bẫy nghiệp vụ (Policy Traps)**, **bẫy dữ liệu (Data Traps)** và các **trường hợp biên (Edge Cases)** trong bài lab Multi-Agent Dispute Resolution. 

Tất cả các thành viên trong team cần đọc kỹ để tránh bị trừ điểm hoặc dính **Hard Gate (0 điểm)**.

---

## 📊 Bảng Tổng Quan Các Bẫy

| STT | Tên Bẫy | Phân loại | Mức độ nguy hiểm | Hậu quả nếu dính bẫy |
|:---:|---------|-----------|------------------|----------------------|
| **1** | `customer_id` vs `customer_unique_id` | Data / Query | 🚨 **Rất Cao** | Không tìm được lịch sử khách hàng (0% điểm context) |
| **2** | Order cũ bị dính vào `affected_entities` | Schema / Policy | 🚨 **Rất Cao** | Sai cấu trúc JSON output, dính False Positive ID |
| **3** | Đơn không có Items (Zero-item order) | Schema / Null | 🚨 **Hard Gate** | Trả về 0/false thay vì `null` ➔ Hard Gate 0 điểm |
| **4** | Dịch tên danh mục bị mất data (Category Translation) | Data Join | ⚠️ **Cao** | Bị lọt sản phẩm không dịch được (dùng INNER JOIN) |
| **5** | Định dạng Evidence ID không đúng | Evidence | ⚠️ **Cao** | Bị tính là False Positive (trừ 15% điểm Evidence) |
| **6** | Thêm thừa Seller vào Evidence | Evidence | ⚠️ **Cao** | Thêm seller không vi phạm vào evidence ➔ False Positive |
| **7** | Định dạng `case_status` bị nhầm khi có Action | Policy | ⚠️ **Cao** | Đơn không hoàn tiền nhưng set `action_required` |
| **8** | Công thức `handoff_variance_hours` | Logic / Calculation | ⚠️ **Cao** | Lấy sai timestamp `shipping_limit_date` của seller |
| **9** | Thêm thừa Action `verify_payment_allocation` | Policy / Actions | 🟡 **Trung bình** | Thêm action thừa khi primary issue là `valid_split_payment` |
| **10** | Tự ý nhân `payment_value` với `installments` | Data Calculation | 🟡 **Trung bình** | Sai tổng tiền payment, làm lệch reconciliation |
| **11** | Tự đổi định dạng Timestamp / Timezone | Schema | 🟡 **Trung bình** | Sai ISO format hoặc lệch giờ do UTC conversion |
| **12** | Đơn `canceled` / `unavailable` không có payment | Policy | 🟡 **Trung bình** | Trả về refund khi khách chưa hề trả tiền |
| **13** | Vi phạm thứ tự ưu tiên Primary & Secondary Issues | Policy | ⚠️ **Cao** | Sai Issue chính / phụ (trừ 15% điểm) |
| **14** | Vượt quá giới hạn mảng (Array Limits) | Schema | 🟡 **Trung bình** | JSON vượt quá kích thước mảng cho phép |
| **15** | Tự ý dịch `category_names` sang tiếng Anh | Schema / Ground Truth | 🚨 **Rất Cao** | Sai tên danh mục ➔ Trừ 100% điểm Product Context |
| **16** | Ép kiểu Float cho `item_ids` (`...:1.0` thay vì `...:1`) | Schema / Formatting | 🚨 **Hard Gate** | Sai định dạng Item ID ➔ Bị tính False Positive 0đ |

---

## 🎯 Chi Tiết 16 Bẫy Nghiệp Vụ & Dữ Liệu

### 1. `customer_id` vs `customer_unique_id`
- **Mô tả:** Trong Olist, mỗi đơn hàng được cấp một `customer_id` mới ngẫu nhiên. Danh tính thực sự của khách hàng nằm ở cột `customer_unique_id`.
- **Dễ mắc sai lầm:** Dùng `customer_id` để query các order khác của khách hàng ➔ Luôn trả về mảng rỗng.
- **Cách xử lý đúng:**
  1. Lấy `customer_id` từ `order_data`.
  2. Query table `customers` ➔ lấy `customer_unique_id`.
  3. Query lại table `customers` bằng `customer_unique_id` ➔ lấy danh sách tất cả `customer_id` của khách.
  4. Query table `orders` bằng danh sách `customer_id` ➔ lấy các order lịch sử.

---

### 2. Order Lịch Sử Bị Dính Vào `affected_entities`
- **Mô tả:** Khách hàng có thể có 3-4 order cũ trong lịch sử (`related_order_ids`).
- **Dễ mắc sai lầm:** Đưa toàn bộ các order cũ vào `affected_entities.order_ids`.
- **Cách xử lý đúng:**
  - `affected_entities.order_ids`: **CHỈ chứa 1 order duy nhất** là `claimed_order_id`.
  - `customer_context.related_order_ids`: Chứa tối đa 5 order ID lịch sử (không chứa `claimed_order_id`).

---

### 3. Đơn Không Có Items (Zero-Item Order)
- **Mô tả:** Các đơn hàng bị hủy (`canceled`) hoặc không khả dụng (`unavailable`) có thể không có bất kỳ dòng item nào trong `olist_order_items_dataset.csv`.
- **Dễ mắc sai lầm:** Gán các biến tính toán bằng `0.0` hoặc `reconciled = False`.
- **Cách xử lý đúng (Quy tắc README Line 113):**
  - `expected_total_brl` = `null` (`None`)
  - `difference_brl` = `null` (`None`)
  - `reconciled` = `null` (`None`)
  - `affected_entities.item_ids` = `[]`
  - `affected_entities.seller_ids` = `[]`
  - `product_context.product_ids` = `[]`
  - `product_context.category_names` = `[]`
  - `delivery_analysis.seller_handoff_analysis` = `[]`

---

### 4. Dịch Tên Danh Mục Bị Mất Data (Category Translation)
- **Mô tả:** File `product_category_name_translation.csv` chỉ chứa 71 danh mục, trong khi `olist_products_dataset.csv` có 73 danh mục (thiếu `pc_gamer` và `portateis_cozinha_e_preparadores_de_alimentos`).
- **Dễ mắc sai lầm:** Dùng `INNER JOIN` giữa Products và Translation ➔ Mất các sản phẩm thuộc danh mục chưa dịch.
- **Cách xử lý đúng:** Luôn giữ nguyên tên gốc tiếng Bồ Đào Nha từ cột `product_category_name` trong `products.csv`.

---

### 5. Định Dạng Evidence ID Chuẩn Bằng Bằng Chứng Thật
- **Mô tả:** Evidence ID phải dựng trực tiếp từ dữ liệu CSV theo đúng cú pháp.
- **Cú pháp quy định:**
  - `order:<order_id>`
  - `item:<order_id>:<order_item_id>` (Ví dụ: `item:e481f5...:1`) ➔ `order_item_id` phải là **số nguyên (int)**, không dùng float `1.0` hay string UUID.
  - `payment:<order_id>:<payment_sequential>` (Ví dụ: `payment:e481f5...:1`) ➔ `payment_sequential` phải là **số nguyên (int)**.
  - `seller:<seller_id>`
  - `policy:<root_cause_code>`
- **Lưu ý:** Evidence sai cú pháp hoặc chứa ID không có trong CSV bị tính là **False Positive** (trừ điểm).

---

### 6. Thêm Thừa Seller Vào Evidence
- **Mô tả:** Trong một đơn multi-seller (ví dụ có Seller A và Seller B), nhưng chỉ có Seller A bàn giao hàng trễ (`late_handoff = True`).
- **Dễ mắc sai lầm:** Đưa cả Seller B vào `evidence_ids`.
- **Cách xử lý đúng:** Chỉ đưa `seller:<seller_id>` vào `evidence_ids` nếu seller đó thuộc danh sách `responsible_parties` (tức là seller thực sự vi phạm).

---

### 7. Quy Tắc Gán `case_status`
- **Mô tả:** README quy định rõ ý nghĩa của 2 trạng thái:
  - `action_required`: Cần hoàn tiền (`recommended_refund_brl > 0`).
  - `no_action`: Không hoàn tiền (`recommended_refund_brl == 0`).
- **Dễ mắc sai lầm:** Đơn hàng có primary issue là `valid_split_payment` có action `explain_valid_split_payment` ➔ Nhầm thành `action_required` vì "có thực hiện hành động giải thích".
- **Cách xử lý đúng:** Kiểm tra `recommended_refund_brl > 0` ? `"action_required"` : `"no_action"`.

---

### 8. Công Thức Tính `handoff_variance_hours`
- **Mô tả:** `handoff_variance_hours = order_delivered_carrier_date - shipping_limit_date (sớm nhất của seller)`.
- **Dễ mắc sai lầm:**
  1. Nếu 1 seller có 2 item với 2 `shipping_limit_date` khác nhau ➔ Phải chọn ngày **SỚM NHẤT** (`min()`) của seller đó.
  2. Lấy nhầm ngày giao cho khách (`order_delivered_customer_date`) thay vì ngày giao cho ĐVVC (`order_delivered_carrier_date`).

---

### 9. Quy Tắc Loại Trừ Action `verify_payment_allocation`
- **Mô tả:** Thứ tự thêm các action bổ sung:
  1. Action chính (`issue_full_refund` / `refund_freight` / `explain_valid_split_payment` / `reject_late_refund`)
  2. `review_seller_handoff` (nếu late seller) HOẶC `review_carrier_delay` (nếu late logistics)
  3. `verify_refund_completion` (nếu refund > 0)
  4. `coordinate_multi_seller_case` (nếu multi-seller)
  5. `verify_payment_allocation` (nếu split payment)
- **ĐIỀU KIỆN ĐẶC BIỆT:** **KHÔNG** thêm `verify_payment_allocation` khi Primary Issue là `valid_split_payment` (vì Action chính đã giải thích split payment).

---

### 10. Không Nhân `payment_value` Với `payment_installments`
- **Mô tả:** Trong `olist_order_payments_dataset.csv`, cột `payment_value` đã là **tổng giá trị tiền** của dòng payment đó.
- **Dễ mắc sai lầm:** Nghĩ rằng `payment_value` là tiền từng kỳ và lấy `payment_value * payment_installments` ➔ Làm sai lệch hoàn toàn số tiền đối soát.
- **Cách xử lý đúng:** Dùng trực tiếp `payment_value`.

---

### 11. Định Dạng Timestamp & Timezone
- **Mô tả:** README quy định: *"Các timestamp được so sánh theo giá trị trong CSV; không cần chuyển múi giờ. Giữ nguyên định dạng `YYYY-MM-DD HH:MM:SS`"*.
- **Dễ mắc sai lầm:** Chuyển timestamp thành datetime object rồi `.isoformat()` ra `2018-03-31T15:23:33Z` (thêm chữ T và Z).
- **Cách xử lý đúng:** Đảm bảo chuỗi timestamp xuất ra JSON có dạng đúng `YYYY-MM-DD HH:MM:SS` (hoặc `null` nếu không có dữ liệu).

---

### 12. Đơn `canceled` / `unavailable` Không Có Payment
- **Mô tả:** Đơn bị hủy nhưng tổng tiền thanh toán = 0 BRL (`payment_total == 0`).
- **Dễ mắc sai lầm:** Tự động refund full tiền đơn.
- **Cách xử lý đúng:** Điều kiện của `canceled_order_paid` là `order_status = canceled` **VÀ tổng payment > 0**. Nếu payment = 0 thì không thỏa mãn primary issue này.

---

### 13. Thứ Tự Ưu Tiên Nghiệp Vụ (Priority Order)

#### Primary Issues (Check từ trên xuống dưới, dừng ở điều kiện đầu tiên khớp):
1. `canceled_order_paid`: `status == canceled` AND `payment_total > 0`
2. `unavailable_order_paid`: `status == unavailable` AND `payment_total > 0`
3. `late_delivery_seller`: Giao trễ (`delivery_variance > 0`) AND Carrier nhận hàng sau ít nhất một `shipping_limit_date` của seller (`late_handoff == True`).
4. `late_delivery_logistics`: Giao trễ (`delivery_variance > 0`) AND KHÔNG seller nào giao trễ cho carrier.
5. `valid_split_payment`: Có từ 2 payment rows AND `reconciled == True` (tổng payment khớp tổng item+freight trong sai số 0.10 BRL).
6. `unsupported_late_claim`: Đơn giao đúng hạn/không trễ AND `reconciled == True`.

#### Secondary Issues (Thêm theo đúng thứ tự 1-5 nếu thỏa điều kiện):
1. `multi_item_order`: Số lượng item rows >= 2
2. `multi_seller_order`: Số lượng seller unique >= 2
3. `split_payment`: Số lượng payment rows >= 2
4. `repeat_customer`: Cùng `customer_unique_id` có order khác
5. `multiple_categories`: Số lượng category unique >= 2

---

### 14. Giới Hạn Kích Thước Mảng (Array Limits)

Mọi mảng xuất ra JSON output đều phải được cắt gọn (`[:limit]`) để không vượt quá giới hạn:

```python
limit_order_ids = 5
limit_item_ids = 5
limit_seller_ids = 3
limit_payment_ids = 5
limit_related_order_ids = 5
limit_product_ids = 5
limit_category_names = 5
limit_ranked_causes = 3
limit_responsible_parties = 3
limit_evidence_ids = 20
limit_resolution_actions = 5
```

---

### 15. Tự Ý Dịch `category_names` Sang Tiếng Anh
- **Mô tả:** Trong `olist_products_dataset.csv`, cột `product_category_name` lưu tên danh mục gốc bằng tiếng Bồ Đào Nha (ví dụ `beleza_saude`). Có 1 file `product_category_name_translation.csv` dùng để dịch sang tiếng Anh (`health_beauty`).
- **Dễ mắc sai lầm:** Dịch tên category sang tiếng Anh trong trường `product_context.category_names`.
- **Cách xử lý đúng:** Ground truth của bộ chấm yêu cầu **GIỮ NGUYÊN TÊN GỐC TIẾNG BỒ ĐÀO NHA** từ cột `product_category_name` trong `products.csv` (ví dụ `beleza_saude`). Không dịch sang tiếng Anh.

---

### 16. Ép Kiểu Float Cho `item_ids` (`...:1.0` thay vì `...:1`)
- **Mô tả:** Cột `order_item_id` khi đọc từ CSV qua Pandas DataFrame mặc định được nhận diện là Float (`1.0`). Khi format chuỗi `f"{order_id}:{item['order_item_id']}"` sẽ tạo ra `...:1.0`.
- **Dễ mắc sai lầm:** Không ép kiểu `int` cho `order_item_id` ➔ Tạo ra ID `...:1.0`.
- **Cách xử lý đúng:** Ép kiểu `int(float(item['order_item_id']))` để đảm bảo chuỗi trả về đúng dạng `...:1`.

---

## 🛠️ Code Verification Status

Tất cả 16 bẫy trên đã được kiểm tra và xử lý triệt để trong codebase:
- ✅ `models.py`: Đã mặc định mảng rỗng `[]` thay vì `null` cho các trường danh sách.
- ✅ `order_product_agent.py`: Đã giữ nguyên tên tiếng Bồ Đào Nha cho `category_names` (`product_category_name`) và ép kiểu `int(float(...))` cho `order_item_id`.
- ✅ `policy_agent.py`: Đã cài đặt đúng 100% thứ tự ưu tiên, công thức, evidence format, và điều kiện loại trừ action.
- ✅ `data_access.py`: Đã hỗ trợ lookup `customer_unique_id`.
