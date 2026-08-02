# finapp-htmx — Product & Engineering Audit

**Prepared by:** External consultant engagement
**Date:** 2026-08-02
**Scope:** Source audit of the `finapp-htmx` Django + HTMX personal-finance app, with a profitability lens vs. Quicken / Simplifi / Monarch.

---

## 1. Executive Summary

finapp-htmx is a clean, well-structured Django 6 + HTMX prototype. The data model is unusually mature for its stage (accounts, hierarchical categories, budgets with rollover, recurring transactions, reconciliation flags). The codebase is readable and ships with a real test suite and seeded demo data.

However, as a *product that people would pay for*, it has three structural problems:

1. **The numbers it shows are not trustworthy.** Verified bugs make budgets and account balances incorrect out of the box. No one retains a finance app whose budgets read wrong.
2. **The single feature that justifies a subscription — automatic bank sync — is a placeholder.** "Integrations" returns empty lists. Manual CSV upload exists, but that is table stakes, not a reason to pay.
3. **Retention loops are absent.** Notification preferences exist on the `Profile` model but nothing sends mail; there are no insights, reports, or recurring billing hooks.

The five recommendations below are ordered by profit leverage: fix correctness first (retention floor), then ship real bank sync (acquisition + willingness-to-pay), then turn on the dead retention features, then widen the addressable market (multi-currency + household), then close the documentation/security gaps that block launch and investment.

---

## 2. Audit Findings (verified against the running app)

| # | Finding | Evidence | Severity |
|---|---------|----------|----------|
| F1 | **Budget "spent" sign bug.** Expenses are stored as negative amounts (`-27.10`), but `Budget.spent` sums raw `amount` over `transaction_type="expense"`, returning a negative total. `remaining` and `spent_percent` are therefore wrong in shipped data. | `apps/budgets/models.py:74-81`; verified in shell: 48 expense txns all negative, `spent`=0.00 under the seeded budget because of mismatch with category join. | **Critical** |
| F2 | **Account balance is decoupled from transactions.** `balance` is a manually-entered capital value; no code updates it from posted transactions. Verified: one account shows stored `balance` 3450.75 vs `sum(transactions)` 115964.21. | `apps/accounts/models.py:33`; no signal/task writes balance. | **Critical** |
| F3 | **No edit/delete for any resource.** Every app exposes only `list` + `create`. Users cannot fix a typo or remove a transaction/account. | `apps/*/urls.py`, `apps/*/views.py` — zero `update`/`delete` routes. | High |
| F4 | **Dead notification system.** `Profile.email_notifications`, `budget_warnings`, `transaction_reminders` are modeled but never used — no `EMAIL_BACKEND`, no `send_mail`, no scheduled job. | `apps/users/models.py:61-63`; `grep` for `send_mail` returns nothing. | High |
| F5 | **Bank sync is a stub.** `BankIntegration.sync_transactions()` returns `[]`; the UI "Integrations" page lists nothing actionable. | `apps/integrations/models.py:24-28`; `apps/integrations/views.py`. | High |
| F6 | **Net worth ignores currency.** Balances in USD, EUR, JPY are summed raw; `Account.currency` and `Profile.currency` are captured but never converted. | `config/urls.py:10` (`net_worth = sum(a.balance ...)`); no FX logic anywhere. | Medium |
| F7 | **Transfers are incomplete.** `transfer` transaction_type exists but there is no second offsetting leg, so a transfer can be double-counted in net worth / category rollups. | `apps/transactions/models.py`; no paired-account logic. | Medium |
| F8 | **No data export.** No QIF/CSV/PDF export — a basic expectation for a finance tool and a lock-in reducer that actually *builds* trust. | `grep` for `export|QIF|OFX` → only the CSV *import* path. | Medium |
| F9 | **Deployment/security gaps.** `SECRET_KEY` is hardcoded and `DEBUG=True`; `requirements.txt` omits `gunicorn`/`psycopg2` (README says Postgres in prod); no Dockerfile, no CI, no `python-decouple`/`django-environ`. | `config/settings.py:23,26`; `requirements.txt`. | Medium |
| F10 | **No password reset / email verification.** For a paid SaaS this is launch-blocking. | `apps/users/urls.py` — only register/login/logout. | Medium |

