from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_categories, name="list_categories"),
    path("create/", views.create_category, name="create_category"),
]
