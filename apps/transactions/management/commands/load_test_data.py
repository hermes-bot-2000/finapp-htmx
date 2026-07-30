#!/usr/bin/env python
"""Management command to generate test data for Finapp."""

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.accounts.models import Account
from apps.categories.models import Category
from apps.transactions.models import Transaction
from apps.budgets.models import Budget


class Command(BaseCommand):
    help = "Generate sample transactions, accounts, categories, and budgets for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            default="testuser",
            help="Username to create/use (default: testuser)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days of transactions to generate (default: 90)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42)",
        )

    def handle(self, *args, **options):
        random.seed(options["seed"])
        username = options["user"]
        days = options["days"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_active": True},
        )
        if created:
            user.set_password("testpass123")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created user '{}'".format(username)))
        else:
            self.stdout.write("Using existing user '{}'".format(username))

        accounts_data = [
            ("Checking", "checking", 3450.75),
            ("Savings", "savings", 12890.00),
            ("Visa Credit", "credit_card", -2340.50),
        ]
        accounts = []
        for name, atype, balance in accounts_data:
            acct, _ = Account.objects.update_or_create(
                user=user,
                name=name,
                defaults={"account_type": atype, "balance": balance},
            )
            accounts.append(acct)
        self.stdout.write(self.style.SUCCESS("Created {} accounts".format(len(accounts))))

        categories_data = [
            ("Salary", "income"),
            ("Freelance", "income"),
            ("Groceries", "expense"),
            ("Rent", "expense"),
            ("Utilities", "expense"),
            ("Dining Out", "expense"),
            ("Gas", "expense"),
            ("Entertainment", "expense"),
            ("Health", "expense"),
            ("Transportation", "expense"),
        ]
        categories = []
        for name, ctype in categories_data:
            cat, _ = Category.objects.update_or_create(
                user=user,
                name=name,
                defaults={"category_type": ctype},
            )
            categories.append(cat)
        self.stdout.write(self.style.SUCCESS("Created {} categories".format(len(categories))))

        Transaction.objects.filter(user=user).delete()

        income_cats = [c for c in categories if c.category_type == "income"]
        expense_cats = [c for c in categories if c.category_type == "expense"]

        tx_count = 0
        start = date.today() - timedelta(days=days)
        for i in range(days):
            day = start + timedelta(days=i)
            num_tx = random.randint(1, 3)
            for _ in range(num_tx):
                if random.random() < 0.25:
                    cat = random.choice(income_cats)
                    amount = round(random.uniform(200, 5000), 2)
                    account = accounts[0]
                else:
                    cat = random.choice(expense_cats)
                    amount = -round(random.uniform(3, 300), 2)
                    account = random.choice(accounts)
                descriptions = self._descriptions(cat.name)
                desc = random.choice(descriptions)
                Transaction.objects.create(
                    user=user,
                    account=account,
                    category=cat,
                    amount=amount,
                    date=day,
                    description=desc,
                )
                tx_count += 1

        self.stdout.write(self.style.SUCCESS("Created {} transactions".format(tx_count)))

        today = date.today()
        month_start = date(today.year, today.month, 1)

        budget_data = [
            (expense_cats[0], 600),
            (expense_cats[2], 200),
            (expense_cats[3], 1500),
            (expense_cats[4], 100),
            (expense_cats[5], 150),
        ]
        for cat, amount in budget_data:
            Budget.objects.update_or_create(
                user=user,
                category=cat,
                month=month_start,
                defaults={"amount": amount},
            )
        self.stdout.write(self.style.SUCCESS("Created {} budgets for {}".format(len(budget_data), month_start.strftime("%Y-%m"))))

        self.stdout.write(self.style.SUCCESS("Done!"))

    def _descriptions(self, category_name):
        mapping = {
            "Salary": ["Monthly salary deposit", "Paycheck - direct deposit", "Quarterly bonus"],
            "Freelance": ["Freelance project payment", "Client invoice payment", "Side gig payout"],
            "Groceries": ["Whole Foods", "Trader Joes", "Grocery run", "Instacart order"],
            "Rent": ["Monthly rent payment", "Rent - apartment"],
            "Utilities": ["Electric bill", "Internet bill", "Water bill", "Phone bill"],
            "Dining Out": ["Dinner at restaurant", "Coffee shop", "Lunch delivery", "Pizza night"],
            "Gas": ["Shell gas station", "Chevron fill-up", "Bus fare"],
            "Entertainment": ["Netflix subscription", "Movie tickets", "Concert", "Streaming service"],
            "Health": ["Pharmacy", "Doctor copay", "Gym membership", "Vitamin shop"],
            "Transportation": ["Lyft ride", "Parking meter", "Toll road", "Car wash"],
        }
        return mapping.get(category_name, ["{} purchase".format(category_name)])
