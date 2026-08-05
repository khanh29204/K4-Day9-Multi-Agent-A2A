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
import asyncio
from typing import Any, Dict, Optional

from models import (
    AffectedEntities,
    CaseAssessment,
    CaseOutput,
    CustomerContext,
    DeliveryAnalysis,
    FinancialResolution,
    PaymentReconciliation,
    ProductContext,
    RankedCause,
    ResponsibleParty,
    RootCauseAnalysis,
    SellerHandoffAnalysis,
    CaseInput,
)
from .base_agent import BaseAgent
from .customer_agent import CustomerAgent
from .delivery_agent import DeliveryAgent
from .order_product_agent import OrderProductAgent
from .payment_agent import PaymentAgent
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
        # Treat every field from the request as untrusted. In particular, the
        # free-text message must never become an instruction or evidence.
        # Pydantic also rejects malformed IDs and unknown control fields before
        # they reach the data-access layer.
        case_input = CaseInput.model_validate(context["case_input"])
        case_id = case_input.case_id
        order_id = case_input.customer_request.claimed_order_id

        self.logger.info(f"Processing case {case_id} for order {order_id}")

        # Step 1: Fetch order data
        order_data = self.data.get_order(order_id)
        if not order_data:
            # Do not turn a user-supplied, unknown ID into fabricated evidence
            # or a policy verdict. The caller should receive a controlled error.
            raise ValueError("claimed_order_id does not exist")

        authenticated_customer_id = case_input.customer_request.authenticated_customer_id
        if authenticated_customer_id:
            if authenticated_customer_id != order_data.get("customer_id"):
                self.logger.warning(
                    "Rejected case %s: authenticated customer does not own claimed order",
                    case_id,
                )
                raise PermissionError("authenticated customer does not own claimed_order_id")
        else:
            # The exercise input has no authenticated identity. We can verify
            # facts in CSV, but cannot establish that the requester owns them.
            self.logger.warning(
                "Case %s has no authenticated customer; ownership cannot be verified",
                case_id,
            )

        shared_context = {
            "case_id": case_id,
            "order_id": order_id,
            "order_data": order_data,
        }

        # Step 2: Run CustomerAgent and OrderProductAgent (parallel)
        customer_result, order_product_result = await asyncio.gather(
            self.customer_agent.process(shared_context),
            self.order_product_agent.process(shared_context),
        )
        shared_context["customer_result"] = customer_result
        shared_context["order_product_result"] = order_product_result
        shared_context["items"] = order_product_result.get("items", [])

        # Step 3: Run PaymentAgent and DeliveryAgent (parallel, depend on items)
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
        customer_res = ctx.get("customer_result", {})
        order_product_res = ctx.get("order_product_result", {})
        payment_res = ctx.get("payment_result", {})
        delivery_res = ctx.get("delivery_result", {})
        policy_res = ctx.get("policy_result", {})

        # 1. Case Assessment
        case_assessment = CaseAssessment(
            primary_issue=policy_res.get("primary_issue"),
            secondary_issues=policy_res.get("secondary_issues", [])[:5],
            case_status=policy_res.get("case_status", "no_action"),
            confidence=policy_res.get("confidence", 0.95),
        )

        # 2. Affected Entities
        affected_entities = AffectedEntities(
            order_ids=[ctx["order_id"]][:5],
            item_ids=order_product_res.get("affected_item_ids", [])[:5],
            seller_ids=order_product_res.get("affected_seller_ids", [])[:3],
            payment_ids=payment_res.get("affected_payment_ids", [])[:5],
        )

        # 3. Customer Context
        customer_context = CustomerContext(
            customer_unique_id=customer_res.get("customer_unique_id"),
            related_order_ids=customer_res.get("related_order_ids", [])[:5],
        )

        # 4. Product Context
        product_context = ProductContext(
            product_ids=order_product_res.get("affected_product_ids", [])[:5],
            category_names=order_product_res.get("categories", [])[:5],
        )

        # 5. Delivery Analysis
        raw_seller_handoff = delivery_res.get("seller_handoff_analysis", [])
        seller_handoff_objects = [
            SellerHandoffAnalysis(
                seller_id=sh.get("seller_id"),
                shipping_limit_at=sh.get("shipping_limit_at"),
                handoff_variance_hours=sh.get("handoff_variance_hours"),
                late_handoff=sh.get("late_handoff"),
            )
            for sh in raw_seller_handoff[:3]
        ]

        delivery_analysis = DeliveryAnalysis(
            delivered_at=delivery_res.get("delivered_at"),
            estimated_delivery_at=delivery_res.get("estimated_delivery_at"),
            carrier_handoff_at=delivery_res.get("carrier_handoff_at"),
            delivery_variance_hours=delivery_res.get("delivery_variance_hours"),
            seller_handoff_analysis=seller_handoff_objects,
            late_handoff_seller_ids=delivery_res.get("late_handoff_seller_ids", [])[:3],
        )

        # 6. Payment Reconciliation
        payment_reconciliation = PaymentReconciliation(
            currency="BRL",
            item_total_brl=payment_res.get("item_total_brl"),
            freight_total_brl=payment_res.get("freight_total_brl"),
            expected_total_brl=payment_res.get("expected_total_brl"),
            payment_total_brl=payment_res.get("payment_total_brl"),
            difference_brl=payment_res.get("difference_brl"),
            reconciled=payment_res.get("reconciled"),
            payment_types=payment_res.get("payment_types", []),
        )

        # 7. Root Cause Analysis
        root_cause_code = policy_res.get("root_cause_code")
        ranked_causes = (
            [RankedCause(cause_code=root_cause_code, rank=1)]
            if root_cause_code
            else []
        )

        raw_parties = policy_res.get("responsible_parties", [])
        party_objects = [
            ResponsibleParty(
                party_type=p.get("party_type"),
                party_id=p.get("party_id"),
            )
            for p in raw_parties[:3]
        ]

        root_cause_analysis = RootCauseAnalysis(
            ranked_causes=ranked_causes[:3],
            responsible_parties=party_objects,
        )

        # 8. Financial Resolution
        refund_amount = policy_res.get("recommended_refund_brl", 0.0)
        financial_resolution = FinancialResolution(
            currency="BRL",
            recommended_refund_brl=refund_amount if refund_amount is not None else 0.0,
        )

        # 9. Complete Output
        output = CaseOutput(
            case_id=case_id,
            case_assessment=case_assessment,
            affected_entities=affected_entities,
            customer_context=customer_context,
            product_context=product_context,
            delivery_analysis=delivery_analysis,
            payment_reconciliation=payment_reconciliation,
            root_cause_analysis=root_cause_analysis,
            evidence_ids=policy_res.get("evidence_ids", [])[:20],
            financial_resolution=financial_resolution,
            resolution_actions=policy_res.get("resolution_actions", [])[:5],
        )

        return output.to_output_dict()
