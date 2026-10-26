"""
Rules API – CRUD for user-saved categorization rules.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.brain.categories import CATEGORIES
from app.db import get_session
from app.models import Transaction, UserRule
from app.schemas import RuleCreate, RuleOut, RuleTestResult

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(session: Session = Depends(get_session)):
    """List all saved rules."""
    rules = session.exec(select(UserRule).order_by(UserRule.created_at.desc())).all()
    return [RuleOut.model_validate(r) for r in rules]


@router.post("", response_model=RuleOut)
def create_rule(body: RuleCreate, session: Session = Depends(get_session)):
    """Create a new user rule."""
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category: {body.category}")

    # Validate regex
    if body.match_type == "regex":
        try:
            re.compile(body.pattern)
        except re.error as exc:
            raise HTTPException(400, f"Invalid regex: {exc}")

    rule = UserRule(
        match_type=body.match_type,
        pattern=body.pattern,
        category=body.category,
        min_cents=body.min_cents,
        max_cents=body.max_cents,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return RuleOut.model_validate(rule)


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    """Delete a saved rule."""
    rule = session.get(UserRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    session.delete(rule)
    session.commit()
    return {"ok": True}


@router.post("/test", response_model=RuleTestResult)
def test_rule(body: RuleCreate, session: Session = Depends(get_session)):
    """
    Test what merchant_keys a proposed rule would match
    against existing transactions in the database.
    """
    txns = session.exec(select(Transaction)).all()
    matched_keys: set[str] = set()

    for t in txns:
        key = t.merchant_key
        if not key:
            continue

        if body.match_type == "exact":
            if key == body.pattern.upper():
                matched_keys.add(key)
        elif body.match_type == "contains":
            if body.pattern.upper() in key:
                matched_keys.add(key)
        elif body.match_type == "regex":
            try:
                if re.search(body.pattern, key, re.I):
                    matched_keys.add(key)
            except re.error:
                pass

    return RuleTestResult(
        pattern=body.pattern,
        would_match=sorted(matched_keys),
    )
