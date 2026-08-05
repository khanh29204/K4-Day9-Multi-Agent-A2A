# 🏗️ Phân Chia Công Việc - Team 4 Người

> **Repo**: `K4-Day9-Multi-Agent-A2A`
> **Codebase**: `codebase/`
> **Deadline**: 17h30 hôm nay

---

## Tổng quan Pipeline

```
Input JSON → Coordinator
                ├─► [Step 2] Customer Agent ──────┐
                ├─► [Step 2] Order/Product Agent ──┤ (song song)
                │                                  │
                ├─► [Step 3] Payment Agent ────────┤ (cần items từ Step 2)
                ├─► [Step 3] Delivery Agent ───────┤ (song song)
                │                                  │
                └─► [Step 4] Policy Agent ─────────┘ (cần tất cả)
                         │
                    Assemble Output → Output JSON
```

---

## 👤 Người 1 — Customer Agent + Order/Product Agent

**Files cần sửa:**
- `codebase/agents/customer_agent.py`
- `codebase/agents/order_product_agent.py`

**Độ khó**: ⭐⭐ (Trung bình)
**Không phụ thuộc ai** — có thể làm ngay.

### Customer Agent — Implement `process()`

**Input từ context:**
```python
order_id = context["order_id"]          # str
order_data = context["order_data"]      # dict có key "customer_id"
```

**DataAccess methods cần dùng:**
```python
self.data.get_customer(customer_id)         # → dict hoặc None
self.data.get_customer_orders(customer_unique_id)  # → list[dict]
```

**Output phải trả về:**
```python
{
    "customer_unique_id": "abc123",           # từ get_customer()
    "related_order_ids": ["order_x", ...],    # order_id của các order khác (tối đa 5)
    "is_repeat_customer": True/False,         # True nếu có >1 order
}
```

**Logic:**
1. `customer_id = order_data["customer_id"]`
2. `customer = self.data.get_customer(customer_id)` → lấy `customer_unique_id`
3. `all_orders = self.data.get_customer_orders(customer_unique_id)`
4. Lọc bỏ `order_id` hiện tại → `related_order_ids` (tối đa 5)
5. `is_repeat_customer = len(related_order_ids) > 0`

### Order/Product Agent — Implement `process()`

**Input từ context:**
```python
order_id = context["order_id"]
```

**DataAccess methods cần dùng:**
```python
self.data.get_order_items(order_id)        # → list[dict] có price, freight_value, seller_id, product_id
self.data.get_product(product_id)          # → dict có product_category_name
self.data.get_seller(seller_id)            # → dict
self.data.get_category_translation(name)   # → str (English name)
```

**Output phải trả về:**
```python
{
    "items": [...],                          # raw item dicts từ CSV
    "products": [...],                       # product dicts
    "sellers": [...],                        # seller dicts (unique)
    "categories": ["electronics", ...],      # category names (English, unique)
    "is_multi_item": True/False,             # len(items) >= 2
    "is_multi_seller": True/False,           # len(unique sellers) >= 2
    "is_multiple_categories": True/False,    # len(unique categories) >= 2
    "affected_item_ids": ["order_id:1", ...],   # format: "{order_id}:{order_item_id}"
    "affected_seller_ids": ["seller_abc", ...],  # unique seller_ids (tối đa 3)
    "affected_product_ids": ["prod_xyz", ...],   # unique product_ids (tối đa 5)
}
```

**Logic:**
1. `items = self.data.get_order_items(order_id)` — nếu rỗng thì return tất cả rỗng/None
2. Với mỗi item: `get_product(item["product_id"])`, `get_seller(item["seller_id"])`
3. Category: `get_category_translation(product["product_category_name"])`
4. Build các flags boolean và affected IDs

---

### 📋 Prompt gợi ý cho agent coding (Người 1):

