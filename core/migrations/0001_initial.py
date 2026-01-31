# Generated manually for initial schema
from django.conf import settings
from django.db import migrations, models
import django.contrib.auth.models
import django.utils.timezone
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, verbose_name="username")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                (
                    "role",
                    models.CharField(choices=[("ADMIN", "ADMIN"), ("TEACHER", "TEACHER"), ("STUDENT", "STUDENT")], max_length=20),
                ),
                (
                    "groups",
                    models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups"),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions"),
                ),
            ],
            options={"abstract": False},
            managers=[("objects", django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name="BonusItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title_lt", models.CharField(max_length=200)),
                ("description_lt", models.TextField()),
                ("price_points", models.PositiveIntegerField()),
                ("max_uses_per_student", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Semester",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("is_active", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="StudentProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(max_length=150)),
                ("class_name", models.CharField(blank=True, max_length=50)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="student_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="TeacherProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(max_length=150)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="TeacherBudget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("allocated_points", models.PositiveIntegerField()),
                ("spent_points", models.PositiveIntegerField(default=0)),
                ("semester", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.semester")),
                ("teacher_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.teacherprofile")),
            ],
            options={"unique_together": {("teacher_profile", "semester")}},
        ),
        migrations.CreateModel(
            name="PointTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tx_type", models.CharField(choices=[("AWARD", "AWARD"), ("REDEEM", "REDEEM"), ("ADMIN_ADJUST", "ADMIN_ADJUST")], max_length=20)),
                ("points_delta", models.IntegerField()),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("bonus_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="core.bonusitem")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_transactions", to=settings.AUTH_USER_MODEL)),
                ("semester", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.semester")),
                ("student_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="point_transactions", to="core.studentprofile")),
            ],
            options={
                "indexes": [models.Index(fields=["semester", "student_profile", "created_at"], name="core_pointt_semeste_3c1e38_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="pointtransaction",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(("tx_type", "REDEEM"), ("bonus_item__isnull", False), ("points_delta__lt", 0))
                    | models.Q(("tx_type", "AWARD"), ("bonus_item__isnull", True), ("points_delta__gt", 0))
                    | models.Q(("tx_type", "ADMIN_ADJUST"), ("bonus_item__isnull", True), ("points_delta__gt", 0))
                ),
                name="pointtransaction_type_constraints",
            ),
        ),
    ]
