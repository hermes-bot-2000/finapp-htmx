# finapp-htmx

Niche SaaS personal finance — Django + HTMX + template partials, zero 3rd-party Django packages.

## Tech Stack

- Django 6 + HTMX (no Django REST Framework, no React)
- SQLite for dev, PostgreSQL for production
- Template partials for all page transitions (no client-side JS framework)
- Blue / white CSS theme (see `static/css/style.css`)

## Quick Start

### Prerequisites

- Python 3.13+
- A virtual environment (recommended)

### Setup

```bash
# Clone the repo
git clone https://github.com/hermes-bot-2000/finapp-htmx.git
cd finapp-htmx

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --settings=config.settings

# Load sample data (optional, for development)
python manage.py load_test_data --settings=config.settings

# Create a superuser (optional, for admin access)
python manage.py createsuperuser --settings=config.settings
```

### Running the Dev Server

```bash
python manage.py runserver --settings=config.settings
```

Open http://localhost:8000 in your browser. The site runs with `DEBUG=True` — do not use this configuration in production.

### Dev User Credentials

After running `load_test_data`, log in with:

- **User:** testuser
- **Password:** testpass123

## Deployment (Dev → Production)

Settings are environment-driven — no code edit is needed to go to production,
and the app refuses to boot misconfigured. With `DJANGO_DEBUG=False`,
`DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` are **mandatory**
(`ImproperlyConfigured` otherwise), and HSTS, `SECURE_SSL_REDIRECT`, secure
session/CSRF cookies and `X_FRAME_OPTIONS=DENY` all switch on automatically.

| Variable | Required in prod | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | yes (`False`) | Turns on every hardening switch below |
| `DJANGO_SECRET_KEY` | yes | 50+ random chars; boot fails without it |
| `DJANGO_ALLOWED_HOSTS` | yes | Comma-separated hostnames |
| `DATABASE_URL` | no | `postgres://user:pw@host:5432/dbname`; SQLite if unset |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | no | Comma-separated `https://` origins |
| `GOCARDLESS_WEBHOOK_SECRET` | for webhooks | HMAC-SHA256 secret; the endpoint returns 503 while unset |

```bash
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
export DJANGO_ALLOWED_HOSTS=finapp.example.com
export DATABASE_URL=postgres://finapp:secret@localhost:5432/finapp
python manage.py migrate
python manage.py collectstatic --noinput
```

Static files are served by WhiteNoise (hashed + compressed via
`CompressedManifestStaticFilesStorage`), so no separate Nginx static config is
required. Verify the deployment posture with:

```bash
python manage.py check --deploy --fail-level WARNING
```

A minimal Gunicorn command for development-ish deployments:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## Project Structure

```
finapp-htmx/
  apps/
    accounts/       # Account models (checking, savings, credit_card)
    budgets/        # Monthly budget tracking
    categories/     # Income / expense categories
    transactions/   # CRUD for transactions
    users/          # Registration, login, logout
    integrations/   # Third-party bank sync (placeholder)
  config/           # Django project settings, URLs, WSGI
  static/css/       # Blue/white theme stylesheet
  templates/        # Base template + per-app templates
  manage.py
  db.sqlite3        # SQLite database (dev only)
  static_root/      # Collected static files for production
```

## License

MIT
