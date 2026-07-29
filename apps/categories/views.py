from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Category
from .forms import CategoryForm

@login_required
def list_categories(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, "categories/list.html", {"categories": categories})

@login_required
@require_http_methods(["GET", "POST"])
def create_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            return redirect("list_categories")
    else:
        form = CategoryForm()
    return render(request, "categories/form.html", {"form": form})
