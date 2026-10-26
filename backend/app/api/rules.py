from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.db.models import MerchantRule
from app.schemas import MerchantRuleOut
from app.services.errors import NotFound

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[MerchantRuleOut])
def list_rules(db: DbSession) -> list[MerchantRule]:
    return list(db.scalars(select(MerchantRule).order_by(MerchantRule.merchant_key)))


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(db: DbSession, rule_id: int) -> Response:
    """Forget a learned rule. Rows it already changed keep their category."""
    rule = db.get(MerchantRule, rule_id)
    if rule is None:
        raise NotFound(f"rule {rule_id} not found")
    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
