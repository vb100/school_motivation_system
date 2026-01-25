from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    User,
    StudentProfile,
    TeacherProfile,
    SchoolSettings,
    Semester,
    TeacherBudget,
    BonusItem,
    PointTransaction,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Rolė", {"fields": ("role",)}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + ((None, {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "class_name", "user")
    search_fields = ("display_name", "class_name", "user__username")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user")
    search_fields = ("display_name", "user__username")


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)


@admin.register(TeacherBudget)
class TeacherBudgetAdmin(admin.ModelAdmin):
    list_display = ("teacher_profile", "semester", "allocated_points", "spent_points")
    list_filter = ("semester",)

@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    list_display = ("name",)

    def has_add_permission(self, request):
        return not SchoolSettings.objects.exists()


@admin.register(BonusItem)
class BonusItemAdmin(admin.ModelAdmin):
    list_display = ("title_lt", "price_points", "max_uses_per_student", "is_active")
    list_filter = ("is_active",)


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("student_profile", "tx_type", "points_delta", "semester", "created_at")
    list_filter = ("tx_type", "semester")
    search_fields = ("student_profile__display_name", "message")
