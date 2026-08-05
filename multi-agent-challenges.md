# Thách thức cho hệ multi-agent — soi từ kết quả pandas trên đúng 50 ticket K4

> **Cập nhật sau khi rà lại từng ticket một** (theo yêu cầu "chạy từng input một, tìm ra cái gì bị thiếu"): mục 0 dưới đây là phát hiện chính — một "bẫy" cụ thể, có chủ đích, nằm trên đúng 5/50 ticket. Các mục 1–7 giữ nguyên từ lần soát đầu.

> Phạm vi: chỉ bàn về 50 ticket `EC_001`–`EC_050` thật trong `K4-Day9-Multi-Agent-A2A/input/`, đối chiếu với `data/*.csv` thật. Không suy rộng ra trường hợp tổng quát ngoài bộ dữ liệu này.
>
> Cách làm: viết một script pandas duy nhất (`run_ec_policy.py`, không dựng agent nào) áp `EC_POLICY_V2` (README K4 mục 4–6) lên cả 50 order thật, ghi 50 file kết quả vào `K4-Day9-Multi-Agent-A2A/output/EC_*.json`, đúng schema và giới hạn mảng. Các con số dưới đây lấy trực tiếp từ kết quả chạy đó.

## Kết quả tổng quan

| primary_issue | Số ticket |
|---|---:|
| `late_delivery_seller` | 10 |
| `late_delivery_logistics` | 10 |
| `unsupported_late_claim` | 8 |
| `canceled_order_paid` | 8 |
| `valid_split_payment` | 8 |
| `unavailable_order_paid` | 6 |

50/50 order groundable, 0 ticket rơi ngoài 6 nhánh, tất cả 50 file output pass kiểm tra giới hạn mảng (order ≤5, item ≤5, seller ≤3, payment ≤5, related_order ≤5, product ≤5, category ≤5, root_cause ≤3, responsible_party ≤3, evidence ≤20, action ≤5) và `confidence ∈ [0,1]`.

Vì bài toán này **giải được gọn bằng một script tính toán thuần** (không cần suy luận ngôn ngữ tự nhiên, không cần "quyết định" mơ hồ — mọi nhánh đều là điều kiện số/enum rạch ròi trên dữ liệu CSV), thách thức thật sự của một **hệ multi-agent** (nhiều agent LLM handoff cho nhau) trên đúng bộ input này không nằm ở "suy luận đúng sai" mà nằm ở việc **một chuỗi agent có tái tạo đúng logic tất định này qua nhiều bước giao tiếp hay không**. Dưới đây là các điểm cụ thể mà bộ 50 ticket này phơi ra.

## 0. Bẫy có chủ đích: 5 ticket vừa "giao trễ" vừa "trông giống split-payment hợp lệ" — chỉ đúng thứ tự ưu tiên mới cứu được

Đây là phát hiện quan trọng nhất sau khi rà từng ticket một (thay vì chỉ nhìn thống kê tổng).

**Cách tìm ra**: với mỗi ticket thuộc `late_delivery_seller`/`late_delivery_logistics`, kiểm tra thêm xem nó có *đồng thời* thỏa điều kiện của `valid_split_payment` hay không (≥2 payment row, `reconciled = true`). Nếu một hệ thống kiểm tra "split payment" **trước** "giao trễ" (thay vì đúng thứ tự ưu tiên README mục 4: `late_delivery_seller` → `late_delivery_logistics` → ... → `valid_split_payment`), nó sẽ chốt nhầm nhánh.

Kết quả: **5/50 ticket (10%) rơi đúng vào bẫy này**:

| case_id | primary_issue đúng | Số payment row | Sai lệch handoff của seller (giờ) |
|---|---|---:|---:|
| `EC_002` | `late_delivery_seller` | 2 | **+1.04h** (seller trễ deadline hãng vận chuyển đúng ~1 tiếng) |
| `EC_013` | `late_delivery_seller` | 2 | **+2.34h** |
| `EC_016` | `late_delivery_logistics` | 3 | **−4.19h** (seller giao đúng hạn, chỉ trễ 4h nếu tính ngược) |
| `EC_042` | `late_delivery_seller` | 3 | +416.68h (biên rộng, không phải trap về giờ) |
| `EC_046` | `late_delivery_seller` | 2 | **+17.56h** |

Cả 5 ticket này đều có `payment_reconciliation.reconciled = true` (payment khớp tuyệt đối với item+freight, sai số 0.00 BRL) và ≥2 payment row — tức là nếu chỉ nhìn riêng phần thanh toán, chúng **trông y hệt** một `valid_split_payment` hoàn hảo. Chỉ có việc kiểm tra "đơn có giao trễ hay không" **trước** mới lộ ra bản chất thật là `late_delivery_seller`/`late_delivery_logistics`. Một Policy Agent lập luận bằng văn xuôi kiểu "hai payment cộng lại vừa khớp tổng đơn → split payment hợp lệ" (đúng nhưng chưa đủ, vì chưa check delivery trước) sẽ sai đúng 5 ticket này — bằng đúng 10% điểm số bài, vì mỗi ticket là một đơn vị chấm độc lập.

