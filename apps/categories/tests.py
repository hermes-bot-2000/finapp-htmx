from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Category

class CategoryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "testpass123")
        self.category = Category.objects.create(
            user=self.user, name="Groceries", category_type="expense"
        )

    def test_category_list_requires_login(self):
        response = self.client.get(reverse("list_categories"))
        self.assertEqual(response.status_code, 302)

    def test_category_list_for_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("list_categories"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Groceries")

    def test_create_category(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("create_category"), {
            "name": "Salary",
            "category_type": "income",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name="Salary").exists())
