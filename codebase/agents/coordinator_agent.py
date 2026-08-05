"""Coordinator Agent - Orchestrates the dispute resolution workflow.

Responsibilities:
- Read input case JSON
- Initialize shared context
- Call agents in dependency order:
  1. Fetch order data (direct data access)
  2. CustomerAgent + OrderProductAgent (parallel)
  3. PaymentAgent + DeliveryAgent (parallel, depend on step 2)
  4. PolicyAgent (depends on all above)
- Assemble final CaseOutput
- Write output JSON

This is the entry point for processing each case.
"""
import json
import os
import asyncio
from typing import Any, Dict, Optional
from .base_agent import BaseAgent
from .customer_agent import CustomerAgent
from .order_product_agent import OrderProductAgent
from .payment_agent import PaymentAgent
from .delivery_agent import DeliveryAgent
from .policy_agent import PolicyAgent


class CoordinatorAgent(BaseAgent):
    def __init__(self, llm_client, data_access):
        super().__init__("coordinator", llm_client, data_access)
        
        # Initialize sub-agents
        self.customer_agent = CustomerAgent(llm_client, data_access)
        self.order_product_agent = OrderProductAgent(llm_client, data_access)
        self.payment_agent = PaymentAgent(llm_client, data_access)
        self.delivery_agent = DeliveryAgent(llm_client, data_access)
        self.policy_agent = PolicyAgent(llm_client, data_access)
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate the full dispute resolution pipeline.
        
        Expected context keys:
            - case_input: dict (parsed input JSON)
        
        Returns:
            - Full case output dict matching the output schema
        """
        case_input = context["case_input"]
        case_id = case_input["case_id"]
        order_id = case_input["customer_request"]["claimed_order_id"]
        
        self.logger.info(f"Processing case {case_id} for order {order_id}")
        
        # Step 1: Fetch order data
        order_data = self.data.get_order(order_id)
        if not order_data:
            self.logger.error(f"Order {order_id} not found")
            return self._build_empty_output(case_id, order_id)
        
        shared_context = {
            "case_id": case_id,
            "order_id": order_id,
            "order_data": order_data,
        }
        
        # Step 2: Run CustomerAgent and OrderProductAgent (can run in parallel)
        customer_result, order_product_result = await asyncio.gather(
            self.customer_agent.process(shared_context),
            self.order_product_agent.process(shared_context),
        )
        shared_context["customer_result"] = customer_result
        shared_context["order_product_result"] = order_product_result
        shared_context["items"] = order_product_result.get("items", [])
        
        # Step 3: Run PaymentAgent and DeliveryAgent (depend on items)
        payment_result, delivery_result = await asyncio.gather(
            self.payment_agent.process(shared_context),
            self.delivery_agent.process(shared_context),
        )
        shared_context["payment_result"] = payment_result
        shared_context["delivery_result"] = delivery_result
        
        # Step 4: Run PolicyAgent (depends on all above)
        policy_result = await self.policy_agent.process(shared_context)
        shared_context["policy_result"] = policy_result
        
        # Step 5: Assemble final output
        output = self._assemble_output(case_id, shared_context)
        return output
    
    def _assemble_output(self, case_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble the final output dict from all agent results."""
        # TODO: Build complete CaseOutput from all agent results
        # This should map agent results to the exact output schema
        raise NotImplementedError("CoordinatorAgent._assemble_output() not yet implemented")
    
    def _build_empty_output(self, case_id: str, order_id: str) -> Dict[str, Any]:
        """Build a minimal output for cases where order is not found."""
        # TODO: Return valid schema with nulls/empty arrays
        raise NotImplementedError("CoordinatorAgent._build_empty_output() not yet implemented")
