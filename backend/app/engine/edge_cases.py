import re

from app.models.transaction import RawTransaction, TransactionType

# Retailers that commonly mix personal and business purchases
PERSONAL_AMBIGUOUS_PATTERNS = [
    r"\bAMAZON(?:\.COM)?\b(?!.*(?:WEB SERVICES|AWS))",
    r"\bTARGET\b",
    r"\bWALMART\b",
    r"\bCOSTCO\b",
    r"\bUBER\s*EATS\b",
    r"\bDOORDASH\b",
    r"\bGRUBHUB\b",
    r"\bSTARBUCKS\b",
    r"\bCAFE\b",
    r"\bCOFFEE\b",
    r"\bRESTAURANT\b",
    r"\bBAKERY\b",
    r"\bBAR\b",
    r"\bTRADER JOE\b",
    r"\bWHOLE FOODS\b",
    r"\bSAFEWAY\b",
    r"\bKROGER\b",
    r"\bPHARMACY\b",
    r"\bCVS\b",
    r"\bWALGREENS\b",
]

# Refund / Reversal keywords
REFUND_PATTERNS = [
    r"\b(?:REFUND|REVERSAL|RETURN|CREDIT ADJ|ADJUSTMENT|DISPUTE REVERSAL|CHARGEBACK REVERSAL)\b",
]

# Internal transfers / payment markers
TRANSFER_PATTERNS = [
    r"\b(?:TRANSFER (?:TO|FROM)|AUTOPAY|PAYMENT THANK YOU|CREDIT CARD PAYMENT|"
    r"INTERNET TRANSFER|ONLINE TRANSFER|MOBILE TRANSFER|ZELLE (?:TO|FROM)|"
    r"SAVINGS TRANSFER|ACCOUNT TRANSFER|TRANSFER CREDIT|TRANSFER DEBIT)\b",
]

STOP_TOKENS = {"REFUND", "RETURN", "REVERSAL", "INC", "CORP", "LLC", "LTD", "SERVICES", "WEB", "ONLINE", "DEBIT", "CREDIT"}


def is_personal_business_ambiguous(normalized_desc: str) -> bool:
    """Detect merchants that have high likelihood of personal/business ambiguity."""
    for pattern in PERSONAL_AMBIGUOUS_PATTERNS:
        if re.search(pattern, normalized_desc, re.IGNORECASE):
            return True
    return False


def is_transfer_marker(normalized_desc: str) -> bool:
    """Detect if the description represents an internal account transfer or card payment."""
    for pattern in TRANSFER_PATTERNS:
        if re.search(pattern, normalized_desc, re.IGNORECASE):
            return True
    return False


def is_refund_marker(normalized_desc: str, transaction_type: TransactionType) -> bool:
    """
    Detect if the transaction is an explicit refund or reversal.
    Typically a credit transaction with refund keywords or reversal memo.
    """
    for pattern in REFUND_PATTERNS:
        if re.search(pattern, normalized_desc, re.IGNORECASE):
            return True
    return False


def detect_duplicates(
    transactions: list[RawTransaction], normalized_descs: list[str]
) -> set[str]:
    """
    Identifies duplicate transactions:
    Transactions with identical date, amount, and normalized merchant.
    Returns a set of transaction IDs that are duplicates (the subsequent instances).
    """
    seen: dict[tuple, str] = {}
    duplicate_ids: set[str] = set()

    for tx, norm_desc in zip(transactions, normalized_descs):
        key = (tx.date, round(abs(tx.amount), 2), tx.transaction_type, norm_desc)
        if key in seen:
            duplicate_ids.add(tx.id)
        else:
            seen[key] = tx.id

    return duplicate_ids


def find_refund_matches(
    transactions: list[RawTransaction], normalized_descs: list[str]
) -> dict[str, str]:
    """
    Links refund (credit) transactions to their original matching expense (debit).
    Looks for preceding or nearby debits with matching merchant and identical or close amount.
    Returns: mapping from refund_tx_id -> original_debit_tx_id
    """
    refund_links: dict[str, str] = {}
    debit_pool: list[tuple[int, RawTransaction, str]] = []

    for idx, (tx, norm_desc) in enumerate(zip(transactions, normalized_descs)):
        if tx.transaction_type == TransactionType.DEBIT:
            debit_pool.append((idx, tx, norm_desc))

    for idx, (tx, norm_desc) in enumerate(zip(transactions, normalized_descs)):
        if tx.transaction_type == TransactionType.CREDIT:
            is_explicit = is_refund_marker(norm_desc, tx.transaction_type)
            tx_amount = round(abs(tx.amount), 2)
            r_tokens = set(re.findall(r"\w+", norm_desc.upper())) - STOP_TOKENS

            best_match_id: str | None = None
            for d_idx, debit_tx, d_norm in debit_pool:
                debit_amount = round(abs(debit_tx.amount), 2)
                d_tokens = set(re.findall(r"\w+", d_norm.upper())) - STOP_TOKENS

                # Shared root merchant token (e.g. "AWS", "JETBRAINS")
                shared = r_tokens & d_tokens

                if shared and debit_amount == tx_amount:
                    best_match_id = debit_tx.id
                    break
                if is_explicit and shared:
                    best_match_id = debit_tx.id
                    break
                if d_norm == norm_desc and debit_amount == tx_amount:
                    best_match_id = debit_tx.id
                    break

            if best_match_id:
                refund_links[tx.id] = best_match_id

    return refund_links
