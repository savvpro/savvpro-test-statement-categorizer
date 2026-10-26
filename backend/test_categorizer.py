import unittest

from backend.categorizer import categorize_csv, categorize_rows, classify, parse_amount


class CategorizerTests(unittest.TestCase):
    def test_direction_normalizes_signed_amount(self):
        self.assertEqual(parse_amount("$22.50", "Debit"), -22.5)
        self.assertEqual(parse_amount("($22.50)", "Credit"), -22.5)
        self.assertEqual(parse_amount("1,200.00", "Credit"), 1200.0)

    def test_ordered_rules_handle_transfer_refund_and_income(self):
        self.assertEqual(classify("TRANSFER TO SAVINGS", -400, "Debit").category, "Transfer / non-spend")
        self.assertEqual(classify("REFUND - AIRTABLE", 24, "Credit").category, "Refund")
        self.assertEqual(classify("CLIENT PAYMENT - NORTHSTAR", 1200, "Credit").category, "Income")

    def test_known_merchants_have_explanations(self):
        decision = classify("ADOBE CREATIVE CLOUD", -59.99, "Debit")
        self.assertEqual(decision.category, "Software")
        self.assertIn("ADOBE", decision.rule_label)

    def test_unknown_and_generic_inflow_need_review(self):
        self.assertEqual(classify("JOES CAFE 9921", -18.75, "Debit").status, "needs_review")
        self.assertEqual(classify("MYSTERY DEPOSIT", 500, "Credit").category, "Needs review")

    def test_duplicate_rows_are_reviewed_instead_of_double_counted(self):
        rows = [
            {"Date": "2026-01-01", "Description": "ADOBE", "Amount": "-10"},
            {"Date": "2026-01-01", "Description": "ADOBE", "Amount": "-10"},
        ]
        result = categorize_rows(rows)
        self.assertEqual(result[0].category, "Software")
        self.assertEqual(result[1].category, "Needs review")
        self.assertIn("duplicate", (result[1].review_reason or "").lower())

    def test_csv_requires_core_headers(self):
        with self.assertRaises(ValueError):
            categorize_csv("Date,Description\n2026-01-01,Adobe\n")


if __name__ == "__main__":
    unittest.main()
