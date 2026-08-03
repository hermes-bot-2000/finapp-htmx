from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_budgets, name="list_budgets"),
    path("create/", views.create_budget, name="create_budget"),
    path("summary/", views.budget_summary, name="budget_summary"),
    path("<int:pk>/edit/", views.BudgetUpdateView.as_view(), name="update_budget"),
    path("<int:pk>/delete/", views.BudgetDeleteView.as_view(), name="delete_budget"),
]