```
Implement process() cho CustomerAgent trong file codebase/agents/customer_agent.py
và OrderProductAgent trong file codebase/agents/order_product_agent.py.

Đọc kỹ README.md (Section 4, 5, 6) để hiểu output schema.
Đọc codebase/data_access.py để biết các methods có sẵn.
Đọc codebase/models.py để biết output models.

Quy tắc:
- Dùng self.data (DataAccess) để query, KHÔNG dùng LLM cho phần này
- Trả về dict với đúng keys đã document trong docstring
- Handle trường hợp data không tìm thấy (return None/empty)
- Giới hạn: tối đa 5 order IDs, 5 product IDs, 3 seller IDs
- Không cần dùng self.llm (LLM) cho logic này — pure data lookup
```

---

## 👤 Người 2 — Payment Agent + Delivery Agent

**Files cần sửa:**
- `codebase/agents/payment_agent.py`
- `codebase/agents/delivery_agent.py`

**Độ khó**: ⭐⭐⭐ (Khá, cần tính toán chính xác)
**Phụ thuộc**: Cần `items` từ OrderProductAgent (Người 1), nhưng có thể code song song vì biết rõ format.

### Payment Agent — Implement `process()`

**Input từ context:**
```python
order_id = context["order_id"]
items = context.get("items", [])   # list[dict] có "price", "freight_value"
```

**DataAccess methods cần dùng:**
```python
self.data.get_order_payments(order_id)  # → list[dict] có payment_sequential, payment_type, payment_value
```

**Output phải trả về:**
```python
{
    "payment_rows": [...],                  # raw payment dicts
    "item_total_brl": 194.0,                # sum(item["price"]) — None nếu không có items
    "freight_total_brl": 18.27,             # sum(item["freight_value"]) — None nếu không có items
    "expected_total_brl": 212.27,           # item_total + freight_total — None nếu không có items
    "payment_total_brl": 212.27,            # sum(payment["payment_value"])
    "difference_brl": 0.0,                  # payment_total - expected_total — None nếu không có items
    "reconciled": True,                     # abs(difference) <= 0.10 — None nếu không có items
    "payment_types": ["credit_card", ...],  # unique payment types
    "is_split_payment": True,               # len(payment_rows) >= 2
    "affected_payment_ids": ["order_id:1", ...],  # format: "{order_id}:{payment_sequential}"
}
```

> [!IMPORTANT]
> **Làm tròn 2 chữ số thập phân** cho tất cả giá trị tiền: `round(value, 2)`
> Nếu `items` rỗng → `item_total_brl`, `freight_total_brl`, `expected_total_brl`, `difference_brl`, `reconciled` = `None`

### Delivery Agent — Implement `process()`

**Input từ context:**
```python
order_id = context["order_id"]
order_data = context["order_data"]  # dict có các timestamp columns
items = context.get("items", [])    # list[dict] có "seller_id", "shipping_limit_date"
```

**Output phải trả về:**
```python
{
    "delivered_at": "2018-03-31 15:23:33",         # order_delivered_customer_date
    "estimated_delivery_at": "2018-03-28 00:00:00", # order_estimated_delivery_date
    "carrier_handoff_at": "2018-03-15 21:33:51",   # order_delivered_carrier_date
    "delivery_variance_hours": 87.39,              # (delivered - estimated) in hours, round 2
    "seller_handoff_analysis": [
        {
            "seller_id": "abc",
            "shipping_limit_at": "2018-03-15 20:31:15",  # earliest shipping_limit per seller
            "handoff_variance_hours": 1.04,                # (carrier_date - shipping_limit) in hours
            "late_handoff": True,                          # handoff_variance > 0
        }
    ],
    "late_handoff_seller_ids": ["abc"],  # sellers có late_handoff=True
    "is_late_delivery": True,            # delivery_variance_hours > 0
    "late_delivery_type": "seller",      # "seller" nếu có late handoff, "logistics" nếu không
}
```

