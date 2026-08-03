"""F1/F2: importing rows must move the account balance, with correct signs."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.integrations.importers import import_statement_rows
from apps.transactions.models import Transaction


class ImportLedgerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("imp", "i@test.com", "pw")
        self.account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking",
            opening_balance=Decimal("1000.00"),
        )

    def test_positive_row_imports_as_income(self):
        imported, errors = import_statement_rows(self.user, self.account, [
            {"date": "2026-01-16", "description": "ACME PAYROLL DIRECT DEP", "amount": "2500.00"},
        ])
        self.assertEqual((imported, errors), (1, []))
        tx = Transaction.objects.get(user=self.user)
        self.assertEqual(tx.transaction_type, "income")
        self.assertEqual(tx.amount, Decimal("2500.00"))

    def test_negative_row_imports_as_expense(self):
        import_statement_rows(self.user, self.account, [
            {"date": "2026-01-15", "description": "WHOLE FOODS MARKET", "amount": "-52.30"},
        ])
        tx = Transaction.objects.get(user=self.user)
        self.assertEqual(tx.transaction_type, "expense")
        self.assertEqual(tx.amount, Decimal("52.30"))

    def test_category_of_the_wrong_type_is_not_attached(self):
        Category.objects.create(user=self.user, name="Payroll", category_type="expense")
        import_statement_rows(self.user, self.account, [
            {"date": "2026-01-16", "description": "PAYROLL DEPOSIT", "amount": "1200.00"},
        ])
        tx = Transaction.objects.get(user=self.user)
        self.assertEqual(tx.transaction_type, "income")
        self.assertIsNone(tx.category)

    def test_import_moves_the_account_balance(self):
        import_statement_rows(self.user, self.account, [
            {"date": "2026-01-15", "description": "WHOLE FOODS MARKET", "amount": "-52.30"},
            {"date": "2026-01-16", "description": "ACME PAYROLL DIRECT DEP", "amount": "2500.00"},
        ])
        self.assertEqual(self.account.computed_balance, Decimal("3447.70"))
