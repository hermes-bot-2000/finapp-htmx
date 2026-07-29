from django.db import models
from django.contrib.auth.models import User

class BaseIntegration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="integrations")
    provider = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def sync_transactions(self):
        raise NotImplementedError("Subclasses must implement sync_transactions")

    def fetch_balances(self):
        raise NotImplementedError("Subclasses must implement fetch_balances")

class BankIntegration(BaseIntegration):
    bank_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)

    def sync_transactions(self):
        return []

    def fetch_balances(self):
        return {}
