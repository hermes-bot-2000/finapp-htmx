from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Account
from .forms import AccountForm

@login_required
def list_accounts(request):
    accounts = Account.objects.filter(user=request.user)
    return render(request, "accounts/list.html", {"accounts": accounts})

@login_required
@require_http_methods(["GET", "POST"])
def create_account(request):
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            return redirect("list_accounts")
    else:
        form = AccountForm()
    return render(request, "accounts/form.html", {"form": form})
