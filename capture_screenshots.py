import os
from playwright.sync_api import sync_playwright
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from decimal import Decimal
from apps.accounts.models import Account
from apps.categories.models import Category
from apps.transactions.models import Transaction
from apps.budgets.models import Budget

u, created = User.objects.get_or_create(username='demo', defaults={'email': 'demo@example.com'})
if created:
    u.set_password('demopass')
    u.save()
    food = Category.objects.create(user=u, name='Food')
    Category.objects.create(user=u, name='Rent')
    a = Account.objects.create(user=u, name='Main Checking', account_type='checking', balance=Decimal('1500.00'))
    Transaction.objects.create(user=u, account=a, category=food, amount=Decimal('45.00'), date='2026-07-29', description='Groceries')
    Transaction.objects.create(user=u, account=a, category=u.categories.get(name='Rent'), amount=Decimal('900.00'), date='2026-07-28', description='Apartment')
    Budget.objects.create(user=u, category=food, amount=Decimal('300.00'), month=date(2026, 7, 1))
print('Seeded demo user')

BASE = 'http://127.0.0.1:8000'
IMAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs', 'images')
os.makedirs(IMAGES, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    page = context.new_page()
    page.goto(BASE + '/users/login/')
    page.fill('input[name="username"]', 'demo')
    page.fill('input[name="password"]', 'demopass')
    page.click('button[type="submit"]')
    page.wait_for_timeout(300)

    pages = [
        ('/users/login/', '01-login.png'),
        ('/accounts/', '02-accounts.png'),
        ('/transactions/', '03-transactions.png'),
        ('/budgets/', '04-budgets.png'),
    ]
    for href, name in pages:
        page.goto(BASE + href)
        page.wait_for_timeout(200)
        path = os.path.join(IMAGES, name)
        page.screenshot(path=path, full_page=False)
        print(f'Screenshot saved: {name} -> {path}')
    browser.close()
