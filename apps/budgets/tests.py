from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.categories.models import Category
from .models import Budget
from apps.transactions.models import Transaction
from apps.accounts.models import Account
from datetime import date

class BudgetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "testpass123")
        self.category = Category.objects.create(user=self.user, name="Groceries", category_type="expense")
        self.budget = Budget.objects.create(
            user=self.user, category=self.category, month=date(2025, 1, 1), amount=400
        )
        self.account = Account.objects.create(user=self.user, name="Checking", account_type="checking")
        self.transaction = Transaction.objects.create(
            user=self.user, account=self.account, category=self.category,
            amount=100, date=date(2025, 1, 10)
        )

    def test_budget_list_requires_login(self):
        response = self.client.get(reverse("list_budgets"))
        self.assertEqual(response.status_code, 302)

    def test_budget_list_for_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("list_budgets"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Groceries")

    def test_create_budget(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("create_budget"), {
            "category": self.category.id,
            "month": "2025-02-01",
            "amount": 500,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Budget.objects.filter(category=self.category, amount=500).exists())

    def test_budget_summary(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("budget_summary"), {"month": "2025-01"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Groceries")
        self.assertContains(response, "100")
