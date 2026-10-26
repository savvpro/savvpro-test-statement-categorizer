"""JSON API routes for merchant rule management and bulk recategorization."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.models.merchant_rule import RuleMatchType
from app.services.rule_service import RuleService

router = APIRouter(prefix="/api/rules", tags=["rules-api"])


class CreateRuleRequest(BaseModel):
    """Payload to create a new merchant rule."""

    merchant_pattern: str = Field(..., min_length=1, description="Merchant name substring or pattern")
    category_id: int = Field(..., description="Target category ID")
    match_type: str = Field(RuleMatchType.CONTAINS, description="CONTAINS, EXACT, or REGEX")
    priority: int = Field(100, ge=1, le=10000, description="Priority score (higher evaluated first)")
    is_active: bool = Field(True, description="Whether rule is currently active")


class UpdateRuleRequest(BaseModel):
    """Payload to update an existing merchant rule."""

    merchant_pattern: Optional[str] = None
    category_id: Optional[int] = None
    match_type: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class ApplyRuleRequest(BaseModel):
    """Payload for bulk recategorization application."""

    override_manual: bool = Field(
        False, description="Whether to overwrite transactions that were manually categorized"
    )


def _serialize_rule(rule) -> Dict[str, Any]:
    """Serialize a MerchantRule model instance."""
    return {
        "id": rule.id,
        "merchant_pattern": rule.merchant_pattern,
        "match_type": rule.match_type,
        "category_id": rule.category_id,
        "category_name": rule.category.name if rule.category else None,
        "priority": rule.priority,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


@router.get("", summary="List merchant rules")
def list_rules(
    active_only: bool = Query(False, description="Filter for active rules only"),
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Retrieve all merchant rules ordered by priority."""
    svc = RuleService(db)
    rules = svc.list_rules(active_only=active_only)
    return [_serialize_rule(r) for r in rules]


@router.post("", summary="Create merchant rule", status_code=201)
def create_rule(
    payload: CreateRuleRequest,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a new reusable categorization rule."""
    svc = RuleService(db)
    try:
        rule = svc.create_rule(
            merchant_pattern=payload.merchant_pattern,
            category_id=payload.category_id,
            match_type=payload.match_type,
            priority=payload.priority,
            is_active=payload.is_active,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    return _serialize_rule(rule)


@router.get("/{rule_id}", summary="Get rule by ID")
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Fetch rule configuration by ID."""
    svc = RuleService(db)
    rule = svc.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _serialize_rule(rule)


@router.put("/{rule_id}", summary="Update rule")
def update_rule(
    rule_id: int,
    payload: UpdateRuleRequest,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update rule settings."""
    svc = RuleService(db)
    try:
        rule = svc.update_rule(
            rule_id=rule_id,
            merchant_pattern=payload.merchant_pattern,
            category_id=payload.category_id,
            match_type=payload.match_type,
            priority=payload.priority,
            is_active=payload.is_active,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    return _serialize_rule(rule)


@router.delete("/{rule_id}", summary="Delete rule")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Safely delete a rule without deleting any past transactions."""
    svc = RuleService(db)
    deleted = svc.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.commit()
    return {"status": "ok", "deleted_rule_id": rule_id}


@router.post("/{rule_id}/toggle", summary="Toggle rule active state")
def toggle_rule(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Toggle a rule between active and inactive states."""
    svc = RuleService(db)
    try:
        rule = svc.toggle_rule(rule_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return _serialize_rule(rule)


@router.post("/{rule_id}/preview", summary="Preview rule recategorization")
def preview_rule(
    rule_id: int,
    override_manual: bool = Query(False, description="Include manually categorized in preview"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Preview matching transactions before applying a rule."""
    svc = RuleService(db)
    try:
        preview = svc.preview_recategorization(rule_id, override_manual=override_manual)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Serialize preview items
    serialized_items = [
        {
            "transaction_id": item.transaction_id,
            "transaction_date": item.transaction_date,
            "original_description": item.original_description,
            "amount": item.amount,
            "current_category_name": item.current_category_name,
            "new_category_name": item.new_category_name,
            "is_manual": item.is_manual,
            "status": item.status,
        }
        for item in preview["items"]
    ]
    preview["items"] = serialized_items
    return preview


@router.post("/{rule_id}/apply", summary="Apply rule to matching transactions")
def apply_rule(
    rule_id: int,
    payload: ApplyRuleRequest,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Apply rule recategorization to matching transactions."""
    svc = RuleService(db)
    try:
        result = svc.apply_recategorization(rule_id, override_manual=payload.override_manual)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

    return result