**Lồng bên trong bẫy đó còn có một bẫy thứ hai, tinh vi hơn**: với `EC_002`, `EC_013`, `EC_016`, `EC_046`, biên độ giữa "seller giao trễ" và "seller giao đúng hạn" chỉ lệch **1–18 giờ** — trong khi độ trễ giao hàng tổng thể (`delivery_variance_hours`) của toàn bộ 20 ticket `late_delivery_*` không bao giờ nhỏ hơn ~68 giờ (xem mục 2 cũ, đã đổi số). Nói cách khác: **tầng quyết định "đơn có trễ không" rất dễ, nhưng tầng quyết định "ai chịu trách nhiệm — seller hay logistics" lại cực sát biên**, đúng trên 4 trong 5 ticket của bẫy trên. Bất kỳ sai lệch nhỏ nào trong cách tính giờ — làm tròn về ngày thay vì giữ giờ:phút:giây, lệch múi giờ dù chỉ 1 tiếng, hoặc lấy nhầm `order_delivered_carrier_date` của *đơn* thay vì so với `shipping_limit_date` của *đúng seller* — đều đủ để lật dấu (+/−) và đổi cả `primary_issue`, `responsible_parties`, `root_cause_analysis`, `financial_resolution`, `evidence_ids` của ticket đó (tức đa số các cụm điểm 15% trong bảng chấm).

Đã kiểm chứng thêm để loại trừ các khả năng gây nhiễu: seller trong 5 ticket này chỉ có đúng 1 `shipping_limit_date` cho mọi item của họ (không có chuyện min/max shipping_limit_date của seller mâu thuẫn nhau), và không có ticket nào trong 45 ticket còn lại có seller "giao trễ handoff" (`late_handoff=true`) mà đơn tổng thể lại không trễ — nghĩa là bẫy này **chỉ và đúng** nằm ở việc thứ tự ưu tiên `late_delivery_*` phải được kiểm tra trước `valid_split_payment`, không có yếu tố nhiễu nào khác trộn vào.

## 1. `customer_request.message` giống hệt nhau ở cả 50 ticket → Coordinator không có tín hiệu định tuyến

Cả 50 file đều có cùng một câu: *"Hãy điều tra khiếu nại, kiểm tra lịch sử khách hàng và đối soát toàn bộ order."* Không có ticket nào gợi ý "giao trễ", "hủy đơn", "hàng không có sẵn"... Hệ quả với multi-agent thật:

- Agent điều phối (Coordinator) **không thể dùng NLU trên message để route** ticket cho agent chuyên trách phù hợp — nó buộc phải gọi *toàn bộ* agent con (Order/Payment/Delivery/Customer/Product) cho mọi ticket, không có đường tắt.
- Vì input không tự mâu thuẫn với kết luận sai, **agent không có tín hiệu nào từ chính ticket để tự phát hiện nó đã suy luận sai** — sai sót chỉ lộ ra khi đối chiếu với CSV, tức là hoàn toàn phụ thuộc vào Verifier có join đúng key hay không.

## 2. Dung sai đối soát 0.10 BRL và ngưỡng "giao trễ" không hề bị bộ dữ liệu này thử thách

Chạy `difference_brl = payment_total − (item_total + freight_total)` trên toàn bộ 44 order có item row: **tất cả đều bằng đúng 0.00 BRL** — không có ticket nào lệch 0.01–0.10 BRL để thực sự cần đến dung sai `<= 0.10`. Tương tự, `delivery_variance_hours` (giao thật so với ngày ước tính) trải từ **−673.72h đến +547.94h**, không có ticket nào nằm sát mốc 0 (borderline).

→ Một pipeline multi-agent (hoặc một Policy Agent dùng LLM để so sánh số) **có thể lượng giá sai ngưỡng dung sai hoặc dấu bất đẳng thức** (vd. dùng `<` thay vì `<=`, hoặc quên dung sai 0.10 mà so bằng tuyệt đối) và **vẫn ra đúng 50/50 kết quả trên chính bộ input này**, vì không ticket nào chạm biên. Nghĩa là: batch 50 ticket không phải là bộ test đủ để phát hiện lỗi ở đúng chỗ dễ sai nhất của policy (xử lý dung sai/ngưỡng).

## 3. 6 order `unavailable` trùng khớp 100% với "không có item row nào" — dễ làm agent suy luận nhầm quan hệ nhân quả

