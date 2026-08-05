from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class CustomerRequest(BaseModel):
    language: Optional[str] = None
    message: Optional[str] = None
    claimed_order_id: Optional[str] = None

class CaseInput(BaseModel):
    case_id: str
    customer_request: CustomerRequest
    investigation_scope: Optional[List[str]] = None
    policy_version: Optional[str] = None

class CaseAssessment(BaseModel):
    primary_issue: Optional[str] = None
    secondary_issues: Optional[List[str]] = None
    case_status: Optional[str] = None
    confidence: Optional[float] = None

class AffectedEntities(BaseModel):
    order_ids: Optional[List[str]] = None
    item_ids: Optional[List[str]] = None
    seller_ids: Optional[List[str]] = None
    payment_ids: Optional[List[str]] = None

class CustomerContext(BaseModel):
    customer_unique_id: Optional[str] = None
    related_order_ids: Optional[List[str]] = None

class ProductContext(BaseModel):
    product_ids: Optional[List[str]] = None
    category_names: Optional[List[str]] = None

class SellerHandoffAnalysis(BaseModel):
    seller_id: Optional[str] = None
    shipping_limit_at: Optional[str] = None
    handoff_variance_hours: Optional[float] = None
    late_handoff: Optional[bool] = None

class DeliveryAnalysis(BaseModel):
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: Optional[List[SellerHandoffAnalysis]] = None
    late_handoff_seller_ids: Optional[List[str]] = None

class PaymentReconciliation(BaseModel):
    currency: Optional[str] = None
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    payment_types: Optional[List[str]] = None

class RankedCause(BaseModel):
    cause_code: Optional[str] = None
    rank: Optional[int] = None

class ResponsibleParty(BaseModel):
    party_type: Optional[str] = None
    party_id: Optional[str] = None

class RootCauseAnalysis(BaseModel):
    ranked_causes: Optional[List[RankedCause]] = None
    responsible_parties: Optional[List[ResponsibleParty]] = None

class FinancialResolution(BaseModel):
    currency: Optional[str] = None
    recommended_refund_brl: Optional[float] = None

class CaseOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    case_id: Optional[str] = None
    case_assessment: Optional[CaseAssessment] = None
    affected_entities: Optional[AffectedEntities] = None
    customer_context: Optional[CustomerContext] = None
    product_context: Optional[ProductContext] = None
    delivery_analysis: Optional[DeliveryAnalysis] = None
    payment_reconciliation: Optional[PaymentReconciliation] = None
    root_cause_analysis: Optional[RootCauseAnalysis] = None
    evidence_ids: Optional[List[str]] = None
    financial_resolution: Optional[FinancialResolution] = None
    resolution_actions: Optional[List[str]] = None

    def to_output_dict(self) -> dict:
        return self.model_dump(exclude_none=False, by_alias=True)
