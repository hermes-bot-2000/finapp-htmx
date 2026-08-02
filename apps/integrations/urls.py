from django.urls import path
from . import views
from . import views_upload

urlpatterns = [
    path("", views.list_integrations, name="list_integrations"),
    path("connect/", views.connect_institutions, name="connect_institutions"),
    path("connect/account/", views.connect_account, name="connect_account"),
    path("callback/", views.integration_callback, name="integration_callback"),
    path("<int:pk>/sync/", views.sync_integration, name="sync_integration"),
    path("<int:pk>/disconnect/", views.disconnect_integration, name="disconnect_integration"),
    path("webhook/", views.integration_webhook, name="integration_webhook"),
    path("upload/", views_upload.upload_statement, name="upload_statement"),
]
