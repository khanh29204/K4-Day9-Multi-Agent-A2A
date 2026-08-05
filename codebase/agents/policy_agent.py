"""Policy Agent - Applies EC_POLICY_V2 business rules.

Responsibilities:
- Determine primary_issue based on policy priority order
- Determine secondary_issues in specified order
- Identify root_cause_code
- Determine responsible_parties
- Calculate recommended_refund_brl
- Determine resolution_actions
- Set case_status and confidence

Policy priority order:
1. canceled_order_paid: order_status=canceled AND total_payment > 0
2. unavailable_order_paid: order_status=unavailable AND total_payment > 0
3. late_delivery_seller: late delivery AND seller late handoff
4. late_delivery_logistics: late delivery AND no seller late handoff
5. valid_split_payment: >=2 payment rows AND reconciled
6. unsupported_late_claim: not late AND reconciled

Secondary issues order:
1. multi_item_order: >=2 item rows
2. multi_seller_order: >=2 distinct sellers
3. split_payment: >=2 payment rows
4. repeat_customer: same customer_unique_id has other orders
5. multiple_categories: >=2 distinct categories
"""
from typing import Any, Dict
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    def __init__(self, llm_client, data_access):
        super().__init__("policy_agent", llm_client, data_access)
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business rules and determine resolution.
        
        Expected context keys:
            - order_data: dict
            - customer_result: dict (from CustomerAgent)
            - order_product_result: dict (from OrderProductAgent)
            - payment_result: dict (from PaymentAgent)
            - delivery_result: dict (from DeliveryAgent)
        
        Returns:
            - primary_issue: str
            - secondary_issues: list[str]
            - case_status: str ("action_required" or "no_action")
            - confidence: float
            - root_cause_code: str
            - responsible_parties: list of dicts
            - recommended_refund_brl: float
            - resolution_actions: list[str]
            - evidence_ids: list[str]
        """
        # TODO: Implement policy evaluation
        # 1. Check primary issues in priority order
        # 2. Check secondary issues in specified order
        # 3. Determine root cause, responsible parties
        # 4. Calculate refund amount
        # 5. Build resolution actions and evidence
        raise NotImplementedError("PolicyAgent.process() not yet implemented")
