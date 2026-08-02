from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Sum
from .models import Budget
from .forms import BudgetForm
from apps.categories.models import Category
from apps.transactions.models import Transaction
from datetime import date
from calendar import monthrange

@login_required
def list_budgets(request):
    budgets = Budget.objects.filter(user=request.user)
    return render(request, "budgets/list.html", {"budgets": budgets})

@login_required
@require_http_methods(["GET", "POST"])
def create_budget(request):
    if request.method == "POST":
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            return redirect("list_budgets")
    else:
        form = BudgetForm(user=request.user)
    return render(request, "budgets/form.html", {"form": form})

@login_required
def budget_summary(request):
    month = request.GET.get("month")
    if month:
        month_start = date.fromisoformat(month + "-01")
    else:
        month_start = date.today().replace(day=1)
    last_day = monthrange(month_start.year, month_start.month)[1]
    month_end = month_start.replace(day=last_day)

    budgets = Budget.objects.filter(user=request.user, month=month_start)
    summary = []
    for budget in budgets:
        actual = Transaction.objects.filter(
            user=request.user,
            category=budget.category,
            transaction_type="expense",
            date__gte=month_start,
            date__lte=month_end,
        ).aggregate(total=Sum("amount"))["total"] or 0
        actual = abs(actual)
        summary.append({
            "category": budget.category.name,
            "amount": budget.amount,
            "actual": actual,
            "remaining": budget.amount - actual,
        })
    return render(request, "budgets/summary.html", {
        "summary": summary,
        "month": month_start,
    })
