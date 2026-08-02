#!/usr/bin/env bash
# Build/setup script for finapp-htmx.
# Applies migrations and seeds the shared default categories so they are
# present when the app is built/started.
set -euo pipefail

cd "$(dirname "$0")/.."

echo ">> Applying migrations"
uv run python manage.py migrate --noinput

echo ">> Seeding default categories"
uv run python manage.py seed_categories

echo ">> Build complete"
