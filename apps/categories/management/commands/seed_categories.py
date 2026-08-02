"""Seed the shared default categories for a residential family of two.

The seed is owned by a single inactive "system" user and flagged
``is_system=True`` so the categories are offered to every user. Each user
can still create their own private (non-system) categories.

The command is idempotent: re-running it will not create duplicates.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.categories.models import Category
from apps.categories.data.default_categories import DEFAULT_CATEGORIES

SYSTEM_USERNAME = "_finapp_system"
SYSTEM_EMAIL = "system@finapp.local"


class Command(BaseCommand):
    help = "Seed the default shared categories (idempotent)."

    def handle(self, *args, **options):
        system_user, created = User.objects.get_or_create(
            username=SYSTEM_USERNAME,
            defaults={
                "email": SYSTEM_EMAIL,
                "is_active": False,
                "is_staff": False,
            },
        )
        if created:
            system_user.set_unusable_password()
            system_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created system owner '{SYSTEM_USERNAME}'"))

        created_count = 0
        with transaction.atomic():
            for group in DEFAULT_CATEGORIES:
                parent = self._ensure_category(system_user, group)
                if parent is not None:
                    created_count += 1
                for child in group.get("children", []):
                    child = dict(child)
                    child["parent"] = parent
                    if self._ensure_category(system_user, child) is not None:
                        created_count += 1

        total = Category.objects.filter(user=system_user, is_system=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_count} new category(ies) created, "
                f"{total} system categories now present."
            )
        )

    def _ensure_category(self, owner, spec):
        """Create a category if it does not already exist; return it or None if skipped."""
        name = spec["name"]
        if Category.objects.filter(user=owner, name=name, is_system=True).exists():
            return None
        return Category.objects.create(
            user=owner,
            name=name,
            category_type=spec["type"],
            description=spec.get("description", ""),
            parent=spec.get("parent"),
            icon=spec.get("icon", ""),
            color=spec.get("color", ""),
            is_system=True,
            is_active=True,
        )