> [!IMPORTANT]
> **Công thức quan trọng** (round 2 chữ số):
> ```python
> from datetime import datetime
> def hours_diff(dt1_str, dt2_str):
>     """(dt1 - dt2) in hours"""
>     dt1 = datetime.strptime(dt1_str, "%Y-%m-%d %H:%M:%S")
>     dt2 = datetime.strptime(dt2_str, "%Y-%m-%d %H:%M:%S")
>     return round((dt1 - dt2).total_seconds() / 3600, 2)
> ```
> - `delivery_variance = delivered_customer_date - estimated_delivery_date`
> - `handoff_variance = delivered_carrier_date - shipping_limit_date` (sớm nhất của seller)
> - Nếu timestamp nào là None → variance cũng None, is_late = False

---

### 📋 Prompt gợi ý cho agent coding (Người 2):

```
Implement process() cho PaymentAgent trong file codebase/agents/payment_agent.py
và DeliveryAgent trong file codebase/agents/delivery_agent.py.

Đọc kỹ README.md Section 4 (Quy tắc nghiệp vụ) về công thức tính.
Đọc codebase/data_access.py để biết methods có sẵn.

Quy tắc:
- Tất cả số tiền và giờ round 2 chữ số thập phân
- Nếu order không có items → các trường liên quan đến items phải là null
- Nếu timestamp null → variance null, is_late = False
- Payment: reconciled = abs(difference_brl) <= 0.10
- Delivery: handoff_variance tính theo shipping_limit_date SỚM NHẤT của mỗi seller
- Không dùng LLM, chỉ dùng self.data + tính toán
```

---

## 👤 Người 3 — Policy Agent

**Files cần sửa:**
- `codebase/agents/policy_agent.py`

**Độ khó**: ⭐⭐⭐⭐ (Khó nhất — cần hiểu rõ toàn bộ business rules)
**Phụ thuộc**: Cần kết quả từ tất cả 4 agent khác (qua context).

### Policy Agent — Implement `process()`

**Input từ context:**
```python
order_data = context["order_data"]               # dict: order_status, ...
customer_result = context["customer_result"]     # từ CustomerAgent
order_product_result = context["order_product_result"]  # từ OrderProductAgent
payment_result = context["payment_result"]       # từ PaymentAgent
delivery_result = context["delivery_result"]     # từ DeliveryAgent
order_id = context["order_id"]
```

**Output phải trả về:**
```python
{
    "primary_issue": "late_delivery_seller",
    "secondary_issues": ["multi_item_order", "split_payment"],
    "case_status": "action_required",   # "action_required" nếu refund > 0, else "no_action"
    "confidence": 0.95,
    "root_cause_code": "SELLER_HANDOFF_AFTER_LIMIT",
    "responsible_parties": [{"party_type": "seller", "party_id": "seller_abc"}],
    "recommended_refund_brl": 18.27,
    "resolution_actions": ["refund_freight", "review_seller_handoff", "verify_payment_allocation"],
    "evidence_ids": ["order:xxx", "item:xxx:1", "payment:xxx:1", "seller:abc", "policy:SELLER_HANDOFF_AFTER_LIMIT"],
}
```

**Logic chi tiết — Primary Issue (theo thứ tự ưu tiên):**

| # | Issue | Điều kiện | Refund | Root cause |
|---|-------|-----------|--------|-----------|
| 1 | `canceled_order_paid` | `order_status == "canceled"` AND `payment_total > 0` | `payment_total` | `ORDER_CANCELED_AFTER_PAYMENT` |
| 2 | `unavailable_order_paid` | `order_status == "unavailable"` AND `payment_total > 0` | `payment_total` | `ORDER_UNAVAILABLE_AFTER_PAYMENT` |
| 3 | `late_delivery_seller` | `is_late_delivery` AND `len(late_handoff_seller_ids) > 0` | `freight_total` | `SELLER_HANDOFF_AFTER_LIMIT` |
| 4 | `late_delivery_logistics` | `is_late_delivery` AND `len(late_handoff_seller_ids) == 0` | `freight_total` | `CARRIER_DELIVERED_AFTER_ESTIMATE` |
| 5 | `valid_split_payment` | `is_split_payment` AND `reconciled == True` | `0` | `MULTIPLE_PAYMENTS_RECONCILED` |
| 6 | `unsupported_late_claim` | không late AND `reconciled` | `0` | `DELIVERY_WITHIN_ESTIMATE` |