Cả 6 ticket có `order_status = unavailable` (EC_012, EC_031, EC_033, EC_034, EC_035, EC_043) đều có **0 dòng trong `order_items`**. Đây là đặc điểm riêng của batch 50 ticket này, không phải quy tắc chung trong `EC_POLICY_V2` (policy chỉ nói "order không có item row" là một case null-handling độc lập, không gắn với `unavailable`).

→ Rủi ro cụ thể: nếu Order/Product Agent hoặc Policy Agent "học" từ vài ticket đầu rằng *thiếu item ⇒ chắc là unavailable* rồi dùng heuristic đó thay vì đọc đúng `order_status`, nó vẫn khớp đáp án trên cả 6 ticket này — sai lệch chỉ lộ nếu có thêm ticket "unavailable nhưng có item" hoặc "delivered/canceled nhưng thiếu item", mà bộ 50 ticket hiện tại **không có** case nào như vậy để bắt lỗi này.

## 4. EC_047 — order `canceled` nhưng đã có `order_delivered_carrier_date` (đã giao cho hãng vận chuyển)

7/8 order `canceled` có cả `order_delivered_carrier_date` lẫn `order_delivered_customer_date` đều null (chưa từng rời kho). Riêng **EC_047** (`order_id 2cfc79d9582e9135c0a9b61fa60e6b21`) có `order_delivered_carrier_date` **không null** — seller đã bàn giao cho carrier — nhưng đơn vẫn bị hủy trước khi tới tay khách (`order_delivered_customer_date` null).

→ Đây là ticket duy nhất trong 50 ticket mà tín hiệu "đã có hoạt động giao hàng" và "trạng thái đơn" mâu thuẫn nhau. Một Delivery Agent nếu suy luận trạng thái case từ *có carrier_handoff_date hay không* (thay vì đọc thẳng `order_status = canceled` theo đúng policy) sẽ dễ misclassify đúng ticket này thành `late_delivery_*` thay vì `canceled_order_paid`. Grounding nghiêm ngặt vào field `order_status` — như yêu cầu ở mục 4 `lab-k4-summary.md` ("chỉ kết luận khi có evidence ID thật") — là điều duy nhất tránh được lỗi này trên bộ input hiện tại.

## 4b. EC_021 — `order_delivered_carrier_date` đứng *trước* `order_approved_at`

Soát ràng buộc thứ tự thời gian (`purchase ≤ approved ≤ carrier ≤ customer`) trên cả 50 order thật lộ ra đúng 1 vi phạm: **EC_021** (`order_id cc8778d76e567b45082b7f52bce23095`) có `order_delivered_carrier_date = 2018-04-23 18:22:46`, tức là **sớm hơn** `order_approved_at = 2018-04-24 19:24:18` hơn 25 giờ — seller đã giao hàng cho hãng vận chuyển trước khi Olist xác nhận thanh toán xong (một đặc điểm có thật của dataset Olist, thường do độ trễ xác nhận boleto). Đây là dị thường duy nhất trong 50 ticket; mọi mốc thời gian khác đều theo đúng thứ tự.

→ `order_approved_at` **không xuất hiện ở bất kỳ công thức hay field nào** trong schema/`EC_POLICY_V2` (mục 4 README), nên dị thường này *không* ảnh hưởng tới kết quả đúng của EC_021 (vẫn là `unsupported_late_claim`, biên rất rộng −673.72h). Rủi ro chỉ nảy sinh nếu một agent tự thêm bước "sanity check" ngoài policy (vd. "nếu carrier_date trước approved_at thì dữ liệu bất thường, đánh dấu cần điều tra thêm") — đúng thứ mà mục 4 `lab-k4-summary.md` cấm ("không tự tạo ra fact mới", chỉ dùng đúng field policy yêu cầu). EC_021 là ticket kiểm chứng trực tiếp cho việc agent có tuân thủ giới hạn phạm vi field hay không.

## 5. Tổ hợp `late_delivery_seller` + `multi_seller_order` không xuất hiện — một nhánh action-ordering không được bộ test này phủ

Toàn bộ 10 ticket `late_delivery_seller` chỉ có **đúng 1 seller** (`n_sellers = 1`). README K4 quy định action bổ sung theo thứ tự cố định: `review_seller_handoff` → `verify_refund_completion` → `coordinate_multi_seller_case` → `verify_payment_allocation`, tức là về lý thuyết một ticket vừa `late_delivery_seller` vừa `multi_seller_order` phải có **cả 4 action phụ cùng lúc** (tổng 5 action kể cả action chính — chạm đúng giới hạn tối đa).

