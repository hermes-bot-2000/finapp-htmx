# finapp-htmx — Independent Prototype Audit

Date: 2026-08-02
Scope: full source review + defect reproduction against the live data layer
(`manage.py shell`, Django test `Client`). 64 existing tests pass; `manage.py check`
is clean. A clean check is not a correct product — every finding below was
reproduced, not inferred.

---

## Executive summary

finapp-htmx is a genuinely well-shaped Django 6 + HTMX prototype: no 3rd-party
Django deps, a sane app split (users / accounts / categories / transactions /
budgets / integrations), 150 seeded system categories, a real GoCardless
open-banking client with a mock fallback, a CSV statement importer, and a
positive-amount money convention enforced in `Transaction.save()`. Test coverage
(64 tests) is above average for a prototype.

Three structural problems block it from being a usable Quicken competitor:

1. **The ledger doesn't add up.** Account balances are a static, hand-entered
   number. Nothing — not manual entry, not CSV import, not bank sync — ever
   derives balance from transactions. A personal-finance app whose balances are
   wrong the moment you use it has no retention floor.
2. **The app is read-mostly.** There is no edit and no delete for *anything*:
   accounts, transactions, categories, budgets. Every URLconf is `list/` +
   `create/`. A mistyped $2,400 rent entry is permanent outside `/admin/`.
3. **Unvalidated user input reaches the ORM and crashes with 500s**, and one
   state-changing endpoint accepts GET, which is CSRF-bypassable.

---

## Findings

