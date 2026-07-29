from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Transaction
from .forms import TransactionForm

@login_required
def list_transactions(request):
    transactions = Transaction.objects.filter(user=request.user)
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    category_id = request.GET.get("category")
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    transactions = transactions.order_by("-date", "-created_at")
    categories = request.user.categories.all()
    return render(request, "transactions/list.html", {
        "transactions": transactions,
        "categories": categories,
        "date_from": date_from or "",
        "date_to": date_to or "",
        "selected_category": int(category_id) if category_id else None,
    })

@login_required
@require_http_methods(["GET", "POST"])
def create_transaction(request):
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect("list_transactions")
    else:
        form = TransactionForm(user=request.user)
    return render(request, "transactions/form.html", {"form": form})
