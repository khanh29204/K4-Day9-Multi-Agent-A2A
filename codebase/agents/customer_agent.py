"""Customer Agent - Identifies customer identity and order history.

Responsibilities:
- Look up customer by customer_id from the order
- Find customer_unique_id
- Search for related orders (repeat customer detection)
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
        all_orders = self.data.get_customer_orders(customer_unique_id)

        related_order_ids = [
            order["order_id"] for order in all_orders if order.get("order_id") != order_id
        ][:5]

        return {
            "customer_unique_id": customer_unique_id,
            "related_order_ids": related_order_ids,
            "is_repeat_customer": len(related_order_ids) > 0,
        }
