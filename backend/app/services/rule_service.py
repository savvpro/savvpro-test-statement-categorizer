"""Service managing reusable merchant categorization rules and bulk recategorization.

Provides rule CRUD, priority ordering, pattern validation (including regex safety),
matching evaluation, dry-run previews, and manual-protection enforcement.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.classification_event import ClassificationEvent, ClassificationEventType
from app.models.merchant_rule import MerchantRule, RuleMatchType
from app.models.transaction import ReviewStatus, Transaction
from app.services.category_repository import CategoryRepository
from app.services.transaction_normalizer import normalize_description


@dataclass(frozen=True)
class RulePreviewItem:
    """Representation of a transaction evaluated in rule preview."""

    transaction_id: int
    transaction_date: Optional[str]
    original_description: str
    amount: float
    current_category_name: str
    new_category_name: str
    is_manual: bool
    status: str  # 'eligible', 'protected_manual', 'already_matching'


class RuleService:
    """Service for merchant rule management and bulk recategorization."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.cat_repo = CategoryRepository(session)

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate_rule(
        self,
        merchant_pattern: str,
        match_type: str,
        category_id: int,
        priority: int = 100,
    ) -> Tuple[str, str, int, int]:
        """Validate rule parameters.

        Returns:
            Tuple of sanitized (merchant_pattern, match_type, category_id, priority).

        Raises:
            ValueError on invalid input.
        """
        if not merchant_pattern or not merchant_pattern.strip():
            raise ValueError("Merchant pattern cannot be empty.")

        cleaned_pattern = merchant_pattern.strip()

        # Validate match type
        norm_match_type = match_type.strip().upper() if match_type else RuleMatchType.CONTAINS
        if norm_match_type not in RuleMatchType.ALL:
            raise ValueError(
                f"Invalid match type '{match_type}'. Must be one of: {RuleMatchType.ALL}"
            )

        # Validate regex syntax if match_type is REGEX
        if norm_match_type == RuleMatchType.REGEX:
            try:
                re.compile(cleaned_pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(
                    f"Invalid regular expression syntax in pattern '{cleaned_pattern}': {exc}"
                )

        # Validate category exists
        cat = self.cat_repo.get_by_id(category_id)
        if not cat:
            raise ValueError(f"Category with ID {category_id} does not exist.")

        # Validate priority
        safe_priority = max(1, min(int(priority), 10000))

        return cleaned_pattern, norm_match_type, category_id, safe_priority

    # -----------------------------------------------------------------------
    # CRUD Operations
    # -----------------------------------------------------------------------

    def create_rule(
        self,
        merchant_pattern: str,
        category_id: int,
        match_type: str = RuleMatchType.CONTAINS,
        priority: int = 100,
        is_active: bool = True,
    ) -> MerchantRule:
        """Create and persist a new merchant categorization rule."""
        pattern, mtype, cat_id, prio = self.validate_rule(
            merchant_pattern=merchant_pattern,
            match_type=match_type,
            category_id=category_id,
            priority=priority,
        )

        rule = MerchantRule(
            merchant_pattern=pattern,
            match_type=mtype,
            category_id=cat_id,
            priority=prio,
            is_active=bool(is_active),
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def get_rule(self, rule_id: int) -> Optional[MerchantRule]:
        """Fetch rule by ID with eager-loaded Category."""
        stmt = (
            select(MerchantRule)
            .options(joinedload(MerchantRule.category))
            .where(MerchantRule.id == rule_id)
        )
        return self.session.execute(stmt).scalars().first()

    def list_rules(self, active_only: bool = False) -> List[MerchantRule]:
        """List rules ordered by priority descending, then creation order ascending."""
        stmt = select(MerchantRule).options(joinedload(MerchantRule.category))
        if active_only:
            stmt = stmt.where(MerchantRule.is_active.is_(True))

        stmt = stmt.order_by(MerchantRule.priority.desc(), MerchantRule.id.asc())
        return list(self.session.execute(stmt).scalars().all())

    def update_rule(
        self,
        rule_id: int,
        merchant_pattern: Optional[str] = None,
        category_id: Optional[int] = None,
        match_type: Optional[str] = None,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> MerchantRule:
        """Update fields of an existing rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found.")

        new_pattern = merchant_pattern if merchant_pattern is not None else rule.merchant_pattern
        new_mtype = match_type if match_type is not None else rule.match_type
        new_cat_id = category_id if category_id is not None else rule.category_id
        new_prio = priority if priority is not None else rule.priority

        pat, mtype, cat_id, prio = self.validate_rule(
            merchant_pattern=new_pattern,
            match_type=new_mtype,
            category_id=new_cat_id,
            priority=new_prio,
        )

        rule.merchant_pattern = pat
        rule.match_type = mtype
        rule.category_id = cat_id
        rule.priority = prio

        if is_active is not None:
            rule.is_active = bool(is_active)

        self.session.flush()
        return rule

    def toggle_rule(self, rule_id: int) -> MerchantRule:
        """Toggle active status of a rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule with ID {rule_id} not found.")
        rule.is_active = not rule.is_active
        self.session.flush()
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """Safely delete a rule without deleting past transactions."""
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        self.session.delete(rule)
        self.session.flush()
        return True

    # -----------------------------------------------------------------------
    # Pattern Matching Evaluation
    # -----------------------------------------------------------------------

    @staticmethod
    def matches_transaction(rule: MerchantRule, tx: Transaction) -> bool:
        """Evaluate if a rule matches a transaction deterministically.

        Checks against normalized description and raw description.
        """
        pattern = rule.merchant_pattern
        mtype = rule.match_type
        norm_desc = (tx.normalized_description or normalize_description(tx.original_description)).upper()
        raw_desc = (tx.original_description or "").upper()

        if mtype == RuleMatchType.EXACT:
            target = pattern.strip().upper()
            return norm_desc == target or raw_desc == target

        if mtype == RuleMatchType.CONTAINS:
            target = pattern.strip().upper()
            return target in norm_desc or target in raw_desc

        if mtype == RuleMatchType.REGEX:
            try:
                rx = re.compile(pattern, re.IGNORECASE)
                return bool(rx.search(norm_desc) or rx.search(raw_desc))
            except re.error:
                return False

        return False

    # -----------------------------------------------------------------------
    # Bulk Recategorization (Preview & Apply)
    # -----------------------------------------------------------------------

    def preview_recategorization(
        self,
        rule_or_id: Any,
        override_manual: bool = False,
    ) -> Dict[str, Any]:
        """Dry-run preview of matching transactions for a rule.

        Identifies:
        - Eligible transactions to be updated
        - Manually categorized transactions protected from overwriting
        - Transactions already categorized with target category
        """
        rule = rule_or_id if isinstance(rule_or_id, MerchantRule) else self.get_rule(rule_or_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_or_id}")

        target_cat = self.cat_repo.get_by_id(rule.category_id)
        target_name = target_cat.name if target_cat else "Unknown Category"

        # Fetch all transactions to evaluate matches
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.category))
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        )
        all_txs = list(self.session.execute(stmt).scalars().all())

        matching_items: List[RulePreviewItem] = []
        eligible_count = 0
        protected_count = 0
        already_matching_count = 0

        for tx in all_txs:
            if not self.matches_transaction(rule, tx):
                continue

            current_cat_name = tx.category.name if tx.category else "Needs Review"
            is_manual = bool(tx.was_manually_categorized)

            if is_manual and not override_manual:
                status = "protected_manual"
                protected_count += 1
            elif tx.category_id == rule.category_id:
                status = "already_matching"
                already_matching_count += 1
            else:
                status = "eligible"
                eligible_count += 1

            matching_items.append(
                RulePreviewItem(
                    transaction_id=tx.id,
                    transaction_date=tx.transaction_date.isoformat() if tx.transaction_date else None,
                    original_description=tx.original_description,
                    amount=float(tx.amount),
                    current_category_name=current_cat_name,
                    new_category_name=target_name,
                    is_manual=is_manual,
                    status=status,
                )
            )

        return {
            "rule_id": rule.id,
            "merchant_pattern": rule.merchant_pattern,
            "match_type": rule.match_type,
            "target_category_id": rule.category_id,
            "target_category_name": target_name,
            "total_matches": len(matching_items),
            "eligible_count": eligible_count,
            "protected_count": protected_count,
            "already_matching_count": already_matching_count,
            "override_manual": override_manual,
            "items": matching_items[:100],  # Bounded preview list
        }

    def apply_recategorization(
        self,
        rule_or_id: Any,
        override_manual: bool = False,
    ) -> Dict[str, Any]:
        """Apply a merchant rule in bulk to matching transactions.

        Strict protection:
        - Manually categorized transactions are NEVER overwritten by default.
        - Any overwrite requires explicit `override_manual=True`.
        - All modifications generate audit classification events.
        """
        rule = rule_or_id if isinstance(rule_or_id, MerchantRule) else self.get_rule(rule_or_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_or_id}")

        target_cat = self.cat_repo.get_by_id(rule.category_id)
        target_name = target_cat.name if target_cat else "Unknown Category"

        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.category))
            .order_by(Transaction.id)
        )
        all_txs = list(self.session.execute(stmt).scalars().all())

        updated_count = 0
        protected_count = 0
        already_matching_count = 0

        for tx in all_txs:
            if not self.matches_transaction(rule, tx):
                continue

            # Protection check
            if tx.was_manually_categorized and not override_manual:
                protected_count += 1
                continue

            if tx.category_id == rule.category_id:
                already_matching_count += 1
                continue

            old_category_id = tx.category_id

            # Apply rule reclassification
            tx.category_id = rule.category_id
            tx.confidence_score = 1.0  # Explicit merchant rule match
            tx.classification_reason = (
                f"Rule #{rule.id} match: '{rule.merchant_pattern}' ({rule.match_type})"
            )
            tx.review_status = ReviewStatus.REVIEWED

            if override_manual and tx.was_manually_categorized:
                # Retain manual flag if overwritten
                tx.was_manually_categorized = True

            # Record audit event
            event = ClassificationEvent(
                transaction_id=tx.id,
                previous_category_id=old_category_id,
                new_category_id=rule.category_id,
                event_type=ClassificationEventType.RULE_RECLASSIFICATION,
                reason=f"Bulk recategorized by rule #{rule.id} ({rule.merchant_pattern})",
            )
            self.session.add(event)
            updated_count += 1

        self.session.flush()

        return {
            "rule_id": rule.id,
            "merchant_pattern": rule.merchant_pattern,
            "target_category_name": target_name,
            "updated_count": updated_count,
            "protected_count": protected_count,
            "already_matching_count": already_matching_count,
            "override_manual": override_manual,
        }
