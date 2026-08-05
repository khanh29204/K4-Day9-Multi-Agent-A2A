"""Payment Agent - Payment reconciliation and analysis.

Responsibilities:
- Fetch all payment rows for the order
- Calculate payment_total_brl
- Compare with expected_total_brl (from items + freight)
- Determine if reconciled (within 0.10 BRL tolerance)
- Detect split_payment secondary issue

Data access: order_payments

Formulas:
  expected_total_brl = sum(price) + sum(freight_value)
  difference_brl = payment_total_brl - expected_total_brl
  reconciled = abs(difference_brl) <= 0.10
"""
from typing import Any, Dict, Optional
from .base_agent import BaseAgent

RECONCILE_TOLERANCE_BRL = 0.10


def _to_float(value: Any) -> Optional[float]:
    """Coerce a CSV cell to float, treating missing/NaN values as None."""
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return None if num != num else num  # NaN check


class PaymentAgent(BaseAgent):
    def __init__(self, llm_client, data_access):
        super().__init__("payment_agent", llm_client, data_access)

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze payment reconciliation.
        
        Expected context keys:
            - order_id: str
            - items: list of item dicts (from OrderProductAgent)
        
        Returns:
            - payment_rows: list of payment dicts
            - item_total_brl: float or None
            - freight_total_brl: float or None
            - expected_total_brl: float or None
            - payment_total_brl: float
            - difference_brl: float or None
            - reconciled: bool or None
            - payment_types: list[str]
            - is_split_payment: bool
            - affected_payment_ids: list[str]
        """
        order_id = context["order_id"]
        items = context.get("items") or []

        payment_rows = self.data.get_order_payments(order_id)
        # Stable order by payment_sequential, as the schema lists payment IDs in source order.
        payment_rows = sorted(
            payment_rows,
            key=lambda row: _to_float(row.get("payment_sequential")) or 0.0,
        )

        payment_total_brl = round(
            sum(_to_float(row.get("payment_value")) or 0.0 for row in payment_rows), 2
        )

        # Without item rows there is nothing to reconcile against: item/expected/difference
        # and reconciled must stay null per EC_POLICY_V2.
        if items:
            item_total_brl = round(
                sum(_to_float(item.get("price")) or 0.0 for item in items), 2
            )
            freight_total_brl = round(
                sum(_to_float(item.get("freight_value")) or 0.0 for item in items), 2
            )
            expected_total_brl = round(item_total_brl + freight_total_brl, 2)
            difference_brl = round(payment_total_brl - expected_total_brl, 2)
            reconciled = abs(difference_brl) <= RECONCILE_TOLERANCE_BRL
        else:
            item_total_brl = None
            freight_total_brl = None
            expected_total_brl = None
            difference_brl = None
            reconciled = None

        payment_types = []
        for row in payment_rows:
            ptype = row.get("payment_type")
            if ptype and ptype not in payment_types:
                payment_types.append(ptype)

        affected_payment_ids = []
        for row in payment_rows:
            seq = _to_float(row.get("payment_sequential"))
            if seq is None:
                continue
            affected_payment_ids.append(f"{order_id}:{int(seq)}")

        self.logger.info(
            f"[{self.name}] order={order_id} payments={len(payment_rows)} "
            f"total={payment_total_brl} diff={difference_brl} reconciled={reconciled}"
        )

        return {
            "payment_rows": payment_rows,
            "item_total_brl": item_total_brl,
            "freight_total_brl": freight_total_brl,
            "expected_total_brl": expected_total_brl,
            "payment_total_brl": payment_total_brl,
            "difference_brl": difference_brl,
            "reconciled": reconciled,
            "payment_types": payment_types,
            "is_split_payment": len(payment_rows) >= 2,
            "affected_payment_ids": affected_payment_ids,
        }

