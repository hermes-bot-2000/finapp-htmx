from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import Account
from apps.categories.models import Category
from apps.budgets.models import Budget
from apps.transactions.models import Transaction
from datetime import date

class DashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "testpass123")
        self.account = Account.objects.create(user=self.user, name="Checking", account_type="checking", balance=1000)
        self.category = Category.objects.create(user=self.user, name="Groceries", category_type="expense")
        self.budget = Budget.objects.create(user=self.user, category=self.category, month=date(2025, 1, 1), amount=400)
        self.transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=50, date=date(2025, 1, 15), description="Walmart"
        )

    def test_dashboard_loads_for_anonymous(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_net_worth_when_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1000")

    def test_dashboard_net_worth_subtracts_liabilities(self):
        """R1: credit-card/loan balances reduce net worth via signed_balance."""
        Account.objects.create(
            user=self.user, name="Visa", account_type="credit_card", balance=400
        )
        self.client.force_login(self.user)
        # Checking 1000 (asset) + Visa 400 (liability) => net worth 600
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "600")

    def test_dashboard_excludes_accounts_opted_out_of_totals(self):
        Account.objects.create(
            user=self.user, name="Hidden", account_type="checking",
            balance=999, include_in_totals=False,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        # Net worth stays at the single included account (1000), not 1099.
        self.assertContains(response, "1000")
        self.assertNotContains(response, "1099")

    def test_dashboard_shows_recent_transactions_when_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Walmart")

    def test_dashboard_shows_budget_summary_when_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Groceries")
