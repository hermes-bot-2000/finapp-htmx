from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_transactions, name="list_transactions"),
    path("create/", views.create_transaction, name="create_transaction"),
]
