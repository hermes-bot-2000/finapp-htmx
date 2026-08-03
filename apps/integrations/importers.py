"""Bank statement CSV parsing and transaction import logic."""
import csv
import io
from decimal import InvalidOperation, Decimal
from datetime import datetime

from apps.transactions.models import Transaction
from apps.categories.models import Category

# Canonical header aliases merchants commonly use.
DATE_HEADERS = {"date", "transaction date", "posted date", "posting date"}
DESC_HEADERS = {"description", "details", "memo", "payee", "name", "narrative"}
AMOUNT_HEADERS = {"amount", "value"}
DEBIT_HEADERS = {"debit", "withdrawal", "withdrawals", "debited"}
CREDIT_HEADERS = {"credit", "deposit", "deposits", "credited"}
BALANCE_HEADERS = {"balance", "running balance"}

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y")


def _normalize_header(h):
    return h.strip().lower().lstrip("\ufeff")


def _parse_date(value):
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("Unrecognized date format: {}".format(value))


def parse_bank_statement(csv_text):
    """Parse a bank statement CSV into a list of normalized row dicts.

    Each row dict has keys: date (str, as parsed), description (str), amount (str).
    Supports both "Amount" (signed) and "Debit"/"Credit" column layouts, and
    tolerates blank rows.
    """
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return []

    header = [_normalize_header(c) for c in rows[0]]
    body = rows[1:]

    date_idx = next((i for i, h in enumerate(header) if h in DATE_HEADERS), None)
    desc_idx = next((i for i, h in enumerate(header) if h in DESC_HEADERS), None)
    amount_idx = next((i for i, h in enumerate(header) if h in AMOUNT_HEADERS), None)
    debit_idx = next((i for i, h in enumerate(header) if h in DEBIT_HEADERS), None)
    credit_idx = next((i for i, h in enumerate(header) if h in CREDIT_HEADERS), None)

    if date_idx is None or desc_idx is None:
        raise ValueError("Could not locate Date and Description columns in statement header.")

    out = []
    for row in body:
        if not any(cell.strip() for cell in row):
            continue
        description = row[desc_idx].strip() if desc_idx < len(row) else ""
        # Amount resolution: prefer a signed Amount column, else Debit-Credit.
        amount = None
        if amount_idx is not None and amount_idx < len(row) and row[amount_idx].strip():
            amount = row[amount_idx].strip()
        else:
            debit = (row[debit_idx].strip() if debit_idx is not None and debit_idx < len(row) else "")
            credit = (row[credit_idx].strip() if credit_idx is not None and credit_idx < len(row) else "")
            if debit:
                amount = "-{}".format(debit)
            elif credit:
                amount = credit
        if amount is None:
            continue
        out.append({
            "date": row[date_idx].strip() if date_idx < len(row) else "",
            "description": description,
            "amount": amount,
        })
    return out


def _match_category(user, description):
    """Return an existing user category whose name appears in the description."""
    desc = description.lower()
    for cat in Category.objects.filter(user=user):
        if cat.name.lower() in desc:
            return cat
    return None


def import_statement_rows(user, account, rows):
    """Import normalized statement rows as Transactions.

    Returns (imported_count, errors). Identical rows (same account, date,
    description, amount) are skipped to make re-uploads idempotent.
    """
    imported = 0
    errors = []
    for row in rows:
        description = (row.get("description") or "").strip()
        try:
            amount = Decimal(str(row.get("amount", "")).replace(",", "").strip())
        except (InvalidOperation, ValueError):
            errors.append("Could not parse amount for '{}'".format(description))
            continue
        try:
            date = _parse_date(row.get("date", ""))
        except ValueError as exc:
            errors.append("{} ({})".format(description, exc))
            continue

        if Transaction.objects.filter(
            user=user, account=account, date=date,
            description=description, amount=abs(amount),
        ).exists():
            continue

        # F2: the sign of the statement amount decides direction, not the
        # guessed category. A category is only attached when it agrees.
        transaction_type = "expense" if amount < 0 else "income"
        category = _match_category(user, description)
        if category and category.category_type != transaction_type:
            category = None
        Transaction.objects.create(
            user=user,
            account=account,
            category=category,
            amount=amount,
            date=date,
            description=description,
            transaction_type=transaction_type,
        )
        imported += 1
    return imported, errors
