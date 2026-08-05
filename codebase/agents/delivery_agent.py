"""Delivery Agent - Analyzes delivery timing and seller handoff.

Responsibilities:
- Calculate delivery_variance_hours
- Calculate handoff_variance_hours per seller
- Determine if delivery was late
- Determine which sellers had late handoff
- Identify responsible party for late delivery

Data access: orders (timestamps), order_items (shipping_limit_date)

Formulas:
  delivery_variance_hours = delivered_customer_date - estimated_delivery_date
  handoff_variance_hours = delivered_carrier_date - shipping_limit_date (earliest per seller)
"""
from datetime import datetime
from typing import Any, Dict, Optional
from .base_agent import BaseAgent

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
SECONDS_PER_HOUR = 3600.0


def _parse_ts(value: Any) -> Optional[datetime]:
    """Parse a CSV timestamp; missing/NaN/unparseable values become None."""
    if value is None or not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in ("nan", "nat"):
        return None
    try:
        return datetime.strptime(text, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def _clean_ts(value: Any) -> Optional[str]:
    """Normalize a timestamp for output, keeping the original CSV format."""
    return value.strftime(TIMESTAMP_FORMAT) if _parse_ts(value) else None


def _variance_hours(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[float]:
    """Hours between two timestamps, rounded to 2 decimals. None if either is missing."""
    if later is None or earlier is None:
        return None
    return round((later - earlier).total_seconds() / SECONDS_PER_HOUR, 2)


class DeliveryAgent(BaseAgent):
    def __init__(self, llm_client, data_access):
        super().__init__("delivery_agent", llm_client, data_access)

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze delivery timing.
        
        Expected context keys:
            - order_id: str
            - order_data: dict (order timestamps)
            - items: list of item dicts (shipping_limit_date per seller)
        
        Returns:
            - delivered_at: str or None
            - estimated_delivery_at: str or None
            - carrier_handoff_at: str or None
            - delivery_variance_hours: float or None
            - seller_handoff_analysis: list of dicts
            - late_handoff_seller_ids: list[str]
            - is_late_delivery: bool
            - late_delivery_type: str or None ("seller" or "logistics")
        """
        order_id = context["order_id"]
        order_data = context.get("order_data") or {}
        items = context.get("items") or []

        delivered_raw = order_data.get("order_delivered_customer_date")
        estimated_raw = order_data.get("order_estimated_delivery_date")
        handoff_raw = order_data.get("order_delivered_carrier_date")

        delivered_at_dt = _parse_ts(delivered_raw)
        estimated_at_dt = _parse_ts(estimated_raw)
        handoff_at_dt = _parse_ts(handoff_raw)

        delivery_variance_hours = _variance_hours(delivered_at_dt, estimated_at_dt)
        # A missing timestamp means we cannot prove lateness, so it is not late.
        is_late_delivery = delivery_variance_hours is not None and delivery_variance_hours > 0

        # Each seller is judged against its EARLIEST shipping_limit_date across the order's items.
        earliest_limit_by_seller: Dict[str, datetime] = {}
        seller_order: list = []
        for item in items:
            seller_id = item.get("seller_id")
            if not seller_id:
                continue
            if seller_id not in seller_order:
                seller_order.append(seller_id)
            limit_dt = _parse_ts(item.get("shipping_limit_date"))
            if limit_dt is None:
                continue
            current = earliest_limit_by_seller.get(seller_id)
            if current is None or limit_dt < current:
                earliest_limit_by_seller[seller_id] = limit_dt

        seller_handoff_analysis = []
        late_handoff_seller_ids = []
        for seller_id in seller_order:
            limit_dt = earliest_limit_by_seller.get(seller_id)
            handoff_variance = _variance_hours(handoff_at_dt, limit_dt)
            late_handoff = handoff_variance is not None and handoff_variance > 0
            seller_handoff_analysis.append({
                "seller_id": seller_id,
                "shipping_limit_at": limit_dt.strftime(TIMESTAMP_FORMAT) if limit_dt else None,
                "handoff_variance_hours": handoff_variance,
                "late_handoff": late_handoff,
            })
            if late_handoff:
                late_handoff_seller_ids.append(seller_id)

        # Responsibility only applies when the delivery itself was late: seller if any
        # handoff missed its limit, otherwise the carrier owns the delay.
        if is_late_delivery:
            late_delivery_type = "seller" if late_handoff_seller_ids else "logistics"
        else:
            late_delivery_type = None

        self.logger.info(
            f"[{self.name}] order={order_id} variance={delivery_variance_hours} "
            f"late={is_late_delivery} type={late_delivery_type} "
            f"late_sellers={len(late_handoff_seller_ids)}"
        )

        return {
            "delivered_at": _clean_ts(delivered_raw),
            "estimated_delivery_at": _clean_ts(estimated_raw),
            "carrier_handoff_at": _clean_ts(handoff_raw),
            "delivery_variance_hours": delivery_variance_hours,
            "seller_handoff_analysis": seller_handoff_analysis,
            "late_handoff_seller_ids": late_handoff_seller_ids,
            "is_late_delivery": is_late_delivery,
            "late_delivery_type": late_delivery_type,
        }