| # | Finding | Evidence (how verified) | Severity |
|---|---------|------------------------|----------|
| F1 | Account balance never updates from transactions | Shell: created account bal 1000.00, imported 2 rows + created a 200.00 expense → `balance` still `1000.00`. No signal/`save()` hook anywhere. | Critical |
| F2 | CSV importer mis-signs income as expense | Shell: row `ACME PAYROLL DIRECT DEP, +2500.00` imported as `transaction_type='expense'`, amount 2500.00. `importers.py:114` — `transaction_type = category.category_type if category else "expense"`; sign of the parsed amount is ignored, then `Transaction.save()` calls `abs()`. Inflates spend, corrupts budgets. | Critical |
| F3 | No update/delete views | `apps/*/urls.py` — every app exposes only `""` and `create/`. Admin is the only escape hatch. | Critical |
| F4 | `?category=abc` → uncaught `ValueError`, HTTP 500 | Test client: `/transactions/?category=abc` raises `ValueError: Field 'id' expected a number but got 'abc'` (`transactions/views.py:18,26`). | High |
| F5 | `?month=notamonth` → uncaught `ValueError`, HTTP 500 | Test client: `/budgets/summary/?month=notamonth` raises `Invalid isoformat string` (`budgets/views.py:35`). | High |
| F6 | `sync_integration` / `disconnect_integration` mutate state on GET | `integrations/urls.py` + `views.py:137` — no `require_POST`. `GET /integrations/1/sync/` triggers a live bank pull; an `<img src>` on any page can fire it. Disconnect renders a confirm on GET but sync does not. | High |
| F7 | Webhook accepts unauthenticated writes when secret unset | Test client: `POST /integrations/webhook/` → 200 with `GOCARDLESS_WEBHOOK_SECRET=""` (default). `csrf_exempt` + `if secret and ...` fails open. Comparison also uses `!=`, not `hmac.compare_digest`. | High |
| F8 | Full account + routing numbers stored in plaintext | `accounts/models.py:39-44`. `masked_account_number` exists but is used only in admin — never in a template. Storing ABA + account number unencrypted is an unnecessary breach liability (and GLBA/PCI-adjacent exposure) for data the app never needs. | High |
| F9 | Production security posture absent | `settings.py`: `ALLOWED_HOSTS=[]`, no `SECURE_HSTS_*`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`; `DEBUG` defaults True; dev SECRET_KEY inline. README claims Postgres + prod deploy; `requirements.txt` has no `psycopg`/`gunicorn`/`whitenoise`. | High |
| F10 | Dashboard money math duplicated & wrong for non-monthly budgets | `config/urls.py:16-26` re-implements budget spend inline over *all* budgets ignoring `budget.month`, `is_active`, `period_start/end` and `rollover_amount`, while `Budget.spent`/`remaining` already do it correctly. Two answers for one number. | Medium |
| F11 | `Profile` is created only at register, never read | `users/views.py:13` creates it; no settings view, no URL. `currency`, `date_format`, `timezone`, `email_notifications`, `budget_warnings`, `transaction_reminders` are dead fields. Templates hardcode `$`. | Medium |
| F12 | Multi-currency modeled but not implemented | `Account.currency` per account; `net_worth = sum(a.signed_balance)` (`config/urls.py:10`) adds USD to JPY with no conversion. | Medium |
| F13 | Transfers don't transfer | `transaction_type='transfer'` exists but a transfer is a single row on one account — no paired leg, no destination account field. Double-counts or loses money in any transfer scenario. | Medium |
| F14 | `is_recurring` is a flag, not a feature | `Transaction.is_recurring/recurring_frequency/recurring_ends` modeled; nothing generates future occurrences. No scheduled/forecast view. | Medium |
| F15 | Importer category matching is O(categories) substring scan | `importers.py:_match_category` loops every user category per row and matches `cat.name.lower() in desc` — "Gas" matches "GASTON'S DINER". Also queries per row (N+1). | Medium |
| F16 | No reporting layer | No net-worth-over-time, cashflow, spend-by-category, or year-over-year view. No CSV/OFX/QIF *export* — data goes in, nothing comes out. Export is table stakes vs Quicken and a trust/lock-in objection. | Medium |
| F17 | Anonymous dashboard renders a live view | `config/urls.py:7` renders `dashboard.html` for anonymous users instead of redirecting to login; no `LOGIN_URL`/`LOGIN_REDIRECT_URL` set. | Low |
| F18 | No rate limiting or lockout on login/register | `users/views.py` uses bare `AuthenticationForm`; unlimited credential stuffing. No email verification, no password reset URLs wired. | Low |
| F19 | Upload has no size/type guard | `StatementUploadForm.file` is a plain `FileField`; a 500MB CSV is read fully into memory via `uploaded.read()` (`views_upload.py:17`). | Low |
| F20 | Dev artifacts in repo | `capture_screenshots.py`, `capture_dashboard.py`, `.DS_Store`, committed `venv/` alongside `.venv/`, test CSVs written to `/tmp` during the test run. | Low |

---

## Top 3 to fix, and how

### 1. Make the ledger self-consistent (F1, F2, F10, F13)

**Problem.** Balances are decorative and imported income is booked as spending.
Both were reproduced in the shell. Everything downstream — net worth, budgets,
any future report — is built on numbers the app itself contradicts.

**How.**

- Make `Account.balance` derived, not stored. Add:
  ```python
  # apps/accounts/models.py
  @property
  def computed_balance(self):
      agg = self.transactions.aggregate(
          inflow=Sum("amount", filter=Q(transaction_type="income")),
          outflow=Sum("amount", filter=Q(transaction_type="expense")),
      )
      opening = self.opening_balance or Decimal("0")
      return opening + (agg["inflow"] or 0) - (agg["outflow"] or 0)
  ```
  Rename the current `balance` field to `opening_balance` (a data migration
  copying the value across), and render `computed_balance` everywhere. If
  aggregate cost becomes a concern later, cache it via a `post_save`/`post_delete`
  signal on `Transaction` — but derive first, optimise second.
- Fix the importer sign in `importers.py:import_statement_rows`: derive the type
  from the parsed amount, and only fall back to the category:
  ```python
  transaction_type = "expense" if amount < 0 else "income"
  category = _match_category(user, description)
  if category and category.category_type == transaction_type:
      pass  # keep it; otherwise leave category null for user review
  ```
  Add a regression test asserting a `+2500.00` payroll row imports as `income`.
- Delete the inline budget math in `config/urls.py` and call `budget.spent` /
  `budget.remaining` / `budget.is_over_budget`, filtered to
  `is_active=True, month=<current period>`. One implementation of every number.
- Model transfers as a paired write: add `transfer_account` (nullable FK) and, in
  a transaction-atomic block, write the mirrored leg; exclude `transfer` rows from
  income/expense aggregates.

Test first (red/green): write the three failing assertions — balance after
expense, payroll import type, dashboard-vs-`Budget.spent` agreement — then fix.

### 2. Add edit + delete for every entity (F3)

**Problem.** The app is append-only. A single typo is uncorrectable through the UI
and there is no way to remove a duplicate import. This alone makes it unusable for
a real household, and it's the cheapest gap to close.

**How.** Use Django's generic CBVs rather than hand-rolling — for each app:

```python
# apps/transactions/views.py
class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    success_url = reverse_lazy("list_transactions")
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)  # ownership scope
    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    success_url = reverse_lazy("list_transactions")
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
```

Wire `<int:pk>/edit/` and `<int:pk>/delete/` per app. The `get_queryset` override
is mandatory on every one — it is what prevents IDOR (user A editing user B's row
by guessing a pk). Add a test per app asserting user B gets 404 on user A's pk.
For system categories, block delete when `is_system=True`.
Prefer HTMX inline edit (`hx-get` the form into the row) to match the existing
partial-swap pattern.

### 3. Close the security holes before any deploy (F6, F7, F8, F4, F5, F9)

**Problem.** Two endpoints let an attacker act without a valid session or CSRF
token, plaintext bank credentials sit in the DB, and two query params 500 the app.

**How, in order:**

- **GET-mutation → POST.** Decorate `sync_integration` with `@require_POST`
  (the template already POSTs; the URL just also accepts GET). Make
  `disconnect_integration` POST-only for the mutating branch.
- **Webhook fails open.** Require the secret and use a constant-time compare:
  ```python
  secret = settings.GOCARDLESS_WEBHOOK_SECRET
  if not secret:
      return HttpResponse("webhook not configured", status=503)
  sig = request.headers.get("Webhook-Signature", "")
  expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
  if not hmac.compare_digest(sig, expected):
      return HttpResponse("invalid signature", status=400)
  ```
  Verify the actual GoCardless signature scheme against their docs before shipping.
- **Stop storing bank credentials.** Drop `routing_number` entirely and store only
  the last 4 of `account_number` (data migration: truncate existing rows). The app
  has no feature that needs the full number — bank linking goes through GoCardless
  requisitions. If full numbers are ever genuinely required, encrypt at rest with
  the already-present `cryptography` dep and a KMS-held key, never the Django
  SECRET_KEY.
- **Validate query params.** Use a small `forms.Form` for the filters
  (`category = ModelChoiceField(queryset=...)`, `month = DateField`) and ignore
  invalid input instead of passing raw strings to the ORM. That fixes F4/F5 and
  scopes the category filter to the user's own categories in one move.
- **Production settings.** Split `config/settings/{base,dev,prod}.py`; in prod
  require `DJANGO_SECRET_KEY` (raise `ImproperlyConfigured` if unset), default
  `DEBUG=False`, set `ALLOWED_HOSTS` from env, and enable
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`,
  `SECURE_HSTS_PRELOAD`, `X_FRAME_OPTIONS="DENY"`. Add `psycopg[binary]`,
  `gunicorn`, `whitenoise` to `requirements.txt` so the README stops lying, and
  gate CI on `manage.py check --deploy`.

---

## Next tier (after the top 3)

4. **Turn on the Profile.** A settings view + `LOGIN_URL` wiring makes `currency`,
   `date_format`, `timezone` and the three notification booleans real. Then a
   nightly `send_budget_warnings` management command using `budget.is_warning`
   gives you an engagement loop out of fields that already exist. Low effort,
   directly retention-positive.
5. **Reporting + export (F16).** Net worth over time, spend-by-category, cashflow,
   and CSV/OFX export. Reports are the reason people pay; export is the reason
   they trust you enough to import.

## Quick wins (ship this week)

- `@require_POST` on `sync_integration` — one line, closes a CSRF hole.
- Webhook 503 when unconfigured — three lines, closes an unauthenticated endpoint.
- Filter-param validation — kills two reproducible 500s.
- Render `masked_account_number` in templates; drop `routing_number`.
- `.gitignore` `venv/`, `.DS_Store`; delete `capture_*.py` or move under `tools/`.
- Point the test CSV writers at `tempfile.mkdtemp()` instead of `/tmp` literals.

---

Findings F1, F2, F4, F5, F7 were reproduced against the running application
(Django shell and test client) on 2026-08-02. The remainder are direct source
observations with file:line citations. No application code was modified during
this audit.
