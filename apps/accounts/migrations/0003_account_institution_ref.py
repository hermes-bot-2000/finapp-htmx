from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_account_options_account_account_number_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="institution_ref",
            field=models.CharField(
                blank=True, help_text="Remote account id from the bank connection", max_length=100
            ),
        ),
    ]
