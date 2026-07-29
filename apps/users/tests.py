from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class UserAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "testpass123")

    def test_register_page_loads(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_register(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "password1": "newpass123",
            "password2": "newpass123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_user_can_login(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 302)

    def test_user_can_logout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
