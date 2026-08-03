from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DeleteView, UpdateView
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


class OwnedAccountMixin(LoginRequiredMixin):
    """Restrict the queryset to the requesting user — a foreign pk 404s."""

    model = Account
    success_url = reverse_lazy("list_accounts")

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)


class AccountUpdateView(OwnedAccountMixin, UpdateView):
    form_class = AccountForm
    template_name = "accounts/form.html"


class AccountDeleteView(OwnedAccountMixin, DeleteView):
    template_name = "accounts/confirm_delete.html"