→ Vì tổ hợp này **không xuất hiện trong 50 ticket thật**, một Policy Agent cài sai thứ tự hoặc bỏ sót action trong đúng tổ hợp đó vẫn "qua" toàn bộ batch. Đây là khoảng trống review cần lưu ý riêng khi tự kiểm (mục 5 `lab-k4-summary.md`), vì "chạy đúng 50/50 trên input đề" không đồng nghĩa "logic action-ordering đã đúng" — chỉ đồng nghĩa "chưa bị lộ trên input đề".

## 6. `related_order_ids`/`repeat_customer` phụ thuộc join `customer_id → customer_unique_id → customer_id khác`, không có gì trong ticket để chéo kiểm

26/50 ticket có khách hàng từng có order khác (`repeat_customer`), nhiều nhất tới vài related order. Vì `investigation_scope.include_customer_history = true` ở **mọi** ticket (không có ticket nào tắt cờ này để so sánh hành vi), Customer Agent bắt buộc chạy join hai bước (`orders.customer_id → customers.customer_unique_id`, rồi `customer_unique_id → mọi customer_id khác → orders`) trên **toàn bộ 96,096 `customer_unique_id`** cho cả 50 ticket, không có ticket nào cho phép bỏ qua bước này.

→ Nếu một agent nhầm lẫn `customer_id` (định danh theo từng order) với `customer_unique_id` (định danh khách hàng xuyên order) — lỗi rất dễ mắc vì hai cột tên gần giống nhau — nó sẽ luôn trả `related_order_ids = []` cho mọi ticket (vì mỗi `customer_id` chỉ gắn với đúng 1 order). Với message ticket không nói gì về lịch sử khách hàng, **không có tín hiệu nào trong input để agent tự nghi ngờ** kết quả rỗng đó là sai — chỉ lộ ra khi so với số liệu 26/50 đã biết trước.

## 7. `payment_types` phải giữ đúng thứ tự nguồn, không phải thứ tự "tự nhiên" của agent tổng hợp

13/50 ticket có ≥2 payment row (vd. `credit_card` + `voucher`). Schema yêu cầu "array phải giữ thứ tự ổn định theo dữ liệu nguồn" — tức thứ tự phải theo `payment_sequential` tăng dần trong CSV, không phải thứ tự agent liệt kê ra khi tổng hợp câu trả lời bằng ngôn ngữ tự nhiên. Một Payment Agent trả lời qua LLM (thay vì đọc thẳng DataFrame đã sort) có xu hướng liệt kê theo trọng số câu chữ ("khách trả chủ yếu bằng thẻ, có thêm voucher") chứ không đảm bảo khớp `payment_sequential` — đây là một lỗi format nhỏ nhưng cụ thể mà batch 50 ticket này (13 ticket multi-payment) đủ để phơi ra nếu không ép agent đọc field gốc thay vì diễn giải.

## Kết luận

Với đúng 50 ticket đề bài, phần "ra quyết định đúng" hoàn toàn giải được bằng một lượt tính pandas tất định (đã chạy, 50/50 khớp policy, xem `K4-Day9-Multi-Agent-A2A/output/`). Thách thức thật của một **hệ multi-agent** trên chính bộ input này nằm ở việc mỗi agent (Customer/Order/Payment/Delivery/Policy/Verifier) phải **tự tái lập đúng từng join và từng điều kiện số ở trên qua handoff bằng ngôn ngữ**, trong khi:

- **Bẫy rõ nhất, có chủ đích**: 5/50 ticket (10%) vừa trông giống `valid_split_payment` (payment khớp tuyệt đối, ≥2 payment row) vừa thực chất là `late_delivery_*` — chỉ đúng thứ tự ưu tiên `EC_POLICY_V2` mới phân biệt được (mục 0). Trong đó 4 ticket còn có biên seller-handoff chỉ lệch 1–18 giờ, tương phản hẳn với phần còn lại của batch (biên luôn ≥68h) — tức là đề bài cố tình đặt đúng những ticket khó nhất ở tầng "ai chịu trách nhiệm" thay vì tầng "có trễ hay không".
- Input không có tín hiệu ngôn ngữ nào giúp agent tự phát hiện khi nó suy luận sai (mục 1, 6).
- Chính bộ 50 ticket này **không phủ hết mọi biên/tổ hợp** của policy (mục 2, 5) — nên "pass hết 50 ticket" không phải bằng chứng đầy đủ rằng agent đã cài đúng toàn bộ `EC_POLICY_V2`, chỉ là bằng chứng nó đúng trên đúng các tổ hợp có mặt trong đề.
- Có ít nhất hai ticket cụ thể mà suy luận theo tín hiệu gián tiếp (thay vì đọc đúng field policy yêu cầu) sẽ ra sai hoặc lạc đề: EC_047 — "canceled" nhưng đã có carrier_handoff (mục 4); EC_021 — carrier_handoff đứng trước approved_at, một dị thường dữ liệu thật nhưng nằm ngoài phạm vi field mà policy dùng (mục 4b).
