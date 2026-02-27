from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_user_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="bonusitem",
            name="assigned_teachers",
            field=models.ManyToManyField(
                blank=True,
                related_name="assigned_bonus_items",
                to="core.teacherprofile",
            ),
        ),
        migrations.AddField(
            model_name="bonusitem",
            name="category",
            field=models.CharField(
                choices=[
                    ("POINTS_RELATED", "Pirkiniai susiję su balais"),
                    ("OTHER", "Kiti pirkiniai"),
                ],
                default="OTHER",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="BonusRedemptionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "PENDING"),
                            ("APPROVED", "APPROVED"),
                            ("DECLINED", "DECLINED"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                (
                    "bonus_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="redemption_requests",
                        to="core.bonusitem",
                    ),
                ),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="decided_bonus_redemption_requests",
                        to="core.user",
                    ),
                ),
                (
                    "requested_teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_redemption_requests",
                        to="core.teacherprofile",
                    ),
                ),
                (
                    "semester",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_redemption_requests",
                        to="core.semester",
                    ),
                ),
                (
                    "student_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_redemption_requests",
                        to="core.studentprofile",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="bonusredemptionrequest",
            index=models.Index(
                fields=["requested_teacher", "status", "created_at"],
                name="core_bonusr_request_357216_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="bonusredemptionrequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "PENDING")),
                fields=("semester", "bonus_item", "student_profile"),
                name="unique_pending_bonus_redemption_request",
            ),
        ),
    ]
