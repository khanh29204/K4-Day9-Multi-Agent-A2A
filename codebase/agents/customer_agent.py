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
        # TODO: Implement customer lookup and history analysis
        # 1. Get customer_id from order_data
        # 2. Look up customer to get customer_unique_id
        # 3. Find all orders with same customer_unique_id
        # 4. Return customer context
        raise NotImplementedError("CustomerAgent.process() not yet implemented")
