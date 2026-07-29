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
        self.account = Account.objects.create(user=self.user, name="Checking", account_type="checking", balance=1000)
        self.category = Category.objects.create(user=self.user, name="Groceries", category_type="expense")
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