**Secondary Issues (theo đúng thứ tự):**
1. `multi_item_order` ← `order_product_result["is_multi_item"]`
2. `multi_seller_order` ← `order_product_result["is_multi_seller"]`
3. `split_payment` ← `payment_result["is_split_payment"]`
4. `repeat_customer` ← `customer_result["is_repeat_customer"]`
5. `multiple_categories` ← `order_product_result["is_multiple_categories"]`

**Resolution Actions (theo thứ tự, sau action chính):**
- Action chính: `issue_full_refund` / `refund_freight` / `explain_valid_split_payment` / `reject_late_refund`
- Thêm: `review_seller_handoff` (nếu late seller) hoặc `review_carrier_delay` (nếu late logistics)
- Thêm: `verify_refund_completion` (nếu có refund)
- Thêm: `coordinate_multi_seller_case` (nếu multi_seller)
- Thêm: `verify_payment_allocation` (nếu split_payment **VÀ** primary issue **KHÔNG** phải `valid_split_payment`)

**Evidence IDs — build từ data:**
```python
evidence = [f"order:{order_id}"]
evidence += [f"item:{order_id}:{item['order_item_id']}" for item in items]
evidence += [f"payment:{order_id}:{p['payment_sequential']}" for p in payments]
if responsible sellers: evidence += [f"seller:{sid}" for sid in seller_ids]
evidence.append(f"policy:{root_cause_code}")
# Tối đa 20 evidence
```

---

### 📋 Prompt gợi ý cho agent coding (Người 3):

```
Implement process() cho PolicyAgent trong file codebase/agents/policy_agent.py.

Đọc kỹ README.md Section 4 (Quy tắc nghiệp vụ) — đây là logic chính.
File này KHÔNG cần gọi self.data hoặc self.llm — tất cả dữ liệu đến từ context.

Context chứa kết quả từ 4 agent khác:
- context["order_data"]: dict order
- context["customer_result"]: có is_repeat_customer, related_order_ids
- context["order_product_result"]: có items, is_multi_item, is_multi_seller, is_multiple_categories, affected_*
- context["payment_result"]: có payment_total_brl, freight_total_brl, reconciled, is_split_payment, payment_rows
- context["delivery_result"]: có is_late_delivery, late_handoff_seller_ids, late_delivery_type

Quy tắc:
- Check primary issue theo THỨ TỰ ƯU TIÊN, dừng lại ở issue đầu tiên match
- Secondary issues theo đúng thứ tự trong README
- Resolution actions theo đúng thứ tự trong README
- Evidence IDs phải match format: order:X, item:X:Y, payment:X:Y, seller:X, policy:X
- confidence = 0.95 nếu có đủ data, giảm nếu thiếu
- case_status = "action_required" nếu refund > 0, "no_action" nếu refund = 0
- Tối đa: 3 root causes, 3 responsible parties, 20 evidence, 5 actions
```

---

## 👤 Người 4 (Team Lead) — Coordinator Agent + Integration + Test

**Files cần sửa:**
- `codebase/agents/coordinator_agent.py` — `_assemble_output()` + `_build_empty_output()`
- `codebase/runner.py` — fix nếu cần
- `codebase/config.py` — cấu hình model thật

**Độ khó**: ⭐⭐⭐ (Integration, cần merge và test toàn bộ)
**Phụ thuộc**: Cần tất cả 3 người kia hoàn thành trước.

### Coordinator — Implement `_assemble_output()` và `_build_empty_output()`

**Logic `_assemble_output(case_id, ctx)`:**

Map kết quả từ các agent vào đúng output schema (xem `codebase/models.py`):

