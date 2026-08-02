.PHONY: migrate seed build test

PYTHON = uv run python

migrate:
	$(PYTHON) manage.py migrate --noinput

seed:
	$(PYTHON) manage.py seed_categories

# Build the app: migrate + seed defaults so categories exist on first run.
build: migrate seed

test:
	$(PYTHON) manage.py test
