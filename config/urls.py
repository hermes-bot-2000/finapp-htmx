from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.db.models import Sum

def dashboard_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard.html")
    accounts = request.user.accounts.filter(include_in_totals=True)
    net_worth = sum(a.signed_balance for a in accounts)
    transactions = request.user.transactions.all()[:5]
    from apps.budgets.models import Budget
    from apps.transactions.models import Transaction
    from datetime import date
    from calendar import monthrange
    budgets = Budget.objects.filter(user=request.user)
    month_start = date.today().replace(day=1)
    month_end = month_start.replace(day=monthrange(month_start.year, month_start.month)[1])
    summary = []
    for budget in budgets:
        actual = Transaction.objects.filter(
            user=request.user, category=budget.category, transaction_type="expense",
            date__gte=month_start, date__lte=month_end
        ).aggregate(total=Sum("amount"))["total"] or 0
        actual = abs(actual)
        summary.append({"category": budget.category.name, "amount": budget.amount, "actual": actual, "remaining": budget.amount - actual})
    return render(request, "dashboard.html", {
        "net_worth": net_worth, "recent_transactions": transactions, "budget_summary": summary
    })

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard_view, name="dashboard"),
    path("users/", include("apps.users.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("categories/", include("apps.categories.urls")),
    path("transactions/", include("apps.transactions.urls")),
    path("budgets/", include("apps.budgets.urls")),
    path("integrations/", include("apps.integrations.urls")),
]
