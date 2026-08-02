from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import BankIntegration

class IntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "testpass123")
        self.integration = BankIntegration.objects.create(
            user=self.user, provider="TestBank", institution_name="Test Bank",
            requisition_id="req_test_1",
        )

    def test_integration_list_requires_login(self):
        response = self.client.get(reverse("list_integrations"))
        self.assertEqual(response.status_code, 302)

    def test_integration_list_for_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("list_integrations"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Bank")

    def test_base_integration_is_abstract(self):
        from apps.integrations.models import BaseIntegration
        self.assertTrue(BaseIntegration._meta.abstract)
