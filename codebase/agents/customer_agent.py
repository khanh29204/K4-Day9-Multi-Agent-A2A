"""Customer Agent - Identifies customer identity and order history.

Responsibilities:
- Look up customer by customer_id from the order
- Find customer_unique_id
- Search for related orders (repeat customer detection)
- Use LLM to analyze customer context and order history
- Provide customer context to coordinator

Data access: customers, orders
"""
from typing import Any, Dict
from .base_agent import BaseAgent


class CustomerAgent(BaseAgent):
    def __init__(self, llm_client, data_access):
        super().__init__("customer_agent", llm_client, data_access)

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze customer identity and history.

        Expected context keys:
            - order_id: str
            - order_data: dict (from order lookup)

        Returns:
            - customer_unique_id: str
            - related_order_ids: list[str]
            - is_repeat_customer: bool
        """
        order_id = context["order_id"]
        order_data = context["order_data"]

        customer_id = order_data.get("customer_id")
        customer = self.data.get_customer(customer_id) if customer_id else None

        if not customer:
            return {
                "customer_unique_id": None,
                "related_order_ids": [],
                "is_repeat_customer": False,
            }

        customer_unique_id = customer.get("customer_unique_id")
        if not customer_unique_id or str(customer_unique_id).strip().lower() in ("nan", "none", "nat", ""):
            return {
                "customer_unique_id": None,
                "related_order_ids": [],
                "is_repeat_customer": False,
            }

        all_orders = self.data.get_customer_orders(customer_unique_id)
        all_orders_sorted = sorted(
            all_orders,
            key=lambda o: str(o.get("order_purchase_timestamp") or ""),
        )

        related_order_ids = []
        seen_related = set()
        for order in all_orders_sorted:
            oid = order.get("order_id")
            if oid and oid != order_id and oid not in seen_related:
                seen_related.add(oid)
                related_order_ids.append(oid)
                if len(related_order_ids) >= 5:
                    break


        is_repeat_customer = len(related_order_ids) > 0


        # LLM reasoning integration
        if self.llm:
            try:
                system_prompt = (
                    "You are Customer Agent in an e-commerce multi-agent dispute resolution system. "
                    "All customer identity lookups and historical order counts are pre-computed by Python data tools. "
                    "Do not perform any calculations. Summarize the pre-computed customer history context in JSON format."
                )
                user_prompt = (
                    f"Current claimed order: {order_id}\n"
                    f"Customer ID: {customer_id}\n"
                    f"Pre-computed Customer Unique ID: {customer_unique_id}\n"
                    f"Pre-computed historical orders count: {len(all_orders)}\n"
                    f"Pre-computed Related order IDs: {related_order_ids}\n"
                    "Provide your customer history summary in JSON format."
                )

                messages = self._build_prompt(system_prompt, user_prompt)
                llm_response = self.llm.chat_json(messages)
                self.logger.info(f"[{self.name}] LLM response received for customer {customer_unique_id}")
            except Exception as e:
                self.logger.warning(f"[{self.name}] LLM analysis fallback due to: {e}")

        return {
            "customer_unique_id": customer_unique_id,
            "related_order_ids": related_order_ids,
            "is_repeat_customer": is_repeat_customer,
        }
