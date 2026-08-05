"""Calculation Tools Module for Multi-Agent System.

This module provides explicit, deterministic calculation tools used by the agents:
- PaymentReconciliationTool: computes monetary sums, expected total, difference, and reconciliation status.
- DeliveryTimingTool: computes timestamp variances, seller handoff deadlines, and late delivery flags.
- PolicyEnforcementTool: evaluates EC_POLICY_V2 primary/secondary issues, refunds, evidence IDs, and actions.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
SECONDS_PER_HOUR = 3600.0
RECONCILE_TOLERANCE_BRL = 0.10


def coerce_float(value: Any) -> Optional[float]:
    """Coerce a cell value to float, treating missing/NaN as None."""
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return None if num != num else num


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse a CSV timestamp string into datetime."""
    if value is None or not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in ("nan", "nat", "none"):
        return None
    try:
        return datetime.strptime(text, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def format_timestamp(value: Any) -> Optional[str]:
    """Format a timestamp into standard YYYY-MM-DD HH:MM:SS format."""
    if isinstance(value, datetime):
        return value.strftime(TIMESTAMP_FORMAT)
    dt = parse_timestamp(value)
    return dt.strftime(TIMESTAMP_FORMAT) if dt else None


def calculate_variance_hours(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[float]:
    """Calculate hours difference rounded to 2 decimal places."""
    if later is None or earlier is None:
        return None
    return round((later - earlier).total_seconds() / SECONDS_PER_HOUR, 2)


class PaymentReconciliationTool:
    """Deterministic calculation tool for payment reconciliation."""

    @staticmethod
    def compute(items: List[Dict[str, Any]], payment_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        sorted_payments = sorted(
            payment_rows or [],
            key=lambda r: coerce_float(r.get("payment_sequential")) or 0.0,
        )

        payment_total_brl = round(
            sum(coerce_float(row.get("payment_value")) or 0.0 for row in sorted_payments), 2
        )

        if items:
            item_total_brl = round(
                sum(coerce_float(item.get("price")) or 0.0 for item in items), 2
            )
            freight_total_brl = round(
                sum(coerce_float(item.get("freight_value")) or 0.0 for item in items), 2
            )
            expected_total_brl = round(item_total_brl + freight_total_brl, 2)
            difference_brl = round(payment_total_brl - expected_total_brl, 2)
            reconciled = abs(difference_brl) <= RECONCILE_TOLERANCE_BRL
        else:
            item_total_brl = 0.0
            freight_total_brl = 0.0
            expected_total_brl = None
            difference_brl = None
            reconciled = None

        payment_types = []
        for row in sorted_payments:
            ptype = row.get("payment_type")
            if ptype and ptype not in payment_types:
                payment_types.append(ptype)

        affected_payment_ids = []
        for row in sorted_payments:
            seq = coerce_float(row.get("payment_sequential"))
            if seq is not None:
                affected_payment_ids.append(f"{seq}")

        return {
            "payment_rows": sorted_payments,
            "item_total_brl": item_total_brl,
            "freight_total_brl": freight_total_brl,
            "expected_total_brl": expected_total_brl,
            "payment_total_brl": payment_total_brl,
            "difference_brl": difference_brl,
            "reconciled": reconciled,
            "payment_types": payment_types,
            "is_split_payment": len(sorted_payments) >= 2,
        }


class DeliveryTimingTool:
    """Deterministic calculation tool for delivery timing and handoff analysis."""

    @staticmethod
    def compute(order_data: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
        delivered_raw = order_data.get("order_delivered_customer_date")
        estimated_raw = order_data.get("order_estimated_delivery_date")
        handoff_raw = order_data.get("order_delivered_carrier_date")

        delivered_at_dt = parse_timestamp(delivered_raw)
        estimated_at_dt = parse_timestamp(estimated_raw)
        handoff_at_dt = parse_timestamp(handoff_raw)

        delivery_variance_hours = calculate_variance_hours(delivered_at_dt, estimated_at_dt)
        is_late_delivery = delivery_variance_hours is not None and delivery_variance_hours > 0

        earliest_limit_by_seller: Dict[str, datetime] = {}
        seller_order: list = []
        for item in (items or []):
            seller_id = item.get("seller_id")
            if not seller_id:
                continue
            if seller_id not in seller_order:
                seller_order.append(seller_id)
            limit_dt = parse_timestamp(item.get("shipping_limit_date"))
            if limit_dt is None:
                continue
            current = earliest_limit_by_seller.get(seller_id)
            if current is None or limit_dt < current:
                earliest_limit_by_seller[seller_id] = limit_dt

        seller_handoff_analysis = []
        late_handoff_seller_ids = []
        for seller_id in seller_order:
            limit_dt = earliest_limit_by_seller.get(seller_id)
            handoff_variance = calculate_variance_hours(handoff_at_dt, limit_dt)
            late_handoff = handoff_variance is not None and handoff_variance > 0
            seller_handoff_analysis.append({
                "seller_id": seller_id,
                "shipping_limit_at": format_timestamp(limit_dt.strftime(TIMESTAMP_FORMAT) if limit_dt else None),
                "handoff_variance_hours": handoff_variance,
                "late_handoff": late_handoff,
            })
            if late_handoff:
                late_handoff_seller_ids.append(seller_id)

        if is_late_delivery:
            late_delivery_type = "seller" if late_handoff_seller_ids else "logistics"
        else:
            late_delivery_type = None

        return {
            "delivered_at": format_timestamp(delivered_raw),
            "estimated_delivery_at": format_timestamp(estimated_raw),
            "carrier_handoff_at": format_timestamp(handoff_raw),
            "delivery_variance_hours": delivery_variance_hours,
            "seller_handoff_analysis": seller_handoff_analysis,
            "late_handoff_seller_ids": late_handoff_seller_ids,
            "is_late_delivery": is_late_delivery,
            "late_delivery_type": late_delivery_type,
        }
