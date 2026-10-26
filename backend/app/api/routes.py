"""HTTP routes. Thin by design: validate, delegate to a service, shape the response."""
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from ..domain.models import CategorizationResult, Category
from ..reporting.tax import TaxEstimate, estimate_tax
from ..services.statement_service import MerchantRuleService, StatementService
from .schemas import MerchantRuleIn, MerchantRuleOut, TaxEstimateRequest

router = APIRouter(prefix="/api")


def get_statement_service(request: Request) -> StatementService:
    return request.app.state.statement_service


def get_rule_service(request: Request) -> MerchantRuleService:
    return request.app.state.rule_service


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/categories", response_model=List[str])
def categories() -> List[str]:
    return [c.value for c in Category]


@router.post("/categorize", response_model=CategorizationResult)
async def categorize_statement(
    file: UploadFile = File(...),
    service: StatementService = Depends(get_statement_service),
) -> CategorizationResult:
    # Read one byte past the limit so oversize files are rejected without loading them fully.
    content = await file.read(service.max_upload_bytes + 1)
    return service.categorize(file.filename or "", content)


@router.post("/tax-estimate", response_model=TaxEstimate)
def tax_estimate(body: TaxEstimateRequest) -> TaxEstimate:
    return estimate_tax(body.transactions)


@router.get("/rules", response_model=List[MerchantRuleOut])
def list_rules(service: MerchantRuleService = Depends(get_rule_service)) -> List[MerchantRuleOut]:
    return [MerchantRuleOut(merchant=r.merchant, category=r.category) for r in service.list()]


@router.put("/rules", response_model=MerchantRuleOut)
def save_rule(body: MerchantRuleIn, service: MerchantRuleService = Depends(get_rule_service)) -> MerchantRuleOut:
    try:
        rule = service.remember(body.merchant, body.category)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return MerchantRuleOut(merchant=rule.merchant, category=rule.category)


@router.delete("/rules/{merchant}", status_code=204)
def delete_rule(merchant: str, service: MerchantRuleService = Depends(get_rule_service)) -> None:
    if not service.forget(merchant):
        raise HTTPException(status_code=404, detail="No rule for that merchant.")
