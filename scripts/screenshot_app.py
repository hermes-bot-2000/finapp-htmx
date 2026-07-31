import os, django
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
    Category.objects.create(user=u, name='Transport')
    a = Account.objects.create(user=u, name='Main Checking', account_type='checking', balance=Decimal('1500.00'))
    Transaction.objects.create(user=u, account=a, category=food, amount=Decimal('45.00'), date='2026-07-29', description='Groceries')
    Budget.objects.create(user=u, category=food, amount=Decimal('300.00'), month=date(2026, 7, 1))
print('Seeded demo user')
