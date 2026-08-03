from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DeleteView, UpdateView
from .models import Transaction
from .forms import TransactionFilterForm, TransactionForm

@login_required
def list_transactions(request):
    transactions = Transaction.objects.filter(user=request.user)
    # F4: validate the query string instead of handing raw input to the ORM.
    filter_form = TransactionFilterForm(request.GET or None, user=request.user)
    transactions = filter_form.filter(transactions).order_by("-date", "-created_at")
    categories = filter_form.fields["category"].queryset
    selected = filter_form.cleaned_data.get("category") if filter_form.is_bound and filter_form.is_valid() else None
    return render(request, "transactions/list.html", {
        "transactions": transactions,
        "filter_form": filter_form,
        "filter_errors": filter_form.errors if filter_form.is_bound else {},
        "categories": categories,
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "selected_category": selected.pk if selected else None,
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


class OwnedTransactionMixin(LoginRequiredMixin):
    """Restrict the queryset to the requesting user — a foreign pk 404s."""

    model = Transaction
    success_url = reverse_lazy("list_transactions")

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class TransactionUpdateView(OwnedTransactionMixin, UpdateView):
    form_class = TransactionForm
    template_name = "transactions/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TransactionDeleteView(OwnedTransactionMixin, DeleteView):
    template_name = "transactions/confirm_delete.html"
