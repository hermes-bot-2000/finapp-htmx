from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_accounts, name="list_accounts"),
    path("create/", views.create_account, name="create_account"),
    path("<int:pk>/edit/", views.AccountUpdateView.as_view(), name="update_account"),
    path("<int:pk>/delete/", views.AccountDeleteView.as_view(), name="delete_account"),
]
