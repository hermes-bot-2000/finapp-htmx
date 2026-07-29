from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Account

class AccountTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "testpass123")
        self.account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking", balance=1000
        )

    def test_account_list_requires_login(self):
        response = self.client.get(reverse("list_accounts"))
        self.assertEqual(response.status_code, 302)

    def test_account_list_for_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("list_accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Checking")

    def test_create_account(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("create_account"), {
            "name": "Savings",
            "account_type": "savings",
            "balance": 5000,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Account.objects.filter(name="Savings").exists())
