"""Policy Agent - Applies EC_POLICY_V2 business rules.

Responsibilities:
- Determine primary_issue based on policy priority order
- Determine secondary_issues in specified order
- Identify root_cause_code
- Determine responsible_parties
- Calculate recommended_refund_brl
- Determine resolution_actions
- Use LLM to perform policy synthesis and verification
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
from typing import Any, Dict, List, Optional, Tuple
from .base_agent import BaseAgent


class PolicyAgent(BaseAgent):
    def __init__(self, llm_client, data_access):
        super().__init__("policy_agent", llm_client, data_access)

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business rules and determine resolution.

        Expected context keys:
            - order_id: str
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
        order_id = context["order_id"]
        order_data = context["order_data"]
        customer_result = context.get("customer_result", {})
        order_product_result = context.get("order_product_result", {})
        payment_result = context.get("payment_result", {})
        delivery_result = context.get("delivery_result", {})

        # --- Extract values from agent results ---
        order_status = order_data.get("order_status")
        payment_total = payment_result.get("payment_total_brl", 0) or 0
        freight_total = payment_result.get("freight_total_brl")
        is_late_delivery = delivery_result.get("is_late_delivery", False)
        late_handoff_seller_ids = delivery_result.get("late_handoff_seller_ids", [])
        late_delivery_type = delivery_result.get("late_delivery_type")
        is_split_payment = payment_result.get("is_split_payment", False)
        reconciled = payment_result.get("reconciled")

        is_multi_item = order_product_result.get("is_multi_item", False)
        is_multi_seller = order_product_result.get("is_multi_seller", False)
        is_multiple_categories = order_product_result.get("is_multiple_categories", False)
        is_repeat_customer = customer_result.get("is_repeat_customer", False)

        items = order_product_result.get("items", [])
        payment_rows = payment_result.get("payment_rows", [])

        # --- Primary issue determination ---
        (
            primary_issue,
            root_cause_code,
            refund_amount,
            main_action,
            party_type,
            party_id,
        ) = self._determine_primary_issue(
            order_status=order_status,
            payment_total=payment_total,
            is_late_delivery=is_late_delivery,
            late_handoff_seller_ids=late_handoff_seller_ids,
            is_split_payment=is_split_payment,
            reconciled=reconciled,
            freight_total=freight_total,
        )

        # --- Secondary issues ---
        secondary_issues = self._determine_secondary_issues(
            is_multi_item=is_multi_item,
            is_multi_seller=is_multi_seller,
            is_split_payment=is_split_payment,
            is_repeat_customer=is_repeat_customer,
            is_multiple_categories=is_multiple_categories,
        )

        # --- Responsible parties ---
        responsible_parties = self._build_responsible_parties(
            primary_issue=primary_issue,
            party_type=party_type,
            party_id=party_id,
            late_handoff_seller_ids=late_handoff_seller_ids,
        )

        # --- Resolution actions ---
        has_late_seller = primary_issue == "late_delivery_seller"
        has_late_logistics = primary_issue == "late_delivery_logistics"
        has_refund = refund_amount > 0

        resolution_actions = self._build_resolution_actions(
            primary_issue=primary_issue,
            main_action=main_action,
            has_late_seller=has_late_seller,
            has_late_logistics=has_late_logistics,
            has_refund=has_refund,
            is_multi_seller=is_multi_seller,
            is_split_payment=is_split_payment,
        )

        # --- Evidence IDs ---
        evidence_ids = self._build_evidence_ids(
            order_id=order_id,
            items=items,
            payment_rows=payment_rows,
            responsible_parties=responsible_parties,
            root_cause_code=root_cause_code,
        )

        # --- Determine case_status and confidence ---
        case_status = "action_required" if refund_amount > 0 else "no_action"

        confidence = 0.95
        if not items:
            confidence -= 0.10
        if not payment_rows:
            confidence -= 0.10
        if order_status in ("canceled", "unavailable"):
            confidence = 0.98
        confidence = round(max(0.0, min(1.0, confidence)), 2)

        # LLM reasoning integration
        if self.llm:
            try:
                system_prompt = (
                    "You are Policy Agent in an e-commerce multi-agent dispute resolution system. "
                    "Synthesize findings from Customer Agent, Order Product Agent, Payment Agent, and Delivery Agent. "
                    "Apply EC_POLICY_V2 policy rules to confirm primary issue, secondary issues, root cause code, refund amount, and resolution actions. "
                    "Return a JSON synthesis."
                )
                user_prompt = (
                    f"Case Order ID: {order_id}\n"
                    f"Order Status: {order_status}\n"
                    f"Customer Unique ID: {customer_result.get('customer_unique_id')}\n"
                    f"Payment Total: {payment_total} BRL, Reconciled: {reconciled}\n"
                    f"Delivery Variance: {delivery_result.get('delivery_variance_hours')} hours, Is Late: {is_late_delivery}\n"
                    f"Determined Primary Issue: {primary_issue}\n"
                    f"Determined Root Cause Code: {root_cause_code}\n"
                    f"Recommended Refund: {refund_amount} BRL\n"
                    f"Case Status: {case_status}\n"
                    f"Resolution Actions: {resolution_actions}\n"
                    "Synthesize policy resolution and return JSON."
                )
                messages = self._build_prompt(system_prompt, user_prompt)
                llm_response = self.llm.chat_json(messages)
                self.logger.info(f"[{self.name}] LLM response received for order {order_id}")
            except Exception as e:
                self.logger.warning(f"[{self.name}] LLM analysis fallback due to: {e}")

        self.logger.info(
            f"Policy result: primary={primary_issue}, status={case_status}, "
            f"refund={refund_amount}, actions={resolution_actions}"
        )

        return {
            "primary_issue": primary_issue,
            "secondary_issues": secondary_issues,
            "case_status": case_status,
            "confidence": confidence,
            "root_cause_code": root_cause_code,
            "responsible_parties": responsible_parties,
            "recommended_refund_brl": round(refund_amount, 2),
            "resolution_actions": resolution_actions,
            "evidence_ids": evidence_ids,
        }

    # ------------------------------------------------------------------ #
    #  Helper methods                                                    #
    # ------------------------------------------------------------------ #

    def _determine_primary_issue(
        self,
        order_status: Optional[str],
        payment_total: Optional[float],
        is_late_delivery: Optional[bool],
        late_handoff_seller_ids: Optional[List[str]],
        is_split_payment: Optional[bool],
        reconciled: Optional[bool],
        freight_total: Optional[float],
    ) -> Tuple[str, str, float, str, Optional[str], Optional[str]]:
        safe_payment = float(payment_total) if payment_total is not None else 0.0
        safe_freight = float(freight_total) if freight_total is not None else 0.0
        safe_sellers = late_handoff_seller_ids if late_handoff_seller_ids else []

        if order_status == "canceled" and safe_payment > 0:
            return (
                "canceled_order_paid",
                "ORDER_CANCELED_AFTER_PAYMENT",
                round(safe_payment, 2),
                "issue_full_refund",
                "platform",
                "OLIST_PLATFORM",
            )

        if order_status == "unavailable" and safe_payment > 0:
            return (
                "unavailable_order_paid",
                "ORDER_UNAVAILABLE_AFTER_PAYMENT",
                round(safe_payment, 2),
                "issue_full_refund",
                "platform",
                "OLIST_PLATFORM",
            )

        if is_late_delivery is True and len(safe_sellers) > 0:
            return (
                "late_delivery_seller",
                "SELLER_HANDOFF_AFTER_LIMIT",
                round(safe_freight, 2),
                "refund_freight",
                "seller",
                None,
            )

        if is_late_delivery is True and len(safe_sellers) == 0:
            return (
                "late_delivery_logistics",
                "CARRIER_DELIVERED_AFTER_ESTIMATE",
                round(safe_freight, 2),
                "refund_freight",
                "logistics_provider",
                "LOGISTICS_PROVIDER",
            )

        if is_split_payment is True and reconciled is True:
            return (
                "valid_split_payment",
                "MULTIPLE_PAYMENTS_RECONCILED",
                0.0,
                "explain_valid_split_payment",
                None,
                None,
            )

        return (
            "unsupported_late_claim",
            "DELIVERY_WITHIN_ESTIMATE",
            0.0,
            "reject_late_refund",
            None,
            None,
        )

    def _determine_secondary_issues(
        self,
        is_multi_item: bool,
        is_multi_seller: bool,
        is_split_payment: bool,
        is_repeat_customer: bool,
        is_multiple_categories: bool,
    ) -> List[str]:
        issues: List[str] = []
        if is_multi_item:
            issues.append("multi_item_order")
        if is_multi_seller:
            issues.append("multi_seller_order")
        if is_split_payment:
            issues.append("split_payment")
        if is_repeat_customer:
            issues.append("repeat_customer")
        if is_multiple_categories:
            issues.append("multiple_categories")
        return issues

    def _build_resolution_actions(
        self,
        primary_issue: str,
        main_action: str,
        has_late_seller: bool,
        has_late_logistics: bool,
        has_refund: bool,
        is_multi_seller: bool,
        is_split_payment: bool,
    ) -> List[str]:
        actions: List[str] = [main_action]
        if has_late_seller:
            actions.append("review_seller_handoff")
        elif has_late_logistics:
            actions.append("review_carrier_delay")
        if has_refund:
            actions.append("verify_refund_completion")
        if is_multi_seller:
            actions.append("coordinate_multi_seller_case")
        if is_split_payment and primary_issue != "valid_split_payment":
            actions.append("verify_payment_allocation")
        return actions[:5]

    def _build_evidence_ids(
        self,
        order_id: str,
        items: Optional[List[Dict]],
        payment_rows: Optional[List[Dict]],
        responsible_parties: List[Dict[str, str]],
        root_cause_code: str,
    ) -> List[str]:
        evidence: List[str] = [f"order:{order_id}"]
        if items:
            for item in items:
                item_id = item.get("order_item_id")
                if item_id is not None:
                    try:
                        evidence.append(f"item:{order_id}:{int(float(item_id))}")
                    except (ValueError, TypeError):
                        pass
        if payment_rows:
            for p in payment_rows:
                seq = p.get("payment_sequential")
                if seq is not None:
                    try:
                        evidence.append(f"payment:{order_id}:{int(float(seq))}")
                    except (ValueError, TypeError):
                        pass

        for party in responsible_parties:
            if party.get("party_type") == "seller" and party.get("party_id"):
                evidence.append(f"seller:{party['party_id']}")
        if root_cause_code:
            evidence.append(f"policy:{root_cause_code}")
        return evidence[:20]

    def _build_responsible_parties(
        self,
        primary_issue: str,
        party_type: Optional[str],
        party_id: Optional[str],
        late_handoff_seller_ids: Optional[List[str]],
    ) -> List[Dict[str, str]]:
        if primary_issue == "late_delivery_seller":
            safe_sellers = late_handoff_seller_ids if late_handoff_seller_ids else []
            return [
                {"party_type": "seller", "party_id": str(sid)}
                for sid in safe_sellers[:3]
            ]
        if party_type is not None and party_id is not None:
            return [{"party_type": str(party_type), "party_id": str(party_id)}]
        return []
