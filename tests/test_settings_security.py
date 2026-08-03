"""F9: production security posture.

These assert the *shape* of the settings module rather than the values a dev
box happens to have: with ``DJANGO_DEBUG=False`` the app must come up hardened,
and Django's own deployment checklist must pass clean.
"""
import os
from importlib import reload
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

# Django's security.W009 check rejects keys under 50 chars, with few unique
# characters, or prefixed "django-insecure-". Use something realistic.
REALISTIC_SECRET_KEY = "8Kq2!vZr9wLp4TgXb7NmYc3Ejd6HsAu1QfWi0ZoRtVyBnMxSlP"


def load_settings(**env):
    """Import config.settings fresh under a patched environment.

    Returns a *snapshot* of the module's uppercase settings: the module object
    itself is reloaded back to the ambient environment before returning, so
    holding a reference to it would show the restored values, not the ones
    produced under ``env``.
    """
    import config.settings as settings_module

    original = {k: os.environ.get(k) for k in env}
    os.environ.update({k: v for k, v in env.items()})
    try:
        reload(settings_module)
        return SimpleNamespace(**{
            name: getattr(settings_module, name)
            for name in dir(settings_module)
            if name.isupper()
        })
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reload(settings_module)


class ProductionSettingsTests(SimpleTestCase):
    """With DEBUG off, every hardening switch must be on."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.prod = load_settings(
            DJANGO_DEBUG="False",
            DJANGO_SECRET_KEY=REALISTIC_SECRET_KEY,
            DJANGO_ALLOWED_HOSTS="finapp.example.com,www.finapp.example.com",
        )

    def test_debug_is_off(self):
        self.assertFalse(self.prod.DEBUG)

    def test_allowed_hosts_comes_from_the_environment(self):
        self.assertEqual(
            self.prod.ALLOWED_HOSTS,
            ["finapp.example.com", "www.finapp.example.com"],
        )

    def test_cookies_are_secure_and_http_only(self):
        self.assertTrue(self.prod.SESSION_COOKIE_SECURE)
        self.assertTrue(self.prod.CSRF_COOKIE_SECURE)
        self.assertTrue(self.prod.SESSION_COOKIE_HTTPONLY)

    def test_ssl_redirect_and_hsts(self):
        self.assertTrue(self.prod.SECURE_SSL_REDIRECT)
        self.assertGreaterEqual(self.prod.SECURE_HSTS_SECONDS, 31536000)
        self.assertTrue(self.prod.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertTrue(self.prod.SECURE_HSTS_PRELOAD)

    def test_content_and_referrer_hardening(self):
        self.assertTrue(self.prod.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(self.prod.X_FRAME_OPTIONS, "DENY")
        self.assertEqual(self.prod.SECURE_REFERRER_POLICY, "same-origin")

    def test_proxy_ssl_header_is_set_for_reverse_proxies(self):
        self.assertEqual(
            self.prod.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https")
        )

    def test_deployment_checklist_passes(self):
        from django.core.management import call_command
        from io import StringIO

        with override_settings(
            DEBUG=False,
            SECRET_KEY=self.prod.SECRET_KEY,
            ALLOWED_HOSTS=self.prod.ALLOWED_HOSTS,
            SESSION_COOKIE_SECURE=self.prod.SESSION_COOKIE_SECURE,
            CSRF_COOKIE_SECURE=self.prod.CSRF_COOKIE_SECURE,
            SECURE_SSL_REDIRECT=self.prod.SECURE_SSL_REDIRECT,
            SECURE_HSTS_SECONDS=self.prod.SECURE_HSTS_SECONDS,
            SECURE_HSTS_INCLUDE_SUBDOMAINS=self.prod.SECURE_HSTS_INCLUDE_SUBDOMAINS,
            SECURE_HSTS_PRELOAD=self.prod.SECURE_HSTS_PRELOAD,
            SECURE_CONTENT_TYPE_NOSNIFF=self.prod.SECURE_CONTENT_TYPE_NOSNIFF,
            X_FRAME_OPTIONS=self.prod.X_FRAME_OPTIONS,
        ):
            out = StringIO()
            call_command("check", "--deploy", "--fail-level", "WARNING", stdout=out, stderr=out)


class SecretKeyTests(SimpleTestCase):
    def test_insecure_dev_key_is_refused_when_debug_is_off(self):
        """A production boot must not silently run on the committed dev key."""
        with self.assertRaises(Exception):
            load_settings(DJANGO_DEBUG="False", DJANGO_SECRET_KEY="")

    def test_dev_boot_still_works_without_any_environment(self):
        dev = load_settings(DJANGO_DEBUG="True", DJANGO_SECRET_KEY="")
        self.assertTrue(dev.DEBUG)
        self.assertTrue(dev.SECRET_KEY)
        self.assertIn("localhost", dev.ALLOWED_HOSTS)
        # Hardening switches stay off locally so http://localhost works.
        self.assertFalse(dev.SECURE_SSL_REDIRECT)


class StaticAndDatabaseTests(SimpleTestCase):
    def test_whitenoise_is_installed_for_static_serving(self):
        from django.conf import settings

        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE
        )
        # Must sit directly after SecurityMiddleware.
        idx = settings.MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware")
        self.assertEqual(
            settings.MIDDLEWARE[idx - 1],
            "django.middleware.security.SecurityMiddleware",
        )

    def test_static_root_is_configured(self):
        from django.conf import settings

        self.assertTrue(settings.STATIC_ROOT)

    def test_database_url_switches_to_postgres(self):
        prod = load_settings(
            DJANGO_DEBUG="False",
            DJANGO_SECRET_KEY=REALISTIC_SECRET_KEY,
            DJANGO_ALLOWED_HOSTS="finapp.example.com",
            DATABASE_URL="postgres://user:pw@dbhost:5432/finapp",
        )
        self.assertEqual(
            prod.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql"
        )
        self.assertEqual(prod.DATABASES["default"]["NAME"], "finapp")
        self.assertEqual(prod.DATABASES["default"]["USER"], "user")
        self.assertEqual(prod.DATABASES["default"]["HOST"], "dbhost")
        self.assertEqual(prod.DATABASES["default"]["PORT"], "5432")

    def test_sqlite_remains_the_default(self):
        from django.conf import settings

        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3"
        )
