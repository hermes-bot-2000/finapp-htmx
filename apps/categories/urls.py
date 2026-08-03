from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_categories, name="list_categories"),
    path("create/", views.create_category, name="create_category"),
    path("<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="update_category"),
    path("<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="delete_category"),
]
