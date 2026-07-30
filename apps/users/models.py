from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    CURRENCY_CHOICES = (
        ("USD", "US Dollar (USD)"),
        ("EUR", "Euro (EUR)"),
        ("GBP", "British Pound (GBP)"),
        ("JPY", "Japanese Yen (JPY)"),
        ("CAD", "Canadian Dollar (CAD)"),
        ("AUD", "Australian Dollar (AUD)"),
        ("CHF", "Swiss Franc (CHF)"),
        ("CNY", "Chinese Yuan (CNY)"),
        ("INR", "Indian Rupee (INR)"),
    )

    DATE_FORMATS = (
        ("%Y-%m-%d", "YYYY-MM-DD (2025-01-15)"),
        ("%m/%d/%Y", "MM/DD/YYYY (01/15/2025)"),
        ("%d/%m/%Y", "DD/MM/YYYY (15/01/2025)"),
        ("%d-%b-%Y", "DD Mon YYYY (15 Jan 2025)"),
    )

    NUMBER_FORMATS = (
        ("en_US", "1,234.56 (US/UK style)"),
        ("de_DE", "1.234,56 (European style)"),
        ("fr_FR", "1 234,56 (French style)"),
    )

    TIMEZONES = (
        ("UTC", "UTC"),
        ("America/New_York", "Eastern Time (US & Canada)"),
        ("America/Chicago", "Central Time (US & Canada)"),
        ("America/Denver", "Mountain Time (US & Canada)"),
        ("America/Los_Angeles", "Pacific Time (US & Canada)"),
        ("Europe/London", "London"),
        ("Europe/Paris", "Paris"),
        ("Europe/Berlin", "Berlin"),
        ("Asia/Tokyo", "Tokyo"),
        ("Asia/Shanghai", "Shanghai"),
        ("Asia/Kolkata", "Kolkata"),
        ("Australia/Sydney", "Sydney"),
    )

    FIRST_DAY_CHOICES = (
        (1, "1st"),
        (2, "2nd"),
        (7, "7th (Sunday)"),
        (8, "8th"),
        (15, "15th"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")
    date_format = models.CharField(max_length=20, choices=DATE_FORMATS, default="%Y-%m-%d")
    number_format = models.CharField(max_length=10, choices=NUMBER_FORMATS, default="en_US")
    timezone = models.CharField(max_length=50, choices=TIMEZONES, default="UTC")
    first_day_of_week = models.PositiveSmallIntegerField(default=1, choices=[(i, i) for i in range(1, 8)])
    first_day_of_month = models.PositiveSmallIntegerField(default=1, choices=[(i, i) for i in range(1, 32)])
    email_notifications = models.BooleanField(default=True, help_text="Receive email notifications")
    budget_warnings = models.BooleanField(default=True, help_text="Receive budget warning notifications")
    transaction_reminders = models.BooleanField(default=False, help_text="Send reminders for pending transactions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

    @property
    def display_name(self):
        """Return the user's display name."""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username