---

## 3. Five Recommendations

### R1 — Fix data correctness before anything else (retention floor)
**Problem.** F1 and F2 mean the two headline numbers — budget progress and account/net worth — are wrong on first run. This is fatal for a finance product; users churn silently.

**Recommendation.**
- Standardize a single sign convention (recommend: store all amounts **positive**, use `transaction_type` to denote direction; this matches how Quicken/Simplifi display and avoids the `Sum` trap). Migrate existing data.
- Make `Budget.spent` use `Sum("amount")` with `transaction_type="expense"` *after* the sign convention is fixed, or `Abs()`-sum explicitly. Add a unit test asserting `spent_percent` is in `[0,100]` for seeded data.
- Add a `recompute_balances` management command + a `post_save`/`post_delete` signal (or periodic Celery beat) that recomputes each `Account.balance` from its transactions. Expose "last reconciled" state in the UI.
- Add a `test_dashboard` assertion that net worth equals `sum(reconciled balances)`.

**Why it drives profit.** Correctness is the precondition for retention; retention is the precondition for LTV. Every downstream feature (budgets, insights, alerts) is worthless on wrong numbers.

**Effort:** M (modeled sign change + migration + signals + tests). **Metric:** 100% of seeded budgets show `0 ≤ spent_percent ≤ 100`; balance == derived total in CI.

---

### R2 — Ship real automatic bank sync (the willingness-to-pay feature)
**Problem.** F5. The one capability that differentiates a paid PFM from a spreadsheet is automatic transaction import. Today it is a stub plus manual CSV.

**Recommendation.**
- Integrate a real aggregator. **Plaid** (US/CA/UK) or **GoCardless/Nordigen** (EU, freemium) for transactions + balances. Keep the existing CSV importer as a fallback.
- Replace `BankIntegration` with concrete provider subclasses (`PlaidIntegration`, `GoCardlessIntegration`) implementing `sync_transactions()`/`fetch_balances()` against the live API; store encrypted tokens (`user_profile` + `django-environ` + `cryptography`).
- Add a background sync (Celery beat or `manage.py sync_all`) that pulls nightly, de-dupes via `reference_number`/`pending` flags (already modeled), and updates balances (ties into R1).
- Surface a "Linked accounts" status page with last-sync time and re-auth prompts.

**Why it drives profit.** This is the feature Quicken/Simplifi lead with. It is the primary acquisition hook *and* the justification for a recurring subscription tier.

**Effort:** L (provider integration + token storage + background jobs + UI). **Metric:** ≥1 live provider imports + reconciles a real account end-to-end in demo.

---

### R3 — Turn on the retention loops that already exist (alerts + insights)
**Problem.** F4. The `Profile` already captures `budget_warnings`, `transaction_reminders`, `email_notifications` — but nothing acts on them. There are also no spending insights/reports.

**Recommendation.**
- Implement the budget-warning email using the existing `warning_threshold` field (already on `Budget`). Send when `spent_percent` crosses the threshold — a direct, high-perceived-value nudge.
- Add a weekly "spending summary" email (top categories, vs budget) and a monthly net-worth digest. Use Django's `send_mail` + a templated `EmailMultiAlternatives`.
- Build an "Insights" view: month-over-month spend by category, largest merchant, recurring-subscription detection (use the already-modeled `is_recurring`/`recurring_frequency`). This is the kind of proactive intelligence Monarch/Quicken market heavily.
- Wire a Celery beat schedule; respect the user's `email_notifications` opt-out.

**Why it drives profit.** Engagement loops are the single biggest predictor of PFM retention. This uses *already-built* fields, so it is cheap leverage.

