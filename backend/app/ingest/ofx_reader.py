"""OFX reader: own SGML (v1) tokenizer, defusedxml for v2. No entity expansion, bounded work."""

import re
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ParseError as XmlParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring as safe_fromstring

from app.core.errors import ParseError
from app.domain.enums import AccountType
from app.domain.models import ParseResult, ParseWarning, RawTransaction
from app.ingest import amounts, dates
from app.ingest.common import RowError, enforce_failure_policy

MAX_DEPTH = 32
MAX_TOKENS = 500_000
_TOKEN_RE = re.compile(r"<(/?)([A-Za-z0-9.]+)>([^<]*)")
_CLOSE_RE = re.compile(r"</([A-Za-z0-9.]+)>")
_DTD_RE = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)


@dataclass(slots=True)
class Node:
    tag: str
    text: str = ""
    children: list["Node"] = field(default_factory=list)


def _unescape(text: str) -> str:
    return text.strip().replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _depth_error() -> ParseError:
    return ParseError(f"OFX nesting deeper than {MAX_DEPTH}", code="OFX_TOO_DEEP")


def parse_sgml(text: str) -> Node:
    """Build a tree from OFX 1.x. Leaf elements carry text and have no close tag."""
    start = text.upper().find("<OFX>")
    if start < 0:
        raise ParseError("No <OFX> element found", code="INVALID_OFX")
    closing_tags = {m.upper() for m in _CLOSE_RE.findall(text, start)}
    root = Node("ROOT")
    stack: list[Node] = [root]
    tokens = 0
    for m in _TOKEN_RE.finditer(text, start):
        tokens += 1
        if tokens > MAX_TOKENS:
            raise ParseError("OFX file has too many elements", code="OFX_TOO_LARGE")
        closing, tag, value = m.group(1), m.group(2).upper(), _unescape(m.group(3))
        if closing:
            for i in range(len(stack) - 1, 0, -1):
                if stack[i].tag == tag:
                    del stack[i:]
                    break
            continue
        node = Node(tag, value)
        stack[-1].children.append(node)
        if not value and tag in closing_tags:
            stack.append(node)
            if len(stack) - 1 > MAX_DEPTH:
                raise _depth_error()
    return root


def parse_xml(text: str) -> Node:
    try:
        element = safe_fromstring(text)
    except DefusedXmlException as exc:
        raise ParseError("OFX contains unsafe XML (DTD/entities)", code="UNSAFE_XML") from exc
    except (XmlParseError, ValueError) as exc:
        raise ParseError("OFX XML is not well formed", code="INVALID_OFX") from exc
    return _convert(element)


def _convert(element: Element) -> Node:
    root = Node(_local(element.tag), (element.text or "").strip())
    work: list[tuple[Element, Node, int]] = [(element, root, 1)]
    tokens = 0
    while work:
        el, node, depth = work.pop()
        if depth > MAX_DEPTH:
            raise _depth_error()
        for child in el:
            tokens += 1
            if tokens > MAX_TOKENS:
                raise ParseError("OFX file has too many elements", code="OFX_TOO_LARGE")
            c = Node(_local(child.tag), _unescape_xml(child.text))
            node.children.append(c)
            work.append((child, c, depth + 1))
    return root


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].upper()


def _unescape_xml(text: str | None) -> str:
    return (text or "").strip()


def _walk(root: Node) -> list[Node]:
    out: list[Node] = []
    stack = [root]
    while stack:
        n = stack.pop()
        out.append(n)
        stack.extend(reversed(n.children))
    return out


def _child(node: Node, tag: str) -> str | None:
    for c in node.children:
        if c.tag == tag and c.text:
            return c.text
    return None


def _nested(node: Node, outer: str, inner: str) -> str | None:
    for c in node.children:
        if c.tag == outer:
            return _child(c, inner)
    return None


def parse_ofx(text: str, *, max_rows: int) -> ParseResult:
    if _DTD_RE.search(text):
        raise ParseError("OFX contains a DOCTYPE/ENTITY declaration", code="UNSAFE_XML")
    head = text.lstrip()[:100].lower()
    is_xml = head.startswith("<?xml") or head.startswith("<?ofx")
    root = parse_xml(text) if is_xml else parse_sgml(text)
    nodes = _walk(root)

    hint = AccountType.CHECKING
    if any(n.tag in {"CREDITCARDMSGSRSV1", "CCSTMTRS", "CCACCTFROM"} for n in nodes):
        hint = AccountType.CREDIT_CARD
    stmttrns = [n for n in nodes if n.tag == "STMTTRN"]
    if len(stmttrns) > max_rows:
        raise ParseError(f"More than {max_rows} transactions", code="ROW_LIMIT")

    rows: list[RawTransaction] = []
    errors: list[RowError] = []
    warnings: list[ParseWarning] = []
    curdef = _curdef(nodes)
    for n, trn in enumerate(stmttrns, start=1):
        posted = _child(trn, "DTPOSTED") or ""
        amount = _child(trn, "TRNAMT")
        err = _validate(posted, amount)
        if err:
            errors.append(RowError(n, err[0], err[1]))
            continue
        trntype = _child(trn, "TRNTYPE")
        name = _child(trn, "NAME") or _nested(trn, "PAYEE", "NAME")
        memo = _child(trn, "MEMO")
        checknum = _child(trn, "CHECKNUM")
        description = name
        if not description:
            if memo:
                description, memo = memo, None
            elif checknum:
                description = f"CHECK #{checknum}"
            else:
                description = trntype or "UNKNOWN"
                warnings.append(
                    ParseWarning("NO_DESCRIPTION", "Transaction has no NAME or MEMO", n)
                )
        extra = {k: v for k, v in (("CHECKNUM", checknum), ("CURDEF", curdef)) if v}
        rows.append(
            RawTransaction(
                row_index=n,
                date_raw=posted,
                description_raw=description,
                amount_raw=amount,
                memo_raw=memo,
                type_raw=trntype,
                fitid=_child(trn, "FITID"),
                extra=extra,
            )
        )
    enforce_failure_policy(errors, len(rows))
    warnings.extend(ParseWarning(e.code, e.message, e.row_index) for e in errors)
    for r in rows:
        if dates.is_future(dates.parse_ofx_date(r.date_raw)):
            warnings.append(ParseWarning("FUTURE_DATE", "Date is in the future", r.row_index))
    return ParseResult(
        rows=tuple(rows),
        warnings=tuple(warnings),
        date_format="ofx",
        account_type_hint=hint,
    )


def _curdef(nodes: list[Node]) -> str | None:
    for n in nodes:
        if n.tag == "CURDEF" and n.text:
            return n.text
    return None


def _validate(posted: str, amount: str | None) -> tuple[str, str] | None:
    try:
        dates.parse_ofx_date(posted)
    except dates.DateError as exc:
        return exc.code, str(exc)
    if amount is None:
        return "EMPTY_AMOUNT", "TRNAMT missing"
    try:
        amounts.parse_amount(amount)
    except amounts.AmountError as exc:
        return exc.code, str(exc)
    return None
