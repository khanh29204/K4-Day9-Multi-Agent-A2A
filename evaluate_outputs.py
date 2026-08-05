"""
Auto-Evaluator Script for Agent Builders.
Evaluates agent output JSON files in output/ directory against policy specifications
and provides subscore breakdowns (Primary/Secondary issues, Entities, Context, Delivery, Payment, Root cause, Financial).
"""

import os
import json
import glob

BASE_DIR = r"d:\Vin_AI\K4-Day9-Multi-Agent-A2A"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INPUT_DIR = os.path.join(BASE_DIR, "input")

WEIGHTS = {
    "issues": 0.15,
    "entities": 0.15,
    "context": 0.15,
    "delivery": 0.15,
    "payment": 0.15,
    "root_cause": 0.15,
    "financial": 0.10
}

def evaluate_case(case_id, pred):
    scores = {}
    
    # 1. Assessment (15%)
    assess = pred.get("case_assessment", {})
    scores["issues"] = 1.0 if assess.get("primary_issue") and isinstance(assess.get("secondary_issues"), list) else 0.0
    
    # 2. Affected entities (15%)
    entities = pred.get("affected_entities", {})
    scores["entities"] = 1.0 if entities.get("order_ids") and isinstance(entities.get("item_ids"), list) else 0.0
    
    # 3. Context (15%)
    cust_ctx = pred.get("customer_context", {})
    prod_ctx = pred.get("product_context", {})
    scores["context"] = 1.0 if cust_ctx.get("customer_unique_id") and isinstance(prod_ctx.get("product_ids"), list) else 0.0
    
    # 4. Delivery analysis (15%)
    deliv = pred.get("delivery_analysis", {})
    scores["delivery"] = 1.0 if "delivery_variance_hours" in deliv and isinstance(deliv.get("seller_handoff_analysis"), list) else 0.0
    
    # 5. Payment reconciliation (15%)
    pay = pred.get("payment_reconciliation", {})
    scores["payment"] = 1.0 if "payment_total_brl" in pay and "reconciled" in pay else 0.0
    
    # 6. Root cause and evidence (15%)
    rc = pred.get("root_cause_analysis", {})
    ev = pred.get("evidence_ids", [])
    scores["root_cause"] = 1.0 if isinstance(rc.get("ranked_causes"), list) and len(ev) > 0 else 0.0
    
    # 7. Financial resolution and actions (10%)
    fin = pred.get("financial_resolution", {})
    act = pred.get("resolution_actions", [])
    scores["financial"] = 1.0 if "recommended_refund_brl" in fin and len(act) > 0 else 0.0
    
    total_case_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return total_case_score, scores

def main():
    json_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "EC_*.json")))
    if not json_files:
        print(f"No JSON files found in output directory: {OUTPUT_DIR}")
        return

    total_score = 0.0
    category_scores = {k: 0.0 for k in WEIGHTS}
    valid_cases = 0

    print(f"Evaluating {len(json_files)} output cases in '{OUTPUT_DIR}'...\n")

    for filepath in json_files:
        case_id = os.path.basename(filepath).replace(".json", "")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                pred = json.load(f)
            c_score, sub_scores = evaluate_case(case_id, pred)
            total_score += c_score
            for k in WEIGHTS:
                category_scores[k] += sub_scores[k]
            valid_cases += 1
        except Exception as e:
            print(f"Error reading {case_id}: {e}")

    avg_total_score = (total_score / len(json_files)) * 100.0 if json_files else 0.0
    
    print("=" * 50)
    print("           AGENT OUTPUT EVALUATION SCORE           ")
    print("=" * 50)
    print(f"Total Cases Evaluated: {valid_cases} / 50")
    print(f"Overall Benchmark Score: {avg_total_score:.2f}% / 100.0%\n")
    print("Subscore Breakdown (Schema & Compliance Validity):")
    for k, w in WEIGHTS.items():
        sub_pct = (category_scores[k] / len(json_files)) * 100.0 if json_files else 0.0
        print(f"  - {k.capitalize():<12} (Weight {w*100:2.0f}%): {sub_pct:.2f}%")
    print("=" * 50)

if __name__ == "__main__":
    main()
