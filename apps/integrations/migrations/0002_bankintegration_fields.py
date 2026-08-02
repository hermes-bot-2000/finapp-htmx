from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bankintegration",
            name="institution_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="bankintegration",
            name="institution_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="bankintegration",
            name="requisition_id",
            field=models.CharField(blank=True, max_length=100, unique=True),
        ),
        migrations.AddField(
            model_name="bankintegration",
            name="account_refs",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="bankintegration",
            name="sync_status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("linked", "Linked"), ("error", "Error")],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="bankintegration",
            name="last_error",
            field=models.TextField(blank=True),
        ),
    ]
