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

For a production deployment, you will need to:

1. Set `DEBUG = False` in `config/settings.py`
2. Add your domain to `ALLOWED_HOSTS`
3. Switch the `DATABASES` setting to PostgreSQL
4. Set a proper `SECRET_KEY` via environment variable
5. Run `collectstatic` to gather static files into `STATIC_ROOT`
6. Serve static files via Nginx or a CDN
7. Run behind Gunicorn or uWSGI

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
