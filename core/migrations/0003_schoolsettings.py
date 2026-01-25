from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_update_pointtransaction_constraint"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchoolSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Mokyklos pavadinimas", max_length=200)),
            ],
        ),
    ]
