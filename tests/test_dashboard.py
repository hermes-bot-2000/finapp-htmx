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
