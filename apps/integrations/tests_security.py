"""F6/F7: state-changing endpoints must reject GET; the webhook must fail closed."""
import hashlib
import hmac
import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from apps.integrations.models import BankIntegration


def sign(secret, body):
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


class StateChangingGetTests(TestCase):
    """F6: GET must not trigger a live bank pull or a disconnect."""

    def setUp(self):
        self.user = User.objects.create_user("bank", "b@test.com", "pw")
        self.integration = BankIntegration.objects.create(
            user=self.user, provider="gocardless", requisition_id="req-1",
            institution_name="Mock Bank", sync_status="linked",
        )
        self.client.force_login(self.user)

    def test_sync_rejects_get(self):
        resp = self.client.get(reverse("sync_integration", args=[self.integration.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_sync_allows_post(self):
        resp = self.client.post(reverse("sync_integration", args=[self.integration.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_disconnect_get_renders_confirmation_without_mutating(self):
        resp = self.client.get(reverse("disconnect_integration", args=[self.integration.pk]))
        self.assertEqual(resp.status_code, 200)
        self.integration.refresh_from_db()
        self.assertTrue(self.integration.is_active)

    def test_disconnect_post_deactivates(self):
        resp = self.client.post(reverse("disconnect_integration", args=[self.integration.pk]))
        self.assertEqual(resp.status_code, 302)
        self.integration.refresh_from_db()
        self.assertFalse(self.integration.is_active)

    def test_sync_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("sync_integration", args=[self.integration.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/users/login/", resp["Location"])

    def test_sync_of_another_users_integration_404s(self):
        other = User.objects.create_user("other", "o@test.com", "pw")
        self.client.force_login(other)
        resp = self.client.post(reverse("sync_integration", args=[self.integration.pk]))
        self.assertEqual(resp.status_code, 404)


class WebhookSecurityTests(TestCase):
    """F7: no secret configured means the endpoint is closed, not open."""

    url_name = "integration_webhook"
    body = json.dumps({"event": "ping"})

    def post(self, signature=None):
        kwargs = {"data": self.body, "content_type": "application/json"}
        if signature is not None:
            kwargs["HTTP_WEBHOOK_SIGNATURE"] = signature
        return self.client.post(reverse(self.url_name), **kwargs)

    def test_fails_closed_when_secret_unset(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET=""):
            resp = self.post()
            self.assertEqual(resp.status_code, 503)

    def test_rejects_missing_signature(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET="topsecret"):
            self.assertEqual(self.post().status_code, 400)

    def test_rejects_wrong_signature(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET="topsecret"):
            self.assertEqual(self.post("deadbeef").status_code, 400)

    def test_accepts_valid_hmac_signature(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET="topsecret"):
            resp = self.post(sign("topsecret", self.body))
            self.assertEqual(resp.status_code, 200)

    def test_signature_is_body_bound(self):
        """A signature captured from one payload must not validate another."""
        with self.settings(GOCARDLESS_WEBHOOK_SECRET="topsecret"):
            stale = sign("topsecret", json.dumps({"event": "other"}))
            self.assertEqual(self.post(stale).status_code, 400)

    def test_rejects_get(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET="topsecret"):
            resp = self.client.get(reverse(self.url_name))
            self.assertEqual(resp.status_code, 405)
