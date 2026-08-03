from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_transactions, name="list_transactions"),
    path("create/", views.create_transaction, name="create_transaction"),
    path("<int:pk>/edit/", views.TransactionUpdateView.as_view(), name="update_transaction"),
    path("<int:pk>/delete/", views.TransactionDeleteView.as_view(), name="delete_transaction"),
]
