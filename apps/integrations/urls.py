from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_integrations, name="list_integrations"),
]
