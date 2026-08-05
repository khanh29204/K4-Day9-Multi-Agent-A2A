from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, StrictStr


class InvestigationScope(BaseModel):
    """Requested enrichment only; it never changes the policy decision."""

    model_config = ConfigDict(extra="ignore")

    include_customer_history: bool = False
    include_product_context: bool = False

class CustomerRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    language: Optional[StrictStr] = None
    # Untrusted free text: retained for audit/UI only and never used as evidence
    # or instructions for an agent.
    message: Optional[StrictStr] = None
    claimed_order_id: str = ""
    # Production callers can supply an authenticated principal. The coordinator
    # checks it against the order record before disclosing any order data.
    authenticated_customer_id: Optional[StrictStr] = None

class CaseInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case_id: str = ""
    customer_request: CustomerRequest
    investigation_scope: Optional[InvestigationScope] = None
    policy_version: Optional[str] = None

class CaseAssessment(BaseModel):
    primary_issue: Optional[str] = None
    secondary_issues: Optional[List[str]] = None
    case_status: Optional[str] = None
    confidence: Optional[float] = None

class AffectedEntities(BaseModel):
    order_ids: List[str] = Field(default_factory=list)
    item_ids: List[str] = Field(default_factory=list)
    seller_ids: List[str] = Field(default_factory=list)
    payment_ids: List[str] = Field(default_factory=list)

class CustomerContext(BaseModel):
    customer_unique_id: Optional[str] = None
    related_order_ids: List[str] = Field(default_factory=list)

class ProductContext(BaseModel):
    product_ids: List[str] = Field(default_factory=list)
    category_names: List[str] = Field(default_factory=list)

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
    seller_handoff_analysis: List[SellerHandoffAnalysis] = Field(default_factory=list)
    late_handoff_seller_ids: List[str] = Field(default_factory=list)

class PaymentReconciliation(BaseModel):
    currency: Optional[str] = "BRL"
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    payment_types: List[str] = Field(default_factory=list)

class RankedCause(BaseModel):
    cause_code: Optional[str] = None
    rank: Optional[int] = None

class ResponsibleParty(BaseModel):
    party_type: Optional[str] = None
    party_id: Optional[str] = None

class RootCauseAnalysis(BaseModel):
    ranked_causes: List[RankedCause] = Field(default_factory=list)
    responsible_parties: List[ResponsibleParty] = Field(default_factory=list)

class FinancialResolution(BaseModel):
    currency: Optional[str] = "BRL"
    recommended_refund_brl: Optional[float] = 0.0

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
    evidence_ids: List[str] = Field(default_factory=list)
    financial_resolution: Optional[FinancialResolution] = None
    resolution_actions: List[str] = Field(default_factory=list)

    def to_output_dict(self) -> dict:
        return self.model_dump(exclude_none=False, by_alias=True)
