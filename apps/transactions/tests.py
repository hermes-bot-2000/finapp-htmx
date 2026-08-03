from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import Account
from apps.categories.models import Category
from .models import Transaction
from datetime import date


class TransactionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "testpass123")
        self.account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking", opening_balance=1000
        )
        self.category = Category.objects.create(
            user=self.user, name="Groceries", category_type="expense"
        )
        self.transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=50, date=date(2025, 1, 15), description="Walmart"
        )

    def test_transaction_list_requires_login(self):
        response = self.client.get(reverse("list_transactions"))
        self.assertEqual(response.status_code, 302)

    def test_transaction_list_for_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("list_transactions"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Walmart")

    def test_filter_by_date(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("list_transactions"), {"date_from": "2025-01-01"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Walmart")

    def test_create_transaction(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("create_transaction"), {
            "account": self.account.id,
            "category": self.category.id,
            "amount": 75,
            "date": "2025-01-20",
            "description": "Target",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Transaction.objects.filter(description="Target").exists())

    def test_transaction_type_auto_derived_from_category(self):
        """Transaction type should be auto-derived from category type on save."""
        transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=25, date=date(2025, 1, 16), description="Test"
        )
        self.assertEqual(transaction.transaction_type, "expense")

    def test_transaction_with_payee_and_memo(self):
        transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=30, date=date(2025, 1, 17), description="Test",
            payee="Amazon", memo="Order #12345"
        )
        self.assertEqual(transaction.payee, "Amazon")
        self.assertEqual(transaction.memo, "Order #12345")

    def test_transaction_recurring(self):
        transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=100, date=date(2025, 1, 1), description="Rent",
            is_recurring=True, recurring_frequency="monthly"
        )
        self.assertTrue(transaction.is_recurring)
        self.assertEqual(transaction.recurring_frequency, "monthly")

    def test_transaction_reconciled(self):
        transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=50, date=date(2025, 1, 15), description="Walmart",
            is_reconciled=True, reconciled_date=date(2025, 1, 31)
        )
        self.assertTrue(transaction.is_reconciled)
        self.assertEqual(transaction.reconciled_date, date(2025, 1, 31))

    def test_transaction_tags(self):
        transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=50, date=date(2025, 1, 15), description="Walmart",
            tags="groceries,food"
        )
        self.assertEqual(transaction.tag_list, ["groceries", "food"])

    def test_transaction_pending(self):
        transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=50, date=date(2025, 1, 15), description="Walmart",
            pending=True
        )
        self.assertTrue(transaction.pending)

    def test_amount_is_stored_positive_regardless_of_input_sign(self):
        """R1: income/expense amounts are stored positive; sign lives in type."""
        t = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=-99.99, date=date(2025, 1, 18), description="Neg input",
        )
        self.assertEqual(t.amount, 99.99)
        self.assertEqual(t.transaction_type, "expense")


class AccountBalanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u2", "u2@test.com", "testpass123")

    def test_signed_balance_liability_is_negative(self):
        from decimal import Decimal
        cc = Account.objects.create(
            user=self.user, name="Visa", account_type="credit_card", opening_balance=500
        )
        self.assertEqual(cc.signed_balance, Decimal("-500"))

    def test_signed_balance_asset_is_positive(self):
        from decimal import Decimal
        chk = Account.objects.create(
            user=self.user, name="Checking", account_type="checking", opening_balance=1000
        )
        self.assertEqual(chk.signed_balance, Decimal("1000"))
