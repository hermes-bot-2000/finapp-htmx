"""TDD: bank statement upload view/form (RED first)."""
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.transactions.models import Transaction


class UploadStatementViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("up", "up@test.com", "pw12345")
        self.account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking", balance=0
        )
        Category.objects.create(user=self.user, name="Groceries", category_type="expense")

    def _csv_text(self):
        return (
            "Date,Description,Amount,Balance\n"
            "2025-01-15,GROCERIES - WHOLE FOODS,-52.30,1200.00\n"
            "2025-01-16,PAYROLL DEPOSIT,2500.00,3700.00\n"
        )

    def test_upload_page_requires_login(self):
        response = self.client.get(reverse("upload_statement"))
        self.assertEqual(response.status_code, 302)

    def test_upload_page_loads_for_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("upload_statement"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload")

    def test_post_valid_csv_creates_transactions(self):
        self.client.force_login(self.user)
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("stmt.csv", self._csv_text().encode(), content_type="text/csv")
        response = self.client.post(reverse("upload_statement"), {"account": self.account.id, "file": f})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 2)
        self.assertContains(response, "Imported 2")

    def test_post_missing_file_shows_form_error(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("upload_statement"), {"account": self.account.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")

    def test_post_valid_csv_returns_error_count(self):
        self.client.force_login(self.user)
        from django.core.files.uploadedfile import SimpleUploadedFile
        bad = "Date,Description,Amount,Balance\n2025-01-15,BADROW,notnum,0\n"
        f = SimpleUploadedFile("stmt.csv", bad.encode(), content_type="text/csv")
        response = self.client.post(reverse("upload_statement"), {"account": self.account.id, "file": f})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 error")
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)
