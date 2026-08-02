"""AppConfig for categories with auto-seeding on startup."""

import warnings
from django.apps import AppConfig


class CategoriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.categories"
    label = "categories"
    verbose_name = "Categories"

    def ready(self):
        # Auto-seed the shared default categories when the app is ready
        # (i.e. at server start / management command run). Idempotent.
        # DB access during app init normally raises an apps-not-ready
        # warning; we silence just that one and let the seed run.
        from apps.categories.management.commands.seed_categories import Command as SeedCommand

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                SeedCommand().handle()
            except Exception as exc:  # pragma: no cover - defensive
                import logging
                logging.getLogger(__name__).warning("Auto seed_categories failed: %s", exc)
