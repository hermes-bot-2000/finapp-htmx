"""F8: no plaintext account or routing numbers at rest.

The app never needs the full PAN/ABA — only enough to let a human tell two
accounts apart — so the fix is to stop storing them, not to encrypt them.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.forms import AccountForm
from apps.accounts.models import Account


class NoSensitiveNumbersStoredTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("pci", "p@test.com", "pw")
        self.client.force_login(self.user)

    def test_routing_number_field_is_gone(self):
        self.assertNotIn(
            "routing_number", [f.name for f in Account._meta.get_fields()]
        )

    def test_full_account_number_field_is_gone(self):
        self.assertNotIn(
            "account_number", [f.name for f in Account._meta.get_fields()]
        )

    def test_only_last_four_is_stored(self):
        account = Account.objects.create(
            user=self.user, name="Checking", account_type="checking",
            account_number_last4="6789",
        )
        account.refresh_from_db()
        self.assertEqual(account.account_number_last4, "6789")
        self.assertEqual(account.masked_account_number, "••••6789")

    def test_masked_number_is_blank_when_unset(self):
        account = Account.objects.create(
            user=self.user, name="Cash", account_type="cash"
        )
        self.assertEqual(account.masked_account_number, "")

    def test_form_keeps_only_the_last_four_digits_of_a_full_number(self):
        """A user pasting a full number must not persist it."""
        form = AccountForm(data={
            "name": "Checking", "account_type": "checking",
            "opening_balance": "0", "account_number_last4": "123456789",
            "is_active": "on", "include_in_totals": "on",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["account_number_last4"], "6789")

    def test_form_rejects_non_digits(self):
        form = AccountForm(data={
            "name": "Checking", "account_type": "checking",
            "opening_balance": "0", "account_number_last4": "abcd",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("account_number_last4", form.errors)

    def test_form_does_not_expose_a_routing_number_input(self):
        self.assertNotIn("routing_number", AccountForm().fields)

    def test_create_view_stores_only_last_four(self):
        resp = self.client.post(reverse("create_account"), {
            "name": "Savings", "account_type": "savings",
            "opening_balance": "100.00", "account_number_last4": "987654321",
            "is_active": "on", "include_in_totals": "on",
        })
        self.assertEqual(resp.status_code, 302)
        account = Account.objects.get(name="Savings")
        self.assertEqual(account.account_number_last4, "4321")

    def test_list_page_never_renders_a_full_number(self):
        Account.objects.create(
            user=self.user, name="Checking", account_type="checking",
            account_number_last4="6789",
        )
        resp = self.client.get(reverse("list_accounts"))
        self.assertContains(resp, "6789")
        self.assertNotContains(resp, "123456789")
