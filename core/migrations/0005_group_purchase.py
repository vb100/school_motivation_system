from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_schoolsettings_logo"),
    ]

    operations = [
        migrations.CreateModel(
            name="GroupPurchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "OPEN"),
                            ("AWAITING_CONFIRMATION", "AWAITING_CONFIRMATION"),
                            ("COMPLETED", "COMPLETED"),
                        ],
                        default="OPEN",
                        max_length=30,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "bonus_item",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.bonusitem"),
                ),
                (
                    "semester",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.semester"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GroupContribution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.PositiveIntegerField()),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "group_purchase",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contributions",
                        to="core.grouppurchase",
                    ),
                ),
                (
                    "student_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_contributions",
                        to="core.studentprofile",
                    ),
                ),
            ],
            options={
                "unique_together": {("group_purchase", "student_profile")},
            },
        ),
        migrations.AddConstraint(
            model_name="grouppurchase",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status__in", ["OPEN", "AWAITING_CONFIRMATION"])),
                fields=("bonus_item", "semester"),
                name="unique_active_group_purchase",
            ),
        ),
    ]
