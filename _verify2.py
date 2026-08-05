"""Phase 2 audit: entities, evidence, actions, root cause, timestamps."""
import json, glob, os, collections, re
import pandas as pd
from datetime import datetime

B = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(B, "data")
orders = pd.read_csv(os.path.join(D, "olist_orders_dataset.csv"))
customers = pd.read_csv(os.path.join(D, "olist_customers_dataset.csv"))
items = pd.read_csv(os.path.join(D, "olist_order_items_dataset.csv"))
pays = pd.read_csv(os.path.join(D, "olist_order_payments_dataset.csv"))
products = pd.read_csv(os.path.join(D, "olist_products_dataset.csv"))
sellers = pd.read_csv(os.path.join(D, "olist_sellers_dataset.csv"))

valid_sellers = set(sellers.seller_id)
valid_products = set(products.product_id)
valid_orders = set(orders.order_id)
TSRE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
prob = collections.defaultdict(list)

LIMITS = {"order_ids":5,"item_ids":5,"seller_ids":3,"payment_ids":5}

for f in sorted(glob.glob(os.path.join(B,"input","EC_*.json"))):
    cid = os.path.basename(f).replace(".json","")
    oid = json.load(open(f,encoding="utf-8"))["customer_request"]["claimed_order_id"]
    out = json.load(open(os.path.join(B,"output",cid+".json"),encoding="utf-8"))
    it = items[items.order_id==oid].sort_values("order_item_id")
    pr = pays[pays.order_id==oid].sort_values("payment_sequential")

    ae = out["affected_entities"]
    # limits
    for k,lim in LIMITS.items():
        if len(ae[k])>lim: prob["limit_exceeded"].append((cid,k,len(ae[k])))
    if len(out["evidence_ids"])>20: prob["evidence>20"].append((cid,len(out["evidence_ids"])))
    if len(out["resolution_actions"])>5: prob["actions>5"].append((cid,))
    if len(out["customer_context"]["related_order_ids"])>5: prob["related>5"].append((cid,))
    if len(out["product_context"]["product_ids"])>5: prob["products>5"].append((cid,))
    if len(out["product_context"]["category_names"])>5: prob["cats>5"].append((cid,))

    # affected_entities.order_ids must be exactly the claimed order
    if ae["order_ids"]!=[oid]: prob["order_ids_not_claimed_only"].append((cid,ae["order_ids"]))
    # related must not contain claimed
    if oid in out["customer_context"]["related_order_ids"]: prob["claimed_in_related"].append((cid,))

    exp_items=[f"{oid}:{int(x)}" for x in it.order_item_id][:5]
    if ae["item_ids"]!=exp_items: prob["item_ids"].append((cid,exp_items,ae["item_ids"]))
    exp_pay=[f"{oid}:{int(x)}" for x in pr.payment_sequential][:5]
    if ae["payment_ids"]!=exp_pay: prob["payment_ids"].append((cid,exp_pay,ae["payment_ids"]))
    exp_sel=list(dict.fromkeys(it.seller_id.tolist()))[:3]
    if ae["seller_ids"]!=exp_sel: prob["seller_ids"].append((cid,exp_sel,ae["seller_ids"]))
    exp_prod=list(dict.fromkeys(it.product_id.tolist()))[:5]
    if out["product_context"]["product_ids"]!=exp_prod: prob["product_ids"].append((cid,))

    # evidence validity / format / false positives
    for e in out["evidence_ids"]:
        if e.startswith("order:"):
            if e[6:] not in valid_orders: prob["ev_bad_order"].append((cid,e))
        elif e.startswith("item:"):
            _,o2,seq=e.split(":")
            if o2!=oid or not seq.isdigit() or int(seq) not in set(int(x) for x in it.order_item_id):
                prob["ev_bad_item"].append((cid,e))
        elif e.startswith("payment:"):
            _,o2,seq=e.split(":")
            if o2!=oid or not seq.isdigit() or int(seq) not in set(int(x) for x in pr.payment_sequential):
                prob["ev_bad_payment"].append((cid,e))
        elif e.startswith("seller:"):
            if e[7:] not in valid_sellers: prob["ev_bad_seller"].append((cid,e))
        elif e.startswith("policy:"): pass
        else: prob["ev_unknown_prefix"].append((cid,e))
    if len(out["evidence_ids"])!=len(set(out["evidence_ids"])): prob["ev_dupes"].append((cid,))

    # seller in evidence must be a responsible party (trap #6)
    resp={p["party_id"] for p in out["root_cause_analysis"]["responsible_parties"] if p["party_type"]=="seller"}
    for e in out["evidence_ids"]:
        if e.startswith("seller:") and e[7:] not in resp: prob["ev_seller_not_responsible"].append((cid,e))

    # policy evidence must be present and match ranked cause
    rc=out["root_cause_analysis"]["ranked_causes"]
    codes=[c["cause_code"] for c in rc]
    if codes and f"policy:{codes[0]}" not in out["evidence_ids"]:
        prob["policy_evidence_missing"].append((cid,codes))
    if rc and [c["rank"] for c in rc]!=list(range(1,len(rc)+1)): prob["rank_bad"].append((cid,))

    # timestamps format
    da=out["delivery_analysis"]
    for k in ("delivered_at","estimated_delivery_at","carrier_handoff_at"):
        v=da[k]
        if v is not None and not TSRE.match(v): prob["ts_format"].append((cid,k,v))
    for sh in da["seller_handoff_analysis"]:
        if sh["shipping_limit_at"] is not None and not TSRE.match(sh["shipping_limit_at"]):
            prob["ts_format"].append((cid,"shipping_limit_at",sh["shipping_limit_at"]))

    # zero-item hard gate (trap #3)
    if len(it)==0:
        pay=out["payment_reconciliation"]
        for k in ("expected_total_brl","difference_brl","reconciled","item_total_brl","freight_total_brl"):
            if pay[k] is not None: prob["ZEROITEM_not_null"].append((cid,k,pay[k]))
        if ae["item_ids"] or ae["seller_ids"] or out["product_context"]["product_ids"] \
           or out["product_context"]["category_names"] or da["seller_handoff_analysis"]:
            prob["ZEROITEM_not_empty"].append((cid,))

    # case_status consistency
    refund=out["financial_resolution"]["recommended_refund_brl"]
    want="action_required" if refund and refund>0 else "no_action"
    if out["case_assessment"]["case_status"]!=want: prob["case_status"].append((cid,refund,out["case_assessment"]["case_status"]))

    # confidence range
    c=out["case_assessment"]["confidence"]
    if c is None or not (0<=c<=1): prob["confidence_range"].append((cid,c))

    # verify_payment_allocation exclusion (trap #9)
    acts=out["resolution_actions"]
    if out["case_assessment"]["primary_issue"]=="valid_split_payment" and "verify_payment_allocation" in acts:
        prob["vpa_on_valid_split"].append((cid,))
    if len(pr)>=2 and out["case_assessment"]["primary_issue"]!="valid_split_payment" and "verify_payment_allocation" not in acts:
        prob["vpa_missing"].append((cid,acts))

print("=== PHASE 2 ISSUES ===")
if not prob: print("  none")
for k,v in sorted(prob.items(), key=lambda x:-len(x[1])):
    print(f"  {k}: {len(v)}")
    for x in v[:5]: print("      ",x)
