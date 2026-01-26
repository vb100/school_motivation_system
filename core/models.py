from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "ADMIN"
        TEACHER = "TEACHER", "TEACHER"
        STUDENT = "STUDENT", "STUDENT"

    role = models.CharField(max_length=20, choices=Role.choices)


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    display_name = models.CharField(max_length=150)
    class_name = models.CharField(max_length=50, blank=True)

    def __str__(self) -> str:
        return self.display_name


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    display_name = models.CharField(max_length=150)

    def __str__(self) -> str:
        return self.display_name


class Semester(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class SchoolSettings(models.Model):
    name = models.CharField(max_length=200, default="Mokyklos pavadinimas")
    logo = models.ImageField(upload_to="school_logos/", blank=True)

    def __str__(self) -> str:
        return self.name


class GroupPurchase(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "OPEN"
        AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION", "AWAITING_CONFIRMATION"
        COMPLETED = "COMPLETED", "COMPLETED"

    bonus_item = models.ForeignKey("BonusItem", on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bonus_item", "semester"],
                condition=Q(status__in=["OPEN", "AWAITING_CONFIRMATION"]),
                name="unique_active_group_purchase",
            )
        ]

    def __str__(self) -> str:
        return f"{self.bonus_item} ({self.semester})"


class GroupContribution(models.Model):
    group_purchase = models.ForeignKey(GroupPurchase, on_delete=models.CASCADE, related_name="contributions")
    student_profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="group_contributions")
    amount = models.PositiveIntegerField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("group_purchase", "student_profile")

    def __str__(self) -> str:
        return f"{self.student_profile} {self.amount}"


class TeacherBudget(models.Model):
    teacher_profile = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    allocated_points = models.PositiveIntegerField()
    spent_points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("teacher_profile", "semester")

    @property
    def remaining_points(self) -> int:
        return max(self.allocated_points - self.spent_points, 0)


class BonusItem(models.Model):
    title_lt = models.CharField(max_length=200)
    description_lt = models.TextField()
    price_points = models.PositiveIntegerField()
    max_uses_per_student = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title_lt


class PointTransaction(models.Model):
    class TxType(models.TextChoices):
        AWARD = "AWARD", "AWARD"
        REDEEM = "REDEEM", "REDEEM"
        ADMIN_ADJUST = "ADMIN_ADJUST", "ADMIN_ADJUST"

    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    student_profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="point_transactions")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_transactions")
    tx_type = models.CharField(max_length=20, choices=TxType.choices)
    points_delta = models.IntegerField()
    message = models.TextField(blank=True)
    bonus_item = models.ForeignKey(BonusItem, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["semester", "student_profile", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(tx_type="REDEEM") & Q(bonus_item__isnull=False) & Q(points_delta__lt=0))
                    | (Q(tx_type="AWARD") & Q(bonus_item__isnull=True) & Q(points_delta__gt=0))
                    | (Q(tx_type="ADMIN_ADJUST") & Q(bonus_item__isnull=True) & Q(points_delta__gt=0))
                ),
                name="pointtransaction_type_constraints",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student_profile} {self.tx_type} {self.points_delta}"
