"""F4/F5: malformed query strings must not 500."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.categories.models import Category
from apps.transactions.models import Transaction


class TransactionFilterValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("filter", "f@test.com", "pw")
        self.other = User.objects.create_user("other", "o@test.com", "pw")
        self.account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking",
            opening_balance=Decimal("1000.00"),
        )
        self.category = Category.objects.create(
            user=self.user, name="Groceries", category_type="expense"
        )
        self.transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=Decimal("50.00"), date=date(2026, 1, 15), description="Walmart",
        )
        self.client.force_login(self.user)

    def test_non_numeric_category_does_not_500(self):
        resp = self.client.get(reverse("list_transactions"), {"category": "abc"})
        self.assertEqual(resp.status_code, 200)
        # The bad filter is ignored, not silently applied.
        self.assertEqual(list(resp.context["transactions"]), [self.transaction])
        self.assertTrue(resp.context["filter_errors"])

    def test_unknown_category_id_does_not_500(self):
        resp = self.client.get(reverse("list_transactions"), {"category": "999999"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["filter_errors"])

    def test_another_users_category_is_rejected(self):
        foreign = Category.objects.create(
            user=self.other, name="Theirs", category_type="expense"
        )
        resp = self.client.get(reverse("list_transactions"), {"category": foreign.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["filter_errors"])
        self.assertEqual(list(resp.context["transactions"]), [self.transaction])

    def test_malformed_dates_do_not_500(self):
        resp = self.client.get(reverse("list_transactions"), {
            "date_from": "notadate", "date_to": "13/45/2026",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["filter_errors"])
        self.assertEqual(list(resp.context["transactions"]), [self.transaction])

    def test_valid_filters_still_apply(self):
        resp = self.client.get(reverse("list_transactions"), {
            "category": self.category.pk, "date_from": "2026-01-01", "date_to": "2026-01-31",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["filter_errors"])
        self.assertEqual(list(resp.context["transactions"]), [self.transaction])

    def test_valid_filter_can_exclude(self):
        resp = self.client.get(reverse("list_transactions"), {"date_from": "2026-02-01"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context["transactions"]), [])


class BudgetSummaryValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bsum", "b@test.com", "pw")
        self.category = Category.objects.create(
            user=self.user, name="Groceries", category_type="expense"
        )
        self.budget = Budget.objects.create(
            user=self.user, category=self.category, month=date(2026, 1, 1),
            amount=Decimal("400.00"),
        )
        self.client.force_login(self.user)

    def test_malformed_month_does_not_500(self):
        resp = self.client.get(reverse("budget_summary"), {"month": "notamonth"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["filter_errors"])
        # Falls back to the current month rather than exploding.
        self.assertEqual(resp.context["month"], date.today().replace(day=1))

    def test_out_of_range_month_does_not_500(self):
        resp = self.client.get(reverse("budget_summary"), {"month": "2026-13"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["filter_errors"])

    def test_valid_month_selects_that_period(self):
        resp = self.client.get(reverse("budget_summary"), {"month": "2026-01"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["filter_errors"])
        self.assertEqual(resp.context["month"], date(2026, 1, 1))
        self.assertEqual(len(resp.context["summary"]), 1)
