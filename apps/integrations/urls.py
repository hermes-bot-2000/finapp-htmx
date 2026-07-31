from django.urls import path
from . import views
from . import views_upload

urlpatterns = [
    path("", views.list_integrations, name="list_integrations"),
    path("upload/", views_upload.upload_statement, name="upload_statement"),
]
