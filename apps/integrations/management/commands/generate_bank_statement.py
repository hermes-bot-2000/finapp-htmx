"""Generate a sample bank statement CSV for testing the upload feature."""
import csv
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand


MERCHANTS = [
    ("GROCERIES - WHOLE FOODS MARKET", -52.30),
    ("GROCERIES - TRADER JOES", -41.18),
    ("DINING - PIZZA NIGHT", -23.50),
    ("DINING - COFFEE SHOP", -4.75),
    ("UTILITIES - ELECTRIC BILL", -89.20),
    ("UTILITIES - INTERNET BILL", -59.99),
    ("TRANSPORT - SHELL GAS STATION", -38.40),
    ("TRANSPORT - LYFT RIDE", -14.25),
    ("ENTERTAINMENT - NETFLIX", -15.49),
    ("ENTERTAINMENT - SPOTIFY", -9.99),
    ("HEALTH - PHARMACY", -27.10),
    ("RETAIL - AMAZON", -63.87),
    ("PAYROLL DIRECT DEPOSIT", 2500.00),
    ("FREELANCE - CLIENT INVOICE", 850.00),
    ("INTEREST PAYMENT", 1.25),
]


class Command(BaseCommand):
    help = "Generate a sample bank statement CSV (default: a few months, realistic mix)."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="sample_statement.csv", help="Output CSV path")
        parser.add_argument("--rows", type=int, default=60, help="Number of transactions")
        parser.add_argument("--starting-balance", default="1200.00", help="Opening balance")
        parser.add_argument("--seed", type=int, default=42, help="Random seed")
        parser.add_argument("--format", default="iso", choices=["iso", "us"], help="Date format")

    def handle(self, *args, **options):
        random.seed(options["seed"])
        rows = options["rows"]
        balance = float(options["starting_balance"])
        fmt = options["format"]

        today = date.today()
        # Spread transactions across the past ~rows/2 days ending today.
        span_days = max(rows // 2, 1)
        start = today - timedelta(days=span_days)

        # Pre-generate dates (some days get multiple transactions).
        dates = []
        for i in range(rows):
            day_offset = random.randint(0, span_days)
            dates.append(start + timedelta(days=day_offset))
        dates.sort()

        with open(options["out"], "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Description", "Amount", "Balance"])
            for d in dates:
                merchant, amount = random.choice(MERCHANTS)
                balance += amount
                date_str = d.strftime("%Y-%m-%d") if fmt == "iso" else d.strftime("%m/%d/%Y")
                writer.writerow([
                    date_str,
                    merchant,
                    "{:.2f}".format(amount),
                    "{:.2f}".format(balance),
                ])

        self.stdout.write(self.style.SUCCESS(
            "Wrote {} transactions to {}".format(rows, options["out"])
        ))