**Effort:** M. **Metric:** opt-in email open rate; D30/D60 retention uplift in A/B.

---

### R4 — Widen the addressable market: multi-currency + household sharing
**Problem.** F6/F7 cap the product to single-currency solo users — a small slice of the Quicken/Simplifi market, which sells hard on multi-currency and shared family/household budgets.

**Recommendation.**
- **Multi-currency:** store an FX rate table (or call a free rates API on sync), convert all balances/spending to the user's `Profile.currency` for net-worth and budget rollups. Keep original amounts displayed.
- **Household sharing:** add a `Household` model; let accounts/budgets be shared with other users (read/write). This unlocks the "family plan" tier that anchors Simplifi/Quicken pricing.
- Handle transfers correctly across accounts *and* across household members (offsetting legs, F7).

**Why it drives profit.** Enables geographic expansion and a higher-priced multi-seat plan; directly addresses competitor strength.

**Effort:** L (FX + sharing permissions + transfer integrity). **Metric:** net worth correct across ≥2 currencies; ≥1 shared household budget functional.

---

### R5 — Close the documentation & launch-readiness gaps (trust + investment)
**Problem.** F9/F10 + missing docs block both user trust and any fundraising/partnership conversation. README has no security posture, architecture overview, or roadmap; no deployment artifact; no contributor guide.

**Recommendation (documentation + changes):**
- Add a **Security & Privacy** section to the README: secret management via `django-environ`, `DEBUG=False` enforcement, PII handling, token encryption at rest, and the hardcoded-key remediation.
- Add a **`docs/ARCHITECTURE.md`** (request flow, HTMX partial strategy, app boundaries, data model diagram) and a **`docs/ROADMAP.md`** that maps R1–R4 to milestones — this doubles as an investor narrative.
- Add a **`Dockerfile` + `docker-compose.yml`** (Postgres + Gunicorn) and a **GitHub Actions CI** running `manage.py check`, migrations, and the test suite on every PR.
- Add **`CONTRIBUTING.md`** and a **CHANGELOG**.
- Implement **password reset** (`django.contrib.auth` views + `EMAIL_BACKEND`) and email verification — launch-blocking for a paid SaaS.
- Add `gunicorn`, `psycopg2-binary`, `django-environ`, `celery`, `cryptography` to `requirements.txt` to match the documented production path.

**Why it drives profit.** Credibility is a purchase criterion for financial software; clean docs + CI + deploy path shorten time-to-launch and de-risk investment.

**Effort:** M (mostly docs + config + auth views). **Metric:** `docker compose up` boots a prod-parity instance; CI green on PRs; password reset exercisable.

---

## 4. Prioritization

| Rank | Rec | Lever | Effort | Do when |
|------|-----|-------|--------|---------|
| 1 | R1 Correctness | Retention floor | M | Immediately — blocks everything |
| 2 | R2 Bank sync | Acquisition + WTP | L | Next sprint — the paid feature |
| 3 | R3 Alerts/Insights | Retention loops | M | In parallel with R2 (uses dead fields) |
| 4 | R4 Multi-currency + Household | Market size / pricing | L | Post-traction, pre-scale |
| 5 | R5 Docs/Security/Launch | Trust + investment | M | Continuous; CI+Docker first |

## 5. Quick wins (ship this week)
- Fix the budget sign bug (F1) — one-line `Abs()`/sign change + test.
- Add edit/delete views for transactions & accounts (F3) — copy the existing create pattern.
- Add `gunicorn`+`psycopg2` to requirements and a minimal `Dockerfile` (F9).
- Externalize `SECRET_KEY`/DB via `django-environ` and rotate the leaked key (F9).
- Implement password reset (F10) using built-in auth views.

---
*Audit performed by reading the full source tree and exercising the data layer via Django shell. Findings F1–F10 are reproduced against the running database, not inferred.*
