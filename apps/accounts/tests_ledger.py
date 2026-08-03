"""F1: account balance must be derived from the ledger, not hand-entered.

RED first: these assertions fail against the stored-``balance`` model.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import Account
from apps.transactions.models import Transaction


class ComputedBalanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ledger", "l@test.com", "pw")
        self.account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking",
            opening_balance=Decimal("1000.00"),
        )

    def _tx(self, amount, ttype, **kw):
        return Transaction.objects.create(
            user=self.user, account=self.account, amount=Decimal(amount),
            date=date(2026, 1, 15), transaction_type=ttype, **kw
        )

    def test_opening_balance_with_no_transactions(self):
        self.assertEqual(self.account.computed_balance, Decimal("1000.00"))

    def test_expense_reduces_balance(self):
        self._tx("200.00", "expense")
        self.assertEqual(self.account.computed_balance, Decimal("800.00"))

    def test_income_increases_balance(self):
        self._tx("2500.00", "income")
        self.assertEqual(self.account.computed_balance, Decimal("3500.00"))

    def test_mixed_ledger(self):
        self._tx("2500.00", "income")
        self._tx("200.00", "expense")
        self._tx("50.00", "expense")
        self.assertEqual(self.account.computed_balance, Decimal("3250.00"))

    def test_transfers_are_excluded_from_this_accounts_arithmetic(self):
        # Transfers are not yet paired (F13); they must not silently move money.
        self._tx("300.00", "transfer")
        self.assertEqual(self.account.computed_balance, Decimal("1000.00"))

    def test_deleting_a_transaction_restores_balance(self):
        tx = self._tx("200.00", "expense")
        tx.delete()
        self.assertEqual(self.account.computed_balance, Decimal("1000.00"))

    def test_balance_property_is_the_computed_one(self):
        self._tx("200.00", "expense")
        self.assertEqual(self.account.balance, Decimal("800.00"))

    def test_liability_charges_increase_amount_owed(self):
        card = Account.objects.create(
            user=self.user, name="Visa", account_type="credit_card",
            opening_balance=Decimal("100.00"), credit_limit=Decimal("1000.00"),
        )
        Transaction.objects.create(
            user=self.user, account=card, amount=Decimal("250.00"),
            date=date(2026, 1, 15), transaction_type="expense",
        )
        # Owed goes up on spend, down on payment (income).
        self.assertEqual(card.computed_balance, Decimal("350.00"))
        self.assertEqual(card.signed_balance, Decimal("-350.00"))
        self.assertEqual(card.available_balance, Decimal("650.00"))

    def test_set_current_balance_reconciles_opening(self):
        """Bank-reported balance is authoritative; opening absorbs the delta."""
        self._tx("200.00", "expense")
        self.account.set_current_balance(Decimal("1234.56"))
        self.account.refresh_from_db()
        self.assertEqual(self.account.computed_balance, Decimal("1234.56"))
        self.assertEqual(self.account.opening_balance, Decimal("1434.56"))


class NetWorthTests(TestCase):
    def test_dashboard_net_worth_follows_the_ledger(self):
        user = User.objects.create_user("nw", "nw@test.com", "pw")
        acct = Account.objects.create(
            user=user, name="Checking", account_type="checking",
            opening_balance=Decimal("1000.00"),
        )
        Transaction.objects.create(
            user=user, account=acct, amount=Decimal("400.00"),
            date=date(2026, 1, 15), transaction_type="expense",
        )
        self.client.force_login(user)
        resp = self.client.get("/")
        self.assertEqual(resp.context["net_worth"], Decimal("600.00"))
