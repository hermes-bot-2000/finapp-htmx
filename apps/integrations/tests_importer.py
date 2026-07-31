"""TDD: bank statement CSV parsing + transaction import (RED first)."""
import csv
import io

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.transactions.models import Transaction
from apps.integrations.importers import (
    parse_bank_statement,
    import_statement_rows,
)


def _write_csv(rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


class ParseBankStatementTests(TestCase):
    def test_parses_standard_csv_columns(self):
        csv_text = _write_csv([
            ["Date", "Description", "Amount", "Balance"],
            ["2025-01-15", "WHOLE FOODS MARKET", "-52.30", "1200.00"],
            ["2025-01-16", "PAYROLL DIRECT DEPOSIT", "2500.00", "3700.00"],
        ])
        rows = parse_bank_statement(csv_text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], "2025-01-15")
        self.assertEqual(rows[0]["description"], "WHOLE FOODS MARKET")
        self.assertEqual(rows[0]["amount"], "-52.30")
        self.assertEqual(rows[1]["amount"], "2500.00")

    def test_parses_alternative_headers(self):
        csv_text = _write_csv([
            ["Transaction Date", "Details", "Debit", "Credit"],
            ["01/20/2025", "STARBUCKS", "4.75", ""],
            ["01/21/2025", "EMPLOYER ACH", "", "1800.00"],
        ])
        rows = parse_bank_statement(csv_text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], "01/20/2025")
        self.assertEqual(rows[0]["description"], "STARBUCKS")
        self.assertEqual(rows[0]["amount"], "-4.75")
        self.assertEqual(rows[1]["amount"], "1800.00")

    def test_normalizes_amount_from_debit_credit_columns(self):
        csv_text = _write_csv([
            ["Date", "Description", "Debit", "Credit"],
            ["2025-02-01", "ATM WITHDRAWAL", "100.00", ""],
            ["2025-02-02", "INTEREST PAYMENT", "", "0.50"],
        ])
        rows = parse_bank_statement(csv_text)
        self.assertEqual(rows[0]["amount"], "-100.00")
        self.assertEqual(rows[1]["amount"], "0.50")

    def test_skips_blank_rows(self):
        csv_text = _write_csv([
            ["Date", "Description", "Amount", "Balance"],
            ["2025-01-15", "WALMART", "-20.00", "1000.00"],
            [],
            ["", "", "", ""],
            ["2025-01-16", "TARGET", "-15.00", "985.00"],
        ])
        rows = parse_bank_statement(csv_text)
        self.assertEqual(len(rows), 2)


class ImportStatementRowsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("imp", "imp@test.com", "pw12345")
        self.account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking", balance=0
        )
        self.expense_cat = Category.objects.create(
            user=self.user, name="Groceries", category_type="expense"
        )
        self.income_cat = Category.objects.create(
            user=self.user, name="Salary", category_type="income"
        )

    def test_import_creates_transaction_for_each_row(self):
        rows = [
            {"date": "2025-01-15", "description": "WHOLE FOODS", "amount": "-52.30"},
            {"date": "2025-01-16", "description": "PAYROLL", "amount": "2500.00"},
        ]
        imported, errors = import_statement_rows(self.user, self.account, rows)
        self.assertEqual(imported, 2)
        self.assertEqual(errors, [])
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 2)

    def test_expense_amount_stored_negative_and_typed_expense(self):
        rows = [
            {"date": "2025-01-15", "description": "WALMART", "amount": "-52.30"},
        ]
        import_statement_rows(self.user, self.account, rows)
        tx = Transaction.objects.get(description="WALMART")
        self.assertEqual(tx.amount, Decimal('-52.30'))
        self.assertEqual(tx.transaction_type, "expense")

    def test_positive_amount_typed_income(self):
        rows = [
            {"date": "2025-01-16", "description": "PAYROLL", "amount": "2500.00"},
        ]
        import_statement_rows(self.user, self.account, rows)
        tx = Transaction.objects.get(description="PAYROLL")
        self.assertEqual(tx.amount, Decimal('2500.00'))
        self.assertEqual(tx.transaction_type, "income")

    def test_import_uses_existing_matching_category_by_keyword(self):
        rows = [
            {"date": "2025-01-15", "description": "GROCERIES - WHOLE FOODS MARKET", "amount": "-52.30"},
        ]
        import_statement_rows(self.user, self.account, rows)
        tx = Transaction.objects.get(description="GROCERIES - WHOLE FOODS MARKET")
        self.assertEqual(tx.category, self.expense_cat)

    def test_import_creates_uncategorized_when_no_match(self):
        rows = [
            {"date": "2025-01-15", "description": "MYSTERY VENDOR XYZ", "amount": "-9.99"},
        ]
        import_statement_rows(self.user, self.account, rows)
        tx = Transaction.objects.get(description="MYSTERY VENDOR XYZ")
        self.assertIsNone(tx.category)
        self.assertEqual(tx.transaction_type, "expense")

    def test_import_is_idempotent_for_identical_rows(self):
        rows = [
            {"date": "2025-01-15", "description": "WALMART", "amount": "-20.00"},
        ]
        import_statement_rows(self.user, self.account, rows)
        imported, errors = import_statement_rows(self.user, self.account, rows)
        self.assertEqual(imported, 0)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 1)

    def test_import_rejects_unparseable_amount(self):
        rows = [
            {"date": "2025-01-15", "description": "BAD AMOUNT", "amount": "not-a-number"},
        ]
        imported, errors = import_statement_rows(self.user, self.account, rows)
        self.assertEqual(imported, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("BAD AMOUNT", errors[0])
