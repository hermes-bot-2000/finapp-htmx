"""F3: every entity needs an update and a delete route, scoped to its owner."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.categories.models import Category
from apps.transactions.models import Transaction


class CrudTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", "o@test.com", "pw")
        self.other = User.objects.create_user("intruder", "i@test.com", "pw")
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
        self.budget = Budget.objects.create(
            user=self.user, category=self.category, month=date(2026, 1, 1),
            amount=Decimal("400.00"),
        )
        self.client.force_login(self.user)


class AccountCrudTests(CrudTestBase):
    def test_update_view_renders(self):
        resp = self.client.get(reverse("update_account", args=[self.account.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Checking")

    def test_update_changes_the_account(self):
        resp = self.client.post(reverse("update_account", args=[self.account.pk]), {
            "name": "Main Checking", "account_type": "checking",
            "opening_balance": "1500.00", "is_active": "on", "include_in_totals": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "Main Checking")
        self.assertEqual(self.account.opening_balance, Decimal("1500.00"))

    def test_delete_requires_post(self):
        resp = self.client.get(reverse("delete_account", args=[self.account.pk]))
        self.assertEqual(resp.status_code, 200)  # confirmation page
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())

    def test_delete_removes_the_account(self):
        resp = self.client.post(reverse("delete_account", args=[self.account.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())

    def test_cannot_touch_another_users_account(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("update_account", args=[self.account.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(reverse("delete_account", args=[self.account.pk])).status_code, 404
        )
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("update_account", args=[self.account.pk])).status_code, 302
        )


class TransactionCrudTests(CrudTestBase):
    def test_update_corrects_a_mistyped_amount(self):
        resp = self.client.post(reverse("update_transaction", args=[self.transaction.pk]), {
            "account": self.account.pk, "category": self.category.pk,
            "amount": "24.00", "date": "2026-01-15", "description": "Walmart",
            "transaction_type": "expense",
        })
        self.assertEqual(resp.status_code, 302)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.amount, Decimal("24.00"))

    def test_update_moves_the_account_balance(self):
        self.assertEqual(self.account.computed_balance, Decimal("950.00"))
        self.client.post(reverse("update_transaction", args=[self.transaction.pk]), {
            "account": self.account.pk, "category": self.category.pk,
            "amount": "24.00", "date": "2026-01-15", "description": "Walmart",
            "transaction_type": "expense",
        })
        self.assertEqual(self.account.computed_balance, Decimal("976.00"))

    def test_delete_restores_the_balance(self):
        resp = self.client.post(reverse("delete_transaction", args=[self.transaction.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=self.transaction.pk).exists())
        self.assertEqual(self.account.computed_balance, Decimal("1000.00"))

    def test_cannot_touch_another_users_transaction(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.post(reverse("delete_transaction", args=[self.transaction.pk])).status_code, 404
        )


class CategoryCrudTests(CrudTestBase):
    def test_update_renames_the_category(self):
        resp = self.client.post(reverse("update_category", args=[self.category.pk]), {
            "name": "Food", "category_type": "expense", "is_active": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Food")

    def test_delete_removes_the_category(self):
        resp = self.client.post(reverse("delete_category", args=[self.category.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())

    def test_system_categories_are_not_editable_or_deletable(self):
        system = Category.objects.create(
            user=self.user, name="System Rent", category_type="expense", is_system=True
        )
        self.assertEqual(
            self.client.get(reverse("update_category", args=[system.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(reverse("delete_category", args=[system.pk])).status_code, 404
        )
        self.assertTrue(Category.objects.filter(pk=system.pk).exists())


class BudgetCrudTests(CrudTestBase):
    def test_update_changes_the_amount(self):
        resp = self.client.post(reverse("update_budget", args=[self.budget.pk]), {
            "category": self.category.pk, "month": "2026-01-01", "amount": "550.00",
            "is_active": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.amount, Decimal("550.00"))

    def test_delete_removes_the_budget(self):
        resp = self.client.post(reverse("delete_budget", args=[self.budget.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Budget.objects.filter(pk=self.budget.pk).exists())

    def test_cannot_touch_another_users_budget(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("update_budget", args=[self.budget.pk])).status_code, 404
        )


class ListPagesExposeEditAndDeleteTests(CrudTestBase):
    def test_account_list_links_to_edit_and_delete(self):
        resp = self.client.get(reverse("list_accounts"))
        self.assertContains(resp, reverse("update_account", args=[self.account.pk]))
        self.assertContains(resp, reverse("delete_account", args=[self.account.pk]))

    def test_transaction_list_links_to_edit_and_delete(self):
        resp = self.client.get(reverse("list_transactions"))
        self.assertContains(resp, reverse("update_transaction", args=[self.transaction.pk]))
        self.assertContains(resp, reverse("delete_transaction", args=[self.transaction.pk]))

    def test_category_list_links_to_edit_and_delete(self):
        resp = self.client.get(reverse("list_categories"))
        self.assertContains(resp, reverse("update_category", args=[self.category.pk]))
        self.assertContains(resp, reverse("delete_category", args=[self.category.pk]))

    def test_budget_list_links_to_edit_and_delete(self):
        resp = self.client.get(reverse("list_budgets"))
        self.assertContains(resp, reverse("update_budget", args=[self.budget.pk]))
        self.assertContains(resp, reverse("delete_budget", args=[self.budget.pk]))
