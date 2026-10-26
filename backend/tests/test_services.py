import pytest

from app.services import InvalidInputError, NotFoundError
from tests.conftest import SAMPLES, csv_bytes


def by_desc(statement, needle):
    return [t for t in statement.transactions if needle in t.description]


def test_import_and_summary(service):
    sid = service.import_statement(
        "s.csv",
        csv_bytes(
            "Date,Description,Amount",
            "01/03/2026,SHELL OIL 57444,-45.20",
            "01/04/2026,AUTOZONE RETURN,24.00",
            "01/05/2026,AUTOZONE #33,-100.00",
            "01/06/2026,UBER USA EDI PYMNTS,600.00",
            "01/07/2026,TRANSFER TO SAVINGS,-500.00",
            "01/08/2026,KROGER,-20.00",
            "01/09/2026,LUCKY STAR LLC,-42.00",
        ),
    )
    s = service.get_statement(sid).summary
    assert s.income_cents == 60000
    # fuel 45.20 + maintenance (100 - 24 refund) = 121.20
    assert s.deductible_expenses_cents == 12120
    assert s.net_profit_cents == 60000 - 12120
    assert s.personal_cents == 2000
    assert s.transfers_out_cents == 50000
    assert s.needs_review_count == 1 and s.needs_review_cents == 4200
    maintenance = next(c for c in s.categories if c.category == "vehicle_maintenance")
    assert maintenance.total_cents == 7600 and maintenance.refund_cents == 2400


def test_duplicate_rows_are_flagged(service):
    sid = service.import_statement(
        "s.csv",
        csv_bytes(
            "Date,Description,Amount",
            "01/23/2026,COSTCO GAS #0144,-58.77",
            "01/23/2026,COSTCO GAS #0144,-58.77",
        ),
    )
    first, second = service.get_statement(sid).transactions
    assert first.status == "auto"
    assert second.status == "needs_review" and "possible_duplicate" in second.flags


def test_overlapping_statements_are_flagged(service):
    data = csv_bytes("Date,Description,Amount", "01/03/2026,SHELL OIL,-45.20")
    service.import_statement("a.csv", data)
    sid = service.import_statement("b.csv", data)
    (tx,) = service.get_statement(sid).transactions
    assert tx.status == "needs_review" and "already_imported" in tx.flags


def test_fixing_a_row_learns_and_reapplies(service):
    sid = service.import_statement(
        "s.csv",
        csv_bytes(
            "Date,Description,Amount",
            "01/03/2026,SQ *JOES CAFE 9921,-6.75",
            "01/10/2026,SQ *JOES CAFE 9921,-7.25",
            "01/11/2026,SQ *JOES CAFE 9921,-7.25",  # different date, not a duplicate
        ),
    )
    rows = service.get_statement(sid).transactions
    assert all(t.status == "needs_review" for t in rows)

    updated = service.update_transaction(sid, rows[0].id, "personal", remember=True)
    first, *others = updated.transactions
    assert first.status == "reviewed" and first.category == "personal"
    assert all(t.category == "personal" and t.status == "auto" for t in others)
    assert all(t.source == "user_rule" for t in others)
    assert updated.summary.needs_review_count == 0

    # The rule also applies to future uploads.
    sid2 = service.import_statement(
        "next.csv", csv_bytes("Date,Description,Amount", "02/01/2026,JOES CAFE,-5.00")
    )
    assert service.get_statement(sid2).transactions[0].category == "personal"
    assert [r.merchant_key for r in service.list_rules()] == ["joes cafe"]


def test_fix_without_remember_does_not_learn(service):
    sid = service.import_statement(
        "s.csv",
        csv_bytes(
            "Date,Description,Amount",
            "01/03/2026,LUCKY STAR LLC,-6.75",
            "01/04/2026,LUCKY STAR LLC,-8.00",
        ),
    )
    a, b = service.get_statement(sid).transactions
    updated = service.update_transaction(sid, a.id, "supplies", remember=False)
    assert updated.transactions[1].status == "needs_review"
    assert service.list_rules() == []


def test_reapplied_rule_keeps_duplicate_flag(service):
    sid = service.import_statement(
        "s.csv",
        csv_bytes(
            "Date,Description,Amount",
            "01/03/2026,LUCKY STAR LLC,-6.75",
            "01/04/2026,LUCKY STAR LLC,-8.00",
            "01/04/2026,LUCKY STAR LLC,-8.00",
        ),
    )
    a, _, dup = service.get_statement(sid).transactions
    updated = service.update_transaction(sid, a.id, "supplies", remember=True)
    statuses = {t.id: t.status for t in updated.transactions}
    assert statuses[dup.id] == "needs_review"


def test_send_back_to_review(service):
    sid = service.import_statement(
        "s.csv", csv_bytes("Date,Description,Amount", "01/03/2026,SHELL OIL,-45.20")
    )
    (tx,) = service.get_statement(sid).transactions
    updated = service.update_transaction(sid, tx.id, None, remember=False)
    assert updated.transactions[0].status == "needs_review"
    assert updated.transactions[0].engine_category == "fuel"


def test_invalid_updates(service):
    sid = service.import_statement(
        "s.csv", csv_bytes("Date,Description,Amount", "01/03/2026,SHELL OIL,-45.20")
    )
    (tx,) = service.get_statement(sid).transactions
    with pytest.raises(InvalidInputError):
        service.update_transaction(sid, tx.id, "not_a_category", remember=False)
    with pytest.raises(NotFoundError):
        service.update_transaction(sid, 9999, "fuel", remember=False)
    with pytest.raises(NotFoundError):
        service.get_statement(9999)


def test_export_csv_contains_rows_and_summary(service):
    sid = service.import_statement("c.csv", (SAMPLES / "gig_driver_checking.csv").read_bytes())
    content = service.export_csv(sid)
    assert content.startswith("Date,Description,Merchant,Amount,Category")
    assert "NEEDS REVIEW" in content
    assert "Estimated net profit" in content


def test_export_neutralises_spreadsheet_formulas(service):
    sid = service.import_statement(
        "s.csv", csv_bytes("Date,Description,Amount", '01/03/2026,"=HYPERLINK(""x"")",-1.00')
    )
    assert "'=HYPERLINK" in service.export_csv(sid)


def test_delete_statement(service):
    sid = service.import_statement(
        "s.csv", csv_bytes("Date,Description,Amount", "01/03/2026,SHELL OIL,-45.20")
    )
    service.delete_statement(sid)
    assert service.list_statements() == []