```python
from models import CaseOutput, CaseAssessment, AffectedEntities, CustomerContext, ...

output = CaseOutput(
    case_id=case_id,
    case_assessment=CaseAssessment(
        primary_issue=ctx["policy_result"]["primary_issue"],
        secondary_issues=ctx["policy_result"]["secondary_issues"],
        case_status=ctx["policy_result"]["case_status"],
        confidence=ctx["policy_result"]["confidence"],
    ),
    affected_entities=AffectedEntities(
        order_ids=[ctx["order_id"]],
        item_ids=ctx["order_product_result"]["affected_item_ids"],
        seller_ids=ctx["order_product_result"]["affected_seller_ids"],
        payment_ids=ctx["payment_result"]["affected_payment_ids"],
    ),
    customer_context=CustomerContext(...),
    product_context=ProductContext(...),
    delivery_analysis=DeliveryAnalysis(...),
    payment_reconciliation=PaymentReconciliation(...),
    root_cause_analysis=RootCauseAnalysis(...),
    evidence_ids=ctx["policy_result"]["evidence_ids"],
    financial_resolution=FinancialResolution(...),
    resolution_actions=ctx["policy_result"]["resolution_actions"],
)
return output.to_output_dict()
```

### Nhiệm vụ Integration:
1. Cấu hình `config.py` với model ≤ 10B thật (nếu agent nào cần LLM)
2. Merge code từ 3 người kia
3. Chạy test: `python runner.py EC_001` → kiểm tra output JSON
4. Chạy full: `python runner.py` → xử lý 50 cases
5. Kiểm tra `output/` có đủ 50 file JSON
6. Kiểm tra `trace.jsonl` và `metadata.json` được tạo
7. Viết `individual_5SoCuoiMHV_HoVaTen.md` cho bản thân

---

### 📋 Prompt gợi ý cho agent coding (Người 4):

```
Implement _assemble_output() và _build_empty_output() trong
codebase/agents/coordinator_agent.py.

Đọc codebase/models.py để biết các Pydantic model (CaseOutput, CaseAssessment, etc.)
Đọc README.md Section 6 để biết output schema chính xác.

_assemble_output(case_id, ctx):
- ctx chứa: order_id, order_data, customer_result, order_product_result,
  payment_result, delivery_result, policy_result
- Map từng field vào CaseOutput model
- Return output.to_output_dict()

_build_empty_output(case_id, order_id):
- Return CaseOutput với case_id, tất cả field khác là None hoặc empty list
- Dùng cho trường hợp order không tìm thấy

Giới hạn output schema:
- Tối đa 5 order_ids, 5 item_ids, 3 seller_ids, 5 payment_ids
- Tối đa 5 related_order_ids, 5 product_ids, 5 categories
- Tối đa 3 ranked_causes, 3 responsible_parties, 20 evidence_ids, 5 actions
```

---

## ⏱️ Timeline Gợi Ý

| Thời gian | Milestone |
|-----------|-----------|
| 13h30 - 14h30 | **Người 1, 2, 3** code song song. Người 4 chuẩn bị coordinator + test |
| 14h30 - 15h00 | Người 1 xong → push. Người 2 có thể test với items thật |
| 15h00 - 15h30 | Người 2, 3 xong → push |
| 15h30 - 16h30 | **Người 4** merge + integration test + fix bugs |
| 16h30 - 17h00 | Chạy full 50 cases, kiểm tra output |
| 17h00 - 17h30 | Buffer — fix edge cases, viết báo cáo cá nhân |

---

## 🔗 Files tham khảo quan trọng

| File | Mục đích |
|------|----------|
| `README.md` | Đề bài + business rules + output schema |
| `codebase/data_access.py` | Tất cả query methods có sẵn |
| `codebase/models.py` | Pydantic output models |
| `codebase/agents/base_agent.py` | Base class (kế thừa) |
| `architecture.md` | Sơ đồ kiến trúc |
